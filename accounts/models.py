from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    """Per-user extras that don't belong on the built-in auth User."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Profile of {self.user.username}'
