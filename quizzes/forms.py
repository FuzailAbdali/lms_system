from django import forms

from .models import Answer, Question, Quiz


class QuizForm(forms.ModelForm):
    class Meta:
        model = Quiz
        fields = ["title", "description"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"


class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ["text", "order"]
        widgets = {
            "text": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"


class AnswerForm(forms.ModelForm):
    class Meta:
        model = Answer
        fields = ["text", "is_correct"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["text"].widget.attrs["class"] = "form-control"
        self.fields["is_correct"].widget.attrs["class"] = "form-check-input"


class QuizAttemptForm(forms.Form):
    def __init__(self, quiz, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.quiz = quiz
        questions = quiz.questions.prefetch_related("answers").all()
        for question in questions:
            choices = [(answer.pk, answer.text) for answer in question.answers.all()]
            self.fields[f"question_{question.pk}"] = forms.ChoiceField(
                label=f"Question {question.order}",
                choices=choices,
                widget=forms.RadioSelect,
                required=True,
            )

    def selected_answer_for(self, question):
        answer_id = self.cleaned_data.get(f"question_{question.pk}")
        if not answer_id:
            return None
        return question.answers.filter(pk=answer_id).first()
