from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from users.decorators import role_required
from users.models import User

from courses.models import Chapter

from .forms import AnswerForm, QuestionForm, QuizAttemptForm, QuizForm
from .models import Answer, Question, Quiz, QuizAttempt, QuizAttemptAnswer


def get_teacher_chapter_or_404(user, course_pk, chapter_pk):
    return get_object_or_404(
        Chapter.objects.select_related("course"),
        pk=chapter_pk,
        course_id=course_pk,
        course__teacher=user,
    )


def get_student_chapter_or_404(course_pk, chapter_pk):
    return get_object_or_404(
        Chapter.objects.select_related("course").prefetch_related(
            "quiz__questions__answers"
        ),
        pk=chapter_pk,
        course_id=course_pk,
    )


@role_required(User.Role.TEACHER)
def quiz_manage(request, course_pk, chapter_pk):
    chapter = get_teacher_chapter_or_404(request.user, course_pk, chapter_pk)
    quiz = Quiz.objects.filter(chapter=chapter).prefetch_related("questions__answers").first()
    context = {
        "title": "Manage Quiz",
        "course": chapter.course,
        "chapter": chapter,
        "quiz": quiz,
    }
    return render(request, "quizzes/quiz_manage.html", context)


@role_required(User.Role.TEACHER)
def quiz_create(request, course_pk, chapter_pk):
    chapter = get_teacher_chapter_or_404(request.user, course_pk, chapter_pk)
    if hasattr(chapter, "quiz"):
        messages.info(request, "This chapter already has a quiz.")
        return redirect("quiz_manage", course_pk=course_pk, chapter_pk=chapter_pk)

    initial = {"title": f"{chapter.title} Quiz"}
    form = QuizForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        quiz = form.save(commit=False)
        quiz.chapter = chapter
        quiz.save()
        messages.success(request, "Quiz created successfully.")
        return redirect("quiz_manage", course_pk=course_pk, chapter_pk=chapter_pk)

    return render(request, "quizzes/quiz_form.html", {"form": form, "course": chapter.course, "chapter": chapter, "title": "Create Quiz"})


@role_required(User.Role.TEACHER)
def quiz_update(request, course_pk, chapter_pk):
    chapter = get_teacher_chapter_or_404(request.user, course_pk, chapter_pk)
    quiz = get_object_or_404(Quiz, chapter=chapter)
    form = QuizForm(request.POST or None, instance=quiz)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Quiz updated successfully.")
        return redirect("quiz_manage", course_pk=course_pk, chapter_pk=chapter_pk)
    return render(request, "quizzes/quiz_form.html", {"form": form, "course": chapter.course, "chapter": chapter, "title": "Update Quiz"})


@role_required(User.Role.TEACHER)
def quiz_delete(request, course_pk, chapter_pk):
    chapter = get_teacher_chapter_or_404(request.user, course_pk, chapter_pk)
    quiz = get_object_or_404(Quiz, chapter=chapter)
    if request.method == "POST":
        quiz.delete()
        messages.success(request, "Quiz deleted successfully.")
        return redirect("chapter_list", course_pk=course_pk)
    return render(
        request,
        "quizzes/quiz_confirm_delete.html",
        {"course": chapter.course, "chapter": chapter, "quiz": quiz, "title": "Delete Quiz"},
    )


@role_required(User.Role.TEACHER)
def question_create(request, course_pk, chapter_pk):
    chapter = get_teacher_chapter_or_404(request.user, course_pk, chapter_pk)
    quiz = get_object_or_404(Quiz, chapter=chapter)
    form = QuestionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        question = form.save(commit=False)
        question.quiz = quiz
        question.save()
        messages.success(request, "Question added successfully.")
        return redirect("quiz_manage", course_pk=course_pk, chapter_pk=chapter_pk)
    return render(request, "quizzes/question_form.html", {"form": form, "course": chapter.course, "chapter": chapter, "quiz": quiz, "title": "Add Question"})


@role_required(User.Role.TEACHER)
def question_update(request, course_pk, chapter_pk, question_pk):
    chapter = get_teacher_chapter_or_404(request.user, course_pk, chapter_pk)
    quiz = get_object_or_404(Quiz, chapter=chapter)
    question = get_object_or_404(Question, pk=question_pk, quiz=quiz)
    form = QuestionForm(request.POST or None, instance=question)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Question updated successfully.")
        return redirect("quiz_manage", course_pk=course_pk, chapter_pk=chapter_pk)
    return render(request, "quizzes/question_form.html", {"form": form, "course": chapter.course, "chapter": chapter, "quiz": quiz, "question": question, "title": "Update Question"})


@role_required(User.Role.TEACHER)
def question_delete(request, course_pk, chapter_pk, question_pk):
    chapter = get_teacher_chapter_or_404(request.user, course_pk, chapter_pk)
    quiz = get_object_or_404(Quiz, chapter=chapter)
    question = get_object_or_404(Question, pk=question_pk, quiz=quiz)
    if request.method == "POST":
        question.delete()
        messages.success(request, "Question deleted successfully.")
        return redirect("quiz_manage", course_pk=course_pk, chapter_pk=chapter_pk)
    return render(request, "quizzes/question_confirm_delete.html", {"course": chapter.course, "chapter": chapter, "quiz": quiz, "question": question, "title": "Delete Question"})


