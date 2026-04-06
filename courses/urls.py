from django.urls import path

from .views import (
    chapter_detail,
    chapter_list,
    course_list,
    enrollment_list,
    enroll_course,
    remove_enrollment,
    teacher_chapter_create,
    teacher_chapter_delete,
    teacher_chapter_update,
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
    path("<int:course_pk>/chapters/", chapter_list, name="chapter_list"),
    path("<int:course_pk>/chapters/<int:pk>/", chapter_detail, name="chapter_detail"),
    path("<int:course_pk>/chapters/create/", teacher_chapter_create, name="teacher_chapter_create"),
    path("<int:course_pk>/chapters/<int:pk>/edit/", teacher_chapter_update, name="teacher_chapter_update"),
    path("<int:course_pk>/chapters/<int:pk>/delete/", teacher_chapter_delete, name="teacher_chapter_delete"),
    path("<int:pk>/enroll/", enroll_course, name="enroll_course"),
    path("enrollments/<int:pk>/remove/", remove_enrollment, name="remove_enrollment"),
]
