from django import forms

from courses.models import Course

from .models import Article


class ArticleForm(forms.ModelForm):
    class Meta:
        model = Article
        fields = ["title", "article_type", "source", "course", "chapter_name", "content"]
        widgets = {
            "content": forms.Textarea(attrs={"rows": 8}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["course"].queryset = Course.objects.select_related("teacher").all()
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"
        self.fields["article_type"].widget.attrs["class"] = "form-select"
        self.fields["source"].help_text = "Enter the source reference for the article topic."
        self.fields["chapter_name"].help_text = "Required only for chapter-based articles."
        self.fields["course"].help_text = "Required only for course-based articles."

    def clean(self):
        cleaned_data = super().clean()
        article_type = cleaned_data.get("article_type")
        course = cleaned_data.get("course")
        chapter_name = (cleaned_data.get("chapter_name") or "").strip()

        if article_type == Article.ArticleType.COURSE and not course:
            self.add_error("course", "Please select a course for a course-based article.")
        if article_type == Article.ArticleType.CHAPTER and not chapter_name:
            self.add_error("chapter_name", "Please enter a chapter name for a chapter-based article.")

        return cleaned_data
