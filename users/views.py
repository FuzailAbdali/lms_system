from django.contrib.auth import login, logout
from django.db.models import Count, Prefetch
from django.shortcuts import redirect, render

from courses.models import Course, Enrollment
from .forms import UserLoginForm, UserRegistrationForm
from .decorators import role_required
from .models import User


def redirect_user_by_role(user):
    if user.is_superuser or user.is_admin():
        return "admin_dashboard"
    if user.is_teacher():
        return "teacher_dashboard"
    return "student_dashboard"


def home_view(request):
    if request.user.is_authenticated:
        return redirect(redirect_user_by_role(request.user))
    return redirect("login")


def register_view(request):
    if request.user.is_authenticated:
        return redirect(redirect_user_by_role(request.user))

    form = UserRegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect(redirect_user_by_role(user))

    return render(request, "users/register.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect(redirect_user_by_role(request.user))

    form = UserLoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.cleaned_data["user"])
        return redirect(redirect_user_by_role(form.cleaned_data["user"]))

    return render(request, "users/login.html", {"form": form})


def logout_view(request):
    logout(request)
    return redirect("login")


def admin_dashboard(request):
    if not request.user.is_authenticated:
        return redirect("login")
    if not (request.user.is_superuser or request.user.is_admin()):
        return redirect("login")
    admin_courses = Course.objects.select_related("teacher").prefetch_related(
        Prefetch(
            "enrollments",
            queryset=Enrollment.objects.select_related("student").order_by("-enrolled_at"),
        )
    ).annotate(total_enrollments=Count("enrollments"))
    context = {
        "title": "Admin Dashboard",
        "total_users": User.objects.count(),
        "total_courses": Course.objects.count(),
        "total_enrollments": Enrollment.objects.count(),
        "admin_courses": admin_courses,
    }
    return render(request, "users/admin_dashboard.html", context)


@role_required(User.Role.TEACHER)
def teacher_dashboard(request):
    teacher_courses = Course.objects.filter(teacher=request.user).prefetch_related(
        Prefetch(
            "enrollments",
            queryset=Enrollment.objects.select_related("student").order_by("-enrolled_at"),
        )
    ).annotate(total_enrollments=Count("enrollments"))
    total_teacher_enrollments = sum(course.total_enrollments for course in teacher_courses)
    context = {
        "title": "Teacher Dashboard",
        "teacher_courses": teacher_courses,
        "total_teacher_enrollments": total_teacher_enrollments,
    }
    return render(request, "users/teacher_dashboard.html", context)


@role_required(User.Role.STUDENT)
def student_dashboard(request):
    enrolled_courses = Course.objects.filter(enrollments__student=request.user).select_related("teacher")
    context = {
        "title": "Student Dashboard",
        "enrolled_courses": enrolled_courses,
        "enrolled_courses_count": enrolled_courses.count(),
    }
    return render(request, "users/student_dashboard.html", context)
