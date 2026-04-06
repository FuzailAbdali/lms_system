from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Prefetch
from django.shortcuts import get_object_or_404, redirect, render

from articles.models import Article
from courses.models import Course, Enrollment
from .forms import (
    AdminManagedUserForm,
    EmailVerificationForm,
    UserLoginForm,
    UserProfileForm,
    UserRegistrationForm,
)
from .decorators import role_required
from .models import User
from .utils import is_otp_expired, send_verification_otp


def redirect_user_by_role(user):
    if user.is_superuser or user.is_admin():
        return "admin_dashboard"
    if user.is_teacher():
        return "teacher_dashboard"
    return "student_dashboard"


def user_avatar_context(user):
    return {
        "managed_user": user,
        "title": user.get_full_name() or user.username,
    }


def home_view(request):
    if request.user.is_authenticated:
        return redirect(redirect_user_by_role(request.user))
    return redirect("login")


def register_view(request):
    if request.user.is_authenticated:
        return redirect(redirect_user_by_role(request.user))

    form = UserRegistrationForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        user = form.save(commit=False)
        user.is_active = False
        user.is_approved = False
        user.is_email_verified = False
        user.set_email_otp()
        user.save()
        try:
            send_verification_otp(user)
        except Exception:
            user.delete()
            form.add_error(None, "Could not send verification email. Please check SMTP settings and try again.")
        else:
            request.session["pending_verification_user_id"] = user.id
            messages.success(request, "We sent an OTP to your email. Please verify your account.")
            return redirect("verify_email")

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


def verify_email_view(request):
    if request.user.is_authenticated:
        return redirect(redirect_user_by_role(request.user))

    pending_user_id = request.session.get("pending_verification_user_id")
    if not pending_user_id:
        messages.info(request, "Please create your account first.")
        return redirect("register")

    user = User.objects.filter(pk=pending_user_id, is_email_verified=False).first()
    if not user:
        request.session.pop("pending_verification_user_id", None)
        messages.info(request, "Your account is already verified. Please log in.")
        return redirect("login")

    form = EmailVerificationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        otp = form.cleaned_data["otp"]
        if is_otp_expired(user):
            form.add_error("otp", "This OTP has expired. Please request a new one.")
        elif user.email_otp != otp:
            form.add_error("otp", "Invalid OTP. Please try again.")
        else:
            user.is_email_verified = True
            user.email_otp = ""
            user.email_otp_created_at = None
            user.is_active = user.is_approved
            user.save(update_fields=["is_active", "is_email_verified", "email_otp", "email_otp_created_at"])
            request.session.pop("pending_verification_user_id", None)
            if user.is_approved:
                login(request, user)
                messages.success(request, "Email verified successfully.")
                return redirect(redirect_user_by_role(user))
            messages.success(request, "Email verified successfully. Your account is awaiting admin approval.")
            return redirect("login")

    return render(request, "users/verify_email.html", {"form": form, "email": user.email})


def resend_otp_view(request):
    pending_user_id = request.session.get("pending_verification_user_id")
    if not pending_user_id:
        messages.info(request, "Please create your account first.")
        return redirect("register")

    user = User.objects.filter(pk=pending_user_id, is_email_verified=False).first()
    if not user:
        request.session.pop("pending_verification_user_id", None)
        messages.info(request, "Your account is already verified. Please log in.")
        return redirect("login")

    user.set_email_otp()
    user.save(update_fields=["email_otp", "email_otp_created_at"])
    try:
        send_verification_otp(user)
    except Exception:
        messages.error(request, "Could not resend OTP email. Please check SMTP settings.")
    else:
        messages.success(request, "A new OTP has been sent to your email.")
    return redirect("verify_email")


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
        "total_students": User.objects.filter(role=User.Role.STUDENT).count(),
        "total_teachers": User.objects.filter(role=User.Role.TEACHER).count(),
        "pending_users": User.objects.filter(role__in=[User.Role.STUDENT, User.Role.TEACHER], is_approved=False).count(),
        "total_courses": Course.objects.count(),
        "total_enrollments": Enrollment.objects.count(),
        "winner_article": Article.objects.select_related("student").filter(is_winner=True).first(),
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
        "winner_article": Article.objects.select_related("student").filter(is_winner=True).first(),
        "teacher_students_count": User.objects.filter(
            enrollments__course__teacher=request.user,
            role=User.Role.STUDENT,
        ).distinct().count(),
    }
    return render(request, "users/teacher_dashboard.html", context)


@role_required(User.Role.STUDENT)
def student_dashboard(request):
    enrolled_courses = Course.objects.filter(enrollments__student=request.user).select_related("teacher")
    context = {
        "title": "Student Dashboard",
        "enrolled_courses": enrolled_courses,
        "enrolled_courses_count": enrolled_courses.count(),
        "winner_article": Article.objects.select_related("student").filter(is_winner=True).first(),
    }
    return render(request, "users/student_dashboard.html", context)


def admin_user_management(request):
    if not request.user.is_authenticated or not (request.user.is_superuser or request.user.is_admin()):
        return redirect("login")

    teachers = User.objects.filter(role=User.Role.TEACHER).order_by("first_name", "username")
    students = User.objects.filter(role=User.Role.STUDENT).order_by("first_name", "username")
    context = {
        "title": "User Management",
        "teachers": teachers,
        "students": students,
    }
    return render(request, "users/manage_users.html", context)


def admin_teacher_list(request):
    if not request.user.is_authenticated or not (request.user.is_superuser or request.user.is_admin()):
        return redirect("login")

    teachers = User.objects.filter(role=User.Role.TEACHER).order_by("first_name", "username")
    return render(
        request,
        "users/user_list.html",
        {"title": "Teachers", "users_list": teachers, "role_label": "Teacher"},
    )


