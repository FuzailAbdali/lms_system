from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from users.decorators import role_required
from users.models import User

from .forms import ArticleForm
from .models import Article


@login_required
def article_list(request):
    if request.user.is_superuser or request.user.role in [User.Role.ADMIN, User.Role.TEACHER]:
        articles = Article.objects.select_related("student").all()
    else:
        articles = Article.objects.select_related("student").filter(student=request.user)

    winner_article = Article.objects.select_related("student").filter(is_winner=True).first()
    context = {
        "title": "Writing Competition",
        "articles": articles,
        "winner_article": winner_article,
    }
    return render(request, "articles/article_list.html", context)


@role_required(User.Role.STUDENT)
def article_create(request):
    form = ArticleForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        article = form.save(commit=False)
        article.student = request.user
        article.save()
        messages.success(request, "Article submitted successfully.")
        return redirect("article_list")
    return render(request, "articles/article_form.html", {"form": form, "title": "Submit Article"})


@role_required(User.Role.STUDENT)
def article_update(request, pk):
    article = get_object_or_404(Article, pk=pk, student=request.user)
    if article.is_approved:
        messages.error(request, "Approved articles cannot be edited.")
        return redirect("article_list")

    form = ArticleForm(request.POST or None, instance=article)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Article updated successfully.")
        return redirect("article_list")
    return render(request, "articles/article_form.html", {"form": form, "title": "Update Article"})


@role_required(User.Role.STUDENT)
def article_delete(request, pk):
    article = get_object_or_404(Article, pk=pk, student=request.user)
    if article.is_approved:
        messages.error(request, "Approved articles cannot be deleted.")
        return redirect("article_list")

    if request.method == "POST":
        article.delete()
        messages.success(request, "Article deleted successfully.")
        return redirect("article_list")
    return render(request, "articles/article_confirm_delete.html", {"article": article, "title": "Delete Article"})


@login_required
def article_approve(request, pk):
    if not (request.user.is_superuser or request.user.role in [User.Role.ADMIN, User.Role.TEACHER]):
        return redirect("login")

    article = get_object_or_404(Article, pk=pk)
    article.is_approved = True
    article.save(update_fields=["is_approved"])
    messages.success(request, "Article approved successfully.")
    return redirect("article_list")


@login_required
def article_mark_winner(request, pk):
    if not (request.user.is_superuser or request.user.role == User.Role.ADMIN):
        return redirect("login")

    article = get_object_or_404(Article, pk=pk)
    article.is_winner = True
    article.save()
    messages.success(request, "Winner article selected successfully.")
    return redirect("article_list")

