from django import forms
from django.contrib.auth import authenticate

from .models import User


class UserRegistrationForm(forms.ModelForm):
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ["first_name", "last_name", "username", "email", "role", "password"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["role"].choices = [
            choice for choice in User.Role.choices if choice[0] != User.Role.ADMIN
        ]
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"
        self.fields["role"].widget.attrs["class"] = "form-select"

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if user.role == User.Role.ADMIN:
            user.is_staff = True
        if commit:
            user.save()
        return user


class UserLoginForm(forms.Form):
    username = forms.CharField(max_length=150)
    password = forms.CharField(widget=forms.PasswordInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"

    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get("username")
        password = cleaned_data.get("password")

        if username and password:
            user = authenticate(username=username, password=password)
            if user is None:
                raise forms.ValidationError("Invalid username or password.")
            cleaned_data["user"] = user
        return cleaned_data
