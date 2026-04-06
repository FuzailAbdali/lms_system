from django.urls import path

from .views import (
    article_approve,
    article_create,
    article_delete,
    article_list,
    article_mark_winner,
    article_update,
)

urlpatterns = [
    path("", article_list, name="article_list"),
    path("submit/", article_create, name="article_create"),
    path("<int:pk>/edit/", article_update, name="article_update"),
    path("<int:pk>/delete/", article_delete, name="article_delete"),
    path("<int:pk>/approve/", article_approve, name="article_approve"),
    path("<int:pk>/winner/", article_mark_winner, name="article_mark_winner"),
]

