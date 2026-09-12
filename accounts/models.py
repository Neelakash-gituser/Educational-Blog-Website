from django.conf import settings
from django.db import models
from django.urls import reverse


class Profile(models.Model):
    """Public identity for a user: how they appear as an author or commenter."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile"
    )
    display_name = models.CharField(max_length=80, blank=True)
    headline = models.CharField(
        max_length=140, blank=True, help_text='e.g. "Physics undergrad, writes about optics".'
    )
    bio = models.TextField(max_length=1000, blank=True)
    avatar = models.ImageField(upload_to="avatars", blank=True)
    location = models.CharField(max_length=80, blank=True)
    website = models.URLField(blank=True)
    github = models.CharField(max_length=60, blank=True, help_text="Username only.")
    twitter = models.CharField(max_length=60, blank=True, help_text="Handle without the @.")
    linkedin = models.CharField(max_length=100, blank=True, help_text="Username only.")
    can_write = models.BooleanField(
        default=False,
        help_text="Lets this user write and publish posts from the dashboard.",
    )

    def __str__(self):
        return self.name

    @property
    def name(self):
        return (
            self.display_name
            or self.user.get_full_name().strip()
            or self.user.username
        )

    @property
    def initials(self):
        parts = [p for p in self.name.replace("_", " ").split() if p]
        if not parts:
            return "?"
        if len(parts) == 1:
            return parts[0][:2].upper()
        return (parts[0][0] + parts[-1][0]).upper()

    @property
    def is_author(self):
        return self.can_write or self.user.is_staff

    def get_absolute_url(self):
        return reverse("blog:author", args=[self.user.username])
