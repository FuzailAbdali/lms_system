from django import forms

from courses.models import Course


class StartLiveClassForm(forms.Form):
    course = forms.ModelChoiceField(queryset=Course.objects.none())
    title = forms.CharField(max_length=255)
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 4}),
    )

    def __init__(self, teacher, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.teacher = teacher
        self.fields["course"].queryset = Course.objects.filter(teacher=teacher).order_by("title")
        for field in self.fields.values():
            existing_class = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{existing_class} form-control".strip()
