from django.contrib.auth import login, logout
from django.shortcuts import redirect, render

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
    context = {
        "title": "Admin Dashboard",
        "total_users": User.objects.count(),
        "total_courses": 0,
    }
    return render(request, "users/admin_dashboard.html", context)


@role_required(User.Role.TEACHER)
def teacher_dashboard(request):
    context = {
        "title": "Teacher Dashboard",
    }
    return render(request, "users/teacher_dashboard.html", context)


@role_required(User.Role.STUDENT)
def student_dashboard(request):
    context = {
        "title": "Student Dashboard",
        "enrolled_courses": [],
        "enrolled_courses_count": 0,
    }
    return render(request, "users/student_dashboard.html", context)
