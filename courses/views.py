from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render

from users.decorators import role_required
from users.models import User

from .forms import CourseForm
from .models import Course, Enrollment


@login_required
def course_list(request):
    courses = Course.objects.select_related("teacher").annotate(
        enrolled_students_count=Count("enrollments")
    )
    enrolled_course_ids = set()
    if request.user.is_authenticated and request.user.role == User.Role.STUDENT:
        enrolled_course_ids = set(
            Enrollment.objects.filter(student=request.user).values_list("course_id", flat=True)
        )

    context = {
        "title": "Courses",
        "courses": courses,
        "enrolled_course_ids": enrolled_course_ids,
    }
    return render(request, "courses/course_list.html", context)


@login_required
def enrollment_list(request):
    can_manage_enrollments = False
    if request.user.is_superuser or request.user.role == User.Role.ADMIN:
        enrollments = Enrollment.objects.select_related("student", "course", "course__teacher").order_by(
            "course__title", "student__username"
        )
        title = "Enrollments"
        can_manage_enrollments = True
    elif request.user.role == User.Role.TEACHER:
        enrollments = Enrollment.objects.select_related("student", "course", "course__teacher").filter(
            course__teacher=request.user
        ).order_by("course__title", "student__username")
        title = "Course Enrollments"
        can_manage_enrollments = True
    else:
        enrollments = Enrollment.objects.select_related("student", "course", "course__teacher").filter(
            student=request.user
        ).order_by("course__title")
        title = "My Enrollments"

    context = {
        "title": title,
        "enrollments": enrollments,
        "can_manage_enrollments": can_manage_enrollments,
    }
    return render(request, "courses/enrollment_list.html", context)


@role_required(User.Role.TEACHER)
def teacher_course_create(request):
    form = CourseForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        course = form.save(commit=False)
        course.teacher = request.user
        course.save()
        messages.success(request, "Course created successfully.")
        return redirect("teacher_dashboard")
    return render(request, "courses/course_form.html", {"form": form, "title": "Create Course"})


@role_required(User.Role.TEACHER)
def teacher_course_update(request, pk):
    course = get_object_or_404(Course, pk=pk, teacher=request.user)
    form = CourseForm(request.POST or None, instance=course)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Course updated successfully.")
        return redirect("teacher_dashboard")
    return render(request, "courses/course_form.html", {"form": form, "title": "Update Course"})


@role_required(User.Role.TEACHER)
def teacher_course_delete(request, pk):
    course = get_object_or_404(Course, pk=pk, teacher=request.user)
    if request.method == "POST":
        course.delete()
        messages.success(request, "Course deleted successfully.")
        return redirect("teacher_dashboard")
    return render(request, "courses/course_confirm_delete.html", {"course": course, "title": "Delete Course"})


@role_required(User.Role.STUDENT)
def enroll_course(request, pk):
    course = get_object_or_404(Course, pk=pk)
    Enrollment.objects.get_or_create(student=request.user, course=course)
    messages.success(request, "You have been enrolled successfully.")
    return redirect("course_list")


@login_required
def remove_enrollment(request, pk):
    enrollment = get_object_or_404(
        Enrollment.objects.select_related("student", "course", "course__teacher"),
        pk=pk,
    )

    allowed = (
        request.user.is_superuser
        or request.user.role == User.Role.ADMIN
        or (request.user.role == User.Role.TEACHER and enrollment.course.teacher_id == request.user.id)
    )
    if not allowed:
        return redirect("login")

    if request.method == "POST":
        enrollment.delete()
        messages.success(request, "Enrollment removed successfully.")
        return redirect("enrollment_list")

    return render(
        request,
        "courses/enrollment_confirm_remove.html",
        {"title": "Remove Enrollment", "enrollment": enrollment},
    )
