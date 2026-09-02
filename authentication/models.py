"""
OTP model for email verification and password reset flows.

Design decisions:
- Uses `secrets` module (cryptographically secure) instead of `random`.
- Has a DB index on (user, purpose, is_used) to make OTP lookups fast.
- Expiry is driven by `settings.OTP_EXPIRY_MINUTES` — not hardcoded.
- `is_valid()` is a pure method — no side effects.
"""

import secrets
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.models import TimeStampedModel


class OTPPurpose(models.TextChoices):
    REGISTRATION = "REGISTRATION", _("Registration")
    PASSWORD_RESET = "PASSWORD_RESET", _("Password Reset")


def _generate_otp_code() -> str:
    """Generate a cryptographically secure 6-digit numeric OTP."""
    return str(secrets.randbelow(1_000_000)).zfill(6)


class OTPRecord(TimeStampedModel):
    """
    Stores a one-time password tied to a user and a specific purpose.

    Lookup pattern: filter(user=user, purpose=purpose, is_used=False)
    Always call `.last()` and then `.is_valid()` before accepting the code.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="otps",
    )
    code = models.CharField(max_length=6, default=_generate_otp_code)
    purpose = models.CharField(max_length=20, choices=OTPPurpose.choices, db_index=True)
    is_used = models.BooleanField(default=False, db_index=True)

    class Meta:
        verbose_name = _("OTP Record")
        verbose_name_plural = _("OTP Records")
        # Composite index matches our most common query pattern
        indexes = [
            models.Index(fields=["user", "purpose", "is_used"], name="otp_lookup_idx"),
        ]

    def is_valid(self) -> bool:
        """Return True if the OTP has not been used and has not expired."""
        expiry = self.created_at + timedelta(minutes=settings.OTP_EXPIRY_MINUTES)
        return not self.is_used and timezone.now() <= expiry

    def __str__(self) -> str:
        return f"OTP({self.purpose}) for {self.user.email}"
