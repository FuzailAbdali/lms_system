from django.urls import path

from .views import (
    answer_create,
    answer_delete,
    answer_update,
    question_create,
    question_delete,
    question_update,
    quiz_attempt,
    quiz_create,
    quiz_delete,
    quiz_manage,
    quiz_result,
    quiz_update,
)

urlpatterns = [
    path("<int:course_pk>/chapters/<int:chapter_pk>/", quiz_manage, name="quiz_manage"),
    path("<int:course_pk>/chapters/<int:chapter_pk>/create/", quiz_create, name="quiz_create"),
    path("<int:course_pk>/chapters/<int:chapter_pk>/edit/", quiz_update, name="quiz_update"),
    path("<int:course_pk>/chapters/<int:chapter_pk>/delete/", quiz_delete, name="quiz_delete"),
    path("<int:course_pk>/chapters/<int:chapter_pk>/attempt/", quiz_attempt, name="quiz_attempt"),
    path("<int:course_pk>/chapters/<int:chapter_pk>/result/", quiz_result, name="quiz_result"),
    path("<int:course_pk>/chapters/<int:chapter_pk>/questions/create/", question_create, name="question_create"),
    path("<int:course_pk>/chapters/<int:chapter_pk>/questions/<int:question_pk>/edit/", question_update, name="question_update"),
    path("<int:course_pk>/chapters/<int:chapter_pk>/questions/<int:question_pk>/delete/", question_delete, name="question_delete"),
    path("<int:course_pk>/chapters/<int:chapter_pk>/questions/<int:question_pk>/answers/create/", answer_create, name="answer_create"),
    path("<int:course_pk>/chapters/<int:chapter_pk>/questions/<int:question_pk>/answers/<int:answer_pk>/edit/", answer_update, name="answer_update"),
    path("<int:course_pk>/chapters/<int:chapter_pk>/questions/<int:question_pk>/answers/<int:answer_pk>/delete/", answer_delete, name="answer_delete"),
]
