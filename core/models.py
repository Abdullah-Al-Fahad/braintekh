"""
Core app — shared base classes, utilities, and exception handling.

Everything that multiple apps need but belongs to no single app lives here.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _


class TimeStampedModel(models.Model):
    """
    Abstract base model that provides self-updating `created_at` and
    `updated_at` fields. Inherit from this in every model.
    """

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ['-created_at']

class Banner(TimeStampedModel):
    title = models.CharField(max_length=255)
    subtitle = models.CharField(max_length=255, blank=True)
    tag = models.CharField(max_length=50, blank=True)
    bg_gradient_start = models.CharField(max_length=7, default="#0F1E2E")
    bg_gradient_end = models.CharField(max_length=7, default="#162A3D")
    image = models.ImageField(upload_to="banners/", null=True, blank=True)
    action_text = models.CharField(max_length=50, blank=True)
    action_url = models.CharField(max_length=255, blank=True)
    target_project_id = models.CharField(max_length=50, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    role = models.CharField(max_length=20, blank=True, help_text="Target role (e.g., INVESTOR). Blank for all.")

    class Meta:
        verbose_name = _("Banner")
        verbose_name_plural = _("Banners")

    def __str__(self):
        return self.title
