from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Profile


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def ensure_profile(sender, instance, created, **kwargs):
    """Every user has exactly one profile, including superusers made on the CLI."""
    if created:
        Profile.objects.create(user=instance)
    elif not Profile.objects.filter(user=instance).exists():
        Profile.objects.create(user=instance)
