from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import PasswordChangeForm, PasswordResetForm, SetPasswordForm

from .models import User


class UserRegistrationForm(forms.ModelForm):
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    phone_number = forms.CharField(
        max_length=20,
        help_text="Include country code, for example +91XXXXXXXXXX.",
    )
    address = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )
    profile_image = forms.ImageField(required=False)
    password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ["first_name", "last_name", "username", "email", "phone_number", "address", "profile_image", "gender", "role", "password"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["role"].choices = [
            choice for choice in User.Role.choices if choice[0] != User.Role.ADMIN
        ]
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"
        self.fields["role"].widget.attrs["class"] = "form-select"
        self.fields["gender"].widget.attrs["class"] = "form-select"

    def clean_phone_number(self):
        phone_number = self.cleaned_data["phone_number"].strip()
        if not phone_number.startswith("+"):
            raise forms.ValidationError("Phone number must include country code and start with '+'.")
        return phone_number

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
                existing_user = User.objects.filter(username=username).first()
                if existing_user and not existing_user.is_active and not existing_user.is_email_verified:
                    raise forms.ValidationError("Please verify your email with the OTP before logging in.")
                if existing_user and existing_user.is_email_verified and not existing_user.is_approved:
                    raise forms.ValidationError("Your account is waiting for admin approval.")
                if existing_user and existing_user.is_email_verified and existing_user.is_approved and not existing_user.is_active:
                    raise forms.ValidationError("Your account is currently blocked. Please contact the administrator.")
                raise forms.ValidationError("Invalid username or password.")
            cleaned_data["user"] = user
        return cleaned_data


class EmailVerificationForm(forms.Form):
    otp = forms.CharField(max_length=6, min_length=6)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["otp"].widget.attrs["class"] = "form-control"


class AdminManagedUserForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "username",
            "email",
            "phone_number",
            "address",
            "profile_image",
            "gender",
            "role",
            "password",
        ]
        widgets = {
            "address": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["role"].choices = [
            choice for choice in User.Role.choices if choice[0] != User.Role.ADMIN
        ]
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"
        self.fields["role"].widget.attrs["class"] = "form-select"
        self.fields["gender"].widget.attrs["class"] = "form-select"

    def clean_phone_number(self):
        phone_number = (self.cleaned_data.get("phone_number") or "").strip()
        if phone_number and not phone_number.startswith("+"):
            raise forms.ValidationError("Phone number must include country code and start with '+'.")
        return phone_number

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        user.is_email_verified = True
        user.is_approved = True
        user.is_active = True
        if commit:
            user.save()
        return user


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "username",
            "phone_number",
            "address",
            "profile_image",
            "gender",
        ]
        widgets = {
            "address": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"
        self.fields["gender"].widget.attrs["class"] = "form-select"

    def clean_phone_number(self):
        phone_number = (self.cleaned_data.get("phone_number") or "").strip()
        if phone_number and not phone_number.startswith("+"):
            raise forms.ValidationError("Phone number must include country code and start with '+'.")
        return phone_number


class StyledPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"


class StyledPasswordResetForm(PasswordResetForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"


class StyledSetPasswordForm(SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"
