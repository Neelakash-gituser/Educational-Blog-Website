from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User

from .models import Profile


class SignUpForm(UserCreationForm):
    email = forms.EmailField(
        required=True, widget=forms.EmailInput(attrs={"placeholder": "you@example.com"})
    )
    display_name = forms.CharField(
        max_length=80,
        required=False,
        help_text="Optional. The name shown on your comments and posts.",
    )

    class Meta:
        model = User
        fields = ("username", "email", "display_name", "password1", "password2")

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
            profile = user.profile
            profile.display_name = self.cleaned_data.get("display_name", "")
            profile.save()
        return user


class LoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={"autofocus": True}))


class ProfileForm(forms.ModelForm):
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)
    email = forms.EmailField(required=True)

    class Meta:
        model = Profile
        fields = (
            "display_name",
            "headline",
            "bio",
            "avatar",
            "location",
            "website",
            "github",
            "twitter",
            "linkedin",
        )
        widgets = {
            "bio": forms.Textarea(attrs={"rows": 5}),
            "headline": forms.TextInput(attrs={"placeholder": "Physics undergrad, writes about optics"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = self.instance.user
        self.fields["first_name"].initial = user.first_name
        self.fields["last_name"].initial = user.last_name
        self.fields["email"].initial = user.email

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        clash = User.objects.filter(email__iexact=email).exclude(pk=self.instance.user_id)
        if clash.exists():
            raise forms.ValidationError("Another account already uses this email.")
        return email

    def save(self, commit=True):
        profile = super().save(commit=commit)
        user = profile.user
        user.first_name = self.cleaned_data.get("first_name", "")
        user.last_name = self.cleaned_data.get("last_name", "")
        user.email = self.cleaned_data["email"]
        if commit:
            user.save(update_fields=["first_name", "last_name", "email"])
        return profile
