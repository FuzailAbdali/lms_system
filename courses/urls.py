from django.urls import path

from .views import (
    course_list,
    enrollment_list,
    enroll_course,
    remove_enrollment,
    teacher_course_create,
    teacher_course_delete,
    teacher_course_update,
)

urlpatterns = [
    path("", course_list, name="course_list"),
    path("enrollments/", enrollment_list, name="enrollment_list"),
    path("create/", teacher_course_create, name="teacher_course_create"),
    path("<int:pk>/edit/", teacher_course_update, name="teacher_course_update"),
    path("<int:pk>/delete/", teacher_course_delete, name="teacher_course_delete"),
    path("<int:pk>/enroll/", enroll_course, name="enroll_course"),
    path("enrollments/<int:pk>/remove/", remove_enrollment, name="remove_enrollment"),
]
