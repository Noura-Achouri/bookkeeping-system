from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import UserProfile


class RegisterForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'email']


class AvatarForm(forms.ModelForm):
    """Upload / replace the user's profile photo."""

    class Meta:
        model = UserProfile
        fields = ['avatar']

    def clean_avatar(self):
        avatar = self.cleaned_data.get('avatar')
        if not avatar:
            raise forms.ValidationError('Please choose an image file.')
        if avatar.size > 5 * 1024 * 1024:
            raise forms.ValidationError('Image must be smaller than 5 MB.')
        return avatar


class ProfileForm(forms.ModelForm):
    """Edit the user's public profile details from the Profile page."""

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'placeholder': 'First name'}),
            'last_name': forms.TextInput(attrs={'placeholder': 'Last name'}),
            'username': forms.TextInput(attrs={'placeholder': 'Username'}),
            'email': forms.EmailInput(attrs={'placeholder': 'you@example.com'}),
        }

    def clean_username(self):
        username = (self.cleaned_data.get('username') or '').strip()
        if not username:
            raise forms.ValidationError('Username is required.')
        if User.objects.filter(username__iexact=username).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('That username is already taken.')
        return username

    def clean_email(self):
        email = (self.cleaned_data.get('email') or '').strip()
        if email and User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('That email address is already in use.')
        return email
