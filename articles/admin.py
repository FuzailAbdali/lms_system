from django.contrib import admin

from .models import Article


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ("title", "article_type", "source", "student", "is_approved", "is_winner", "created_at")
    list_filter = ("article_type", "is_approved", "is_winner")
    search_fields = ("title", "source", "chapter_name", "student__username", "student__email")
