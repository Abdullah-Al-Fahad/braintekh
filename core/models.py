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
