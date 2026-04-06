from django.contrib.auth import views as auth_views
from django.urls import path
from django.urls import reverse_lazy

from .views import (
    admin_dashboard,
    admin_student_detail,
    admin_student_list,
    admin_teacher_detail,
    admin_teacher_list,
    admin_user_create,
    admin_user_delete,
    admin_user_management,
    admin_user_toggle_approval,
    admin_user_toggle_block,
    home_view,
    login_view,
    logout_view,
    profile_edit_view,
    profile_view,
    register_view,
    resend_otp_view,
    student_dashboard,
    teacher_student_detail,
    teacher_students_view,
    teacher_dashboard,
    verify_email_view,
)
from .forms import StyledPasswordChangeForm, StyledPasswordResetForm, StyledSetPasswordForm

urlpatterns = [
    path("", home_view, name="home"),
    path("register/", register_view, name="register"),
    path("verify-email/", verify_email_view, name="verify_email"),
    path("resend-otp/", resend_otp_view, name="resend_otp"),
    path("login/", login_view, name="login"),
    path(
        "forgot-password/",
        auth_views.PasswordResetView.as_view(
            form_class=StyledPasswordResetForm,
            template_name="users/password_reset_form.html",
            email_template_name="users/password_reset_email.txt",
            subject_template_name="users/password_reset_subject.txt",
            success_url=reverse_lazy("password_reset_done"),
        ),
        name="password_reset",
    ),
    path(
        "forgot-password/done/",
        auth_views.PasswordResetDoneView.as_view(template_name="users/password_reset_done.html"),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            form_class=StyledSetPasswordForm,
            template_name="users/password_reset_confirm.html",
            success_url=reverse_lazy("password_reset_complete"),
        ),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(template_name="users/password_reset_complete.html"),
        name="password_reset_complete",
    ),
    path("logout/", logout_view, name="logout"),
    path(
        "profile/password/",
        auth_views.PasswordChangeView.as_view(
            form_class=StyledPasswordChangeForm,
            template_name="users/password_change_form.html",
            success_url=reverse_lazy("password_change_done"),
        ),
        name="password_change",
    ),
    path(
        "profile/password/done/",
        auth_views.PasswordChangeDoneView.as_view(template_name="users/password_change_done.html"),
        name="password_change_done",
    ),
    path("profile/", profile_view, name="profile"),
    path("profile/edit/", profile_edit_view, name="profile_edit"),
    path("dashboard/admin/", admin_dashboard, name="admin_dashboard"),
    path("dashboard/admin/users/", admin_user_management, name="admin_user_management"),
    path("dashboard/admin/users/teachers/", admin_teacher_list, name="admin_teacher_list"),
    path("dashboard/admin/users/teachers/<int:pk>/", admin_teacher_detail, name="admin_teacher_detail"),
    path("dashboard/admin/users/students/", admin_student_list, name="admin_student_list"),
    path("dashboard/admin/users/students/<int:pk>/", admin_student_detail, name="admin_student_detail"),
    path("dashboard/admin/users/create/", admin_user_create, name="admin_user_create"),
    path("dashboard/admin/users/<int:pk>/approve/", admin_user_toggle_approval, name="admin_user_toggle_approval"),
    path("dashboard/admin/users/<int:pk>/block/", admin_user_toggle_block, name="admin_user_toggle_block"),
    path("dashboard/admin/users/<int:pk>/delete/", admin_user_delete, name="admin_user_delete"),
    path("dashboard/teacher/", teacher_dashboard, name="teacher_dashboard"),
    path("dashboard/teacher/students/", teacher_students_view, name="teacher_students"),
    path("dashboard/teacher/students/<int:pk>/", teacher_student_detail, name="teacher_student_detail"),
    path("dashboard/student/", student_dashboard, name="student_dashboard"),
]
