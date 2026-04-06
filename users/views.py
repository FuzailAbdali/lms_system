from django.contrib import messages
from django.contrib.auth import login, logout
from django.db.models import Count, Prefetch
from django.shortcuts import redirect, render

from courses.models import Course, Enrollment
from .forms import EmailVerificationForm, UserLoginForm, UserRegistrationForm
from .decorators import role_required
from .models import User
from .utils import is_otp_expired, send_verification_otp


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
        user = form.save(commit=False)
        user.is_active = False
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
            user.is_active = True
            user.is_email_verified = True
            user.email_otp = ""
            user.email_otp_created_at = None
            user.save(update_fields=["is_active", "is_email_verified", "email_otp", "email_otp_created_at"])
            request.session.pop("pending_verification_user_id", None)
            login(request, user)
            messages.success(request, "Email verified successfully.")
            return redirect(redirect_user_by_role(user))

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
