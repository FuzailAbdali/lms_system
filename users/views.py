from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render

from .forms import UserLoginForm, UserRegistrationForm


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


@login_required
def admin_dashboard(request):
    if not (request.user.is_superuser or request.user.is_admin()):
        return HttpResponseForbidden("You do not have access to this dashboard.")
    return render(request, "users/dashboard.html", {"title": "Admin Dashboard"})


@login_required
def teacher_dashboard(request):
    if not request.user.is_teacher():
        return HttpResponseForbidden("You do not have access to this dashboard.")
    return render(request, "users/dashboard.html", {"title": "Teacher Dashboard"})


@login_required
def student_dashboard(request):
    if not request.user.is_student():
        return HttpResponseForbidden("You do not have access to this dashboard.")
    return render(request, "users/dashboard.html", {"title": "Student Dashboard"})
