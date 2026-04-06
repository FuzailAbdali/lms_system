from django.conf import settings
from django.db import models, transaction


class Article(models.Model):
    class ArticleType(models.TextChoices):
        COURSE = "course", "Course Article"
        CHAPTER = "chapter", "Chapter Article"
        OPEN = "open", "Open Article"

    title = models.CharField(max_length=255)
    content = models.TextField()
    article_type = models.CharField(
        max_length=20,
        choices=ArticleType.choices,
        default=ArticleType.OPEN,
    )
    source = models.CharField(max_length=255, blank=True)
    course = models.ForeignKey(
        "courses.Course",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="articles",
    )
    chapter_name = models.CharField(max_length=255, blank=True)
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="articles",
        limit_choices_to={"role": "student"},
    )
    is_approved = models.BooleanField(default=False)
    is_winner = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        with transaction.atomic():
            if self.article_type != self.ArticleType.COURSE:
                self.course = None
            if self.article_type != self.ArticleType.CHAPTER:
                self.chapter_name = ""
            if self.is_winner:
                Article.objects.exclude(pk=self.pk).update(is_winner=False)
                self.is_approved = True
            super().save(*args, **kwargs)