@role_required(User.Role.TEACHER)
def answer_create(request, course_pk, chapter_pk, question_pk):
    chapter = get_teacher_chapter_or_404(request.user, course_pk, chapter_pk)
    quiz = get_object_or_404(Quiz, chapter=chapter)
    question = get_object_or_404(Question, pk=question_pk, quiz=quiz)
    form = AnswerForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        answer = form.save(commit=False)
        answer.question = question
        answer.save()
        messages.success(request, "Answer added successfully.")
        return redirect("quiz_manage", course_pk=course_pk, chapter_pk=chapter_pk)
    return render(request, "quizzes/answer_form.html", {"form": form, "course": chapter.course, "chapter": chapter, "quiz": quiz, "question": question, "title": "Add Answer"})


@role_required(User.Role.TEACHER)
def answer_update(request, course_pk, chapter_pk, question_pk, answer_pk):
    chapter = get_teacher_chapter_or_404(request.user, course_pk, chapter_pk)
    quiz = get_object_or_404(Quiz, chapter=chapter)
    question = get_object_or_404(Question, pk=question_pk, quiz=quiz)
    answer = get_object_or_404(Answer, pk=answer_pk, question=question)
    form = AnswerForm(request.POST or None, instance=answer)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Answer updated successfully.")
        return redirect("quiz_manage", course_pk=course_pk, chapter_pk=chapter_pk)
    return render(request, "quizzes/answer_form.html", {"form": form, "course": chapter.course, "chapter": chapter, "quiz": quiz, "question": question, "answer": answer, "title": "Update Answer"})


@role_required(User.Role.TEACHER)
def answer_delete(request, course_pk, chapter_pk, question_pk, answer_pk):
    chapter = get_teacher_chapter_or_404(request.user, course_pk, chapter_pk)
    quiz = get_object_or_404(Quiz, chapter=chapter)
    question = get_object_or_404(Question, pk=question_pk, quiz=quiz)
    answer = get_object_or_404(Answer, pk=answer_pk, question=question)
    if request.method == "POST":
        answer.delete()
        messages.success(request, "Answer deleted successfully.")
        return redirect("quiz_manage", course_pk=course_pk, chapter_pk=chapter_pk)
    return render(request, "quizzes/answer_confirm_delete.html", {"course": chapter.course, "chapter": chapter, "quiz": quiz, "question": question, "answer": answer, "title": "Delete Answer"})


@role_required(User.Role.STUDENT)
def quiz_attempt(request, course_pk, chapter_pk):
    chapter = get_student_chapter_or_404(course_pk, chapter_pk)
    quiz = get_object_or_404(
        Quiz.objects.select_related("chapter", "chapter__course").prefetch_related("questions__answers"),
        chapter=chapter,
    )
    if not quiz.questions.exists():
        messages.info(request, "This quiz does not have any questions yet.")
        return redirect("chapter_detail", course_pk=course_pk, pk=chapter_pk)

    existing_attempt = QuizAttempt.objects.filter(quiz=quiz, student=request.user).first()
    if existing_attempt:
        messages.info(request, "You have already attempted this quiz.")
        return redirect("quiz_result", course_pk=course_pk, chapter_pk=chapter_pk)

    form = QuizAttemptForm(quiz, request.POST or None)
    questions = quiz.questions.prefetch_related("answers").all()
    if request.method == "POST" and form.is_valid():
        score = 0
        with transaction.atomic():
            attempt = QuizAttempt.objects.create(
                quiz=quiz,
                student=request.user,
                total_questions=questions.count(),
            )
            for question in questions:
                selected_answer = form.selected_answer_for(question)
                is_correct = bool(selected_answer and selected_answer.is_correct)
                if is_correct:
                    score += 1
                QuizAttemptAnswer.objects.create(
                    attempt=attempt,
                    question=question,
                    selected_answer=selected_answer,
                    is_correct=is_correct,
                )
            attempt.score = score
            attempt.save(update_fields=["score"])
        messages.success(request, "Quiz submitted successfully.")
        return redirect("quiz_result", course_pk=course_pk, chapter_pk=chapter_pk)

    context = {
        "title": quiz.title,
        "course": chapter.course,
        "chapter": chapter,
        "quiz": quiz,
        "form": form,
        "question_fields": [(question, form[f"question_{question.pk}"]) for question in questions],
    }
    return render(request, "quizzes/quiz_attempt.html", context)


@role_required(User.Role.STUDENT)
def quiz_result(request, course_pk, chapter_pk):
    chapter = get_student_chapter_or_404(course_pk, chapter_pk)
    quiz = get_object_or_404(Quiz.objects.select_related("chapter", "chapter__course"), chapter=chapter)
    attempt = get_object_or_404(
        QuizAttempt.objects.select_related("quiz", "student").prefetch_related(
            "attempt_answers__question",
            "attempt_answers__selected_answer",
            "attempt_answers__question__answers",
        ),
        quiz=quiz,
        student=request.user,
    )
    context = {
        "title": f"{quiz.title} Result",
        "course": chapter.course,
        "chapter": chapter,
        "quiz": quiz,
        "attempt": attempt,
    }
    return render(request, "quizzes/quiz_result.html", context)
