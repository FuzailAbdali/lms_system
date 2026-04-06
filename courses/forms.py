from django import forms

from .models import Chapter, Course


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ["title", "description"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 5}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"


class ChapterForm(forms.ModelForm):
    class Meta:
        model = Chapter
        fields = ["title", "content", "order"]
        widgets = {
            "content": forms.Textarea(attrs={"rows": 7}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"
