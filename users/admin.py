from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("LMS", {"fields": ("role", "phone_number", "address", "is_email_verified")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("LMS", {"fields": ("role", "phone_number", "address", "is_email_verified")}),
    )
    list_display = ("username", "email", "first_name", "last_name", "phone_number", "role", "is_email_verified", "is_staff")
    list_filter = ("role", "is_staff", "is_superuser", "is_active")