def admin_student_list(request):
    if not request.user.is_authenticated or not (request.user.is_superuser or request.user.is_admin()):
        return redirect("login")

    students = User.objects.filter(role=User.Role.STUDENT).order_by("first_name", "username")
    return render(
        request,
        "users/user_list.html",
        {"title": "Students", "users_list": students, "role_label": "Student"},
    )


def admin_teacher_detail(request, pk):
    if not request.user.is_authenticated or not (request.user.is_superuser or request.user.is_admin()):
        return redirect("login")

    teacher = get_object_or_404(User, pk=pk, role=User.Role.TEACHER)
    teacher_courses = Course.objects.filter(teacher=teacher).annotate(total_enrollments=Count("enrollments"))
    context = user_avatar_context(teacher)
    context.update(
        {
            "page_heading": "Teacher Detail",
            "teacher_courses": teacher_courses,
            "show_admin_actions": True,
        }
    )
    return render(request, "users/user_detail.html", context)


def admin_student_detail(request, pk):
    if not request.user.is_authenticated or not (request.user.is_superuser or request.user.is_admin()):
        return redirect("login")

    student = get_object_or_404(User, pk=pk, role=User.Role.STUDENT)
    student_enrollments = Enrollment.objects.select_related("course", "course__teacher").filter(student=student)
    context = user_avatar_context(student)
    context.update(
        {
            "page_heading": "Student Detail",
            "student_enrollments": student_enrollments,
            "show_admin_actions": True,
        }
    )
    return render(request, "users/user_detail.html", context)


def admin_user_create(request):
    if not request.user.is_authenticated or not (request.user.is_superuser or request.user.is_admin()):
        return redirect("login")

    form = AdminManagedUserForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "User created successfully.")
        return redirect("admin_user_management")

    return render(request, "users/user_form.html", {"form": form, "title": "Add User"})


def admin_user_toggle_approval(request, pk):
    if not request.user.is_authenticated or not (request.user.is_superuser or request.user.is_admin()):
        return redirect("login")

    user = get_object_or_404(User, pk=pk)
    if user.is_superuser or user.role == User.Role.ADMIN:
        messages.error(request, "Admin accounts cannot be managed from this screen.")
        return redirect("admin_user_management")

    user.is_approved = not user.is_approved
    user.is_active = user.is_approved and user.is_email_verified
    user.save(update_fields=["is_approved", "is_active"])
    messages.success(request, "User approval status updated.")
    return redirect("admin_user_management")


def admin_user_toggle_block(request, pk):
    if not request.user.is_authenticated or not (request.user.is_superuser or request.user.is_admin()):
        return redirect("login")

    user = get_object_or_404(User, pk=pk)
    if user.is_superuser or user.role == User.Role.ADMIN:
        messages.error(request, "Admin accounts cannot be managed from this screen.")
        return redirect("admin_user_management")

    user.is_active = not user.is_active if user.is_approved else False
    user.save(update_fields=["is_active"])
    messages.success(request, "User active status updated.")
    return redirect("admin_user_management")


def admin_user_delete(request, pk):
    if not request.user.is_authenticated or not (request.user.is_superuser or request.user.is_admin()):
        return redirect("login")

    user = get_object_or_404(User, pk=pk)
    if user.is_superuser or user.role == User.Role.ADMIN:
        messages.error(request, "Admin accounts cannot be deleted from this screen.")
        return redirect("admin_user_management")

    if request.method == "POST":
        user.delete()
        messages.success(request, "User deleted successfully.")
        return redirect("admin_user_management")

    return render(request, "users/user_confirm_delete.html", {"managed_user": user, "title": "Delete User"})


@login_required
def profile_view(request):
    context = {
        "title": "My Profile",
        "managed_user": request.user,
        "page_heading": "My Profile",
        "student_enrollments": Enrollment.objects.select_related("course", "course__teacher").filter(student=request.user)
        if request.user.role == User.Role.STUDENT
        else None,
        "teacher_courses": Course.objects.filter(teacher=request.user).annotate(total_enrollments=Count("enrollments"))
        if request.user.role == User.Role.TEACHER
        else None,
        "show_admin_actions": False,
    }
    return render(request, "users/user_detail.html", context)


@login_required
def profile_edit_view(request):
    form = UserProfileForm(request.POST or None, request.FILES or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Profile updated successfully.")
        return redirect("profile")

    return render(request, "users/profile_form.html", {"title": "Edit Profile", "form": form})


@role_required(User.Role.TEACHER)
def teacher_students_view(request):
    students = User.objects.filter(
        role=User.Role.STUDENT,
        enrollments__course__teacher=request.user,
    ).distinct().order_by("first_name", "username")
    return render(
        request,
        "users/teacher_students.html",
        {"title": "My Students", "students": students},
    )


@role_required(User.Role.TEACHER)
def teacher_student_detail(request, pk):
    student = get_object_or_404(
        User.objects.filter(
            role=User.Role.STUDENT,
            enrollments__course__teacher=request.user,
        ).distinct(),
        pk=pk,
    )
    student_enrollments = Enrollment.objects.select_related("course", "course__teacher").filter(
        student=student,
        course__teacher=request.user,
    )
    context = user_avatar_context(student)
    context.update(
        {
            "page_heading": "Student Detail",
            "student_enrollments": student_enrollments,
            "show_admin_actions": False,
        }
    )
    return render(request, "users/user_detail.html", context)
