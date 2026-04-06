from django.urls import path

from .views import (
    admin_dashboard,
    home_view,
    login_view,
    logout_view,
    register_view,
    resend_otp_view,
    student_dashboard,
    teacher_dashboard,
    verify_email_view,
)

urlpatterns = [
    path("", home_view, name="home"),
    path("register/", register_view, name="register"),
    path("verify-email/", verify_email_view, name="verify_email"),
    path("resend-otp/", resend_otp_view, name="resend_otp"),
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
    path("dashboard/admin/", admin_dashboard, name="admin_dashboard"),
    path("dashboard/teacher/", teacher_dashboard, name="teacher_dashboard"),
    path("dashboard/student/", student_dashboard, name="student_dashboard"),
]
