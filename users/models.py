"""
Custom User model.

Uses email as the primary identifier (no username field).
Extends AbstractUser to retain all built-in Django auth behaviour
(permissions, groups, password hashing, etc.).
"""

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
    """
    Manager for the custom User model.
    Provides create_user and create_superuser factory methods.
    """

    use_in_migrations = True

    def _create_user(self, email: str, password: str, **extra_fields):
        """Shared logic for all user creation paths."""
        if not email:
            raise ValueError(_("An email address is required."))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email: str, password: str = None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email: str, password: str = None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Superuser must have is_staff=True."))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Superuser must have is_superuser=True."))

        return self._create_user(email, password, **extra_fields)


class RoleChoices(models.TextChoices):
    SPONSOR = "SPONSOR", _("Sponsor")
    INVESTOR = "INVESTOR", _("Investor")
    NONE = "NONE", _("None")


class User(AbstractUser):
    """
    Project-wide User model.

    Key design decisions:
    - Email is the login identifier, not username.
    - `role` drives which profile and onboarding flow applies.
    - `is_email_verified` is set to True only after successful OTP verification.
    """

    username = None  # Disable the default username field

    email = models.EmailField(_("email address"), unique=True, db_index=True)
    first_name = models.CharField(_("first name"), max_length=150)
    last_name = models.CharField(_("last name"), max_length=150)

    role = models.CharField(
        max_length=20,
        choices=RoleChoices.choices,
        default=RoleChoices.NONE,
        db_index=True,
    )
    is_email_verified = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    objects = UserManager()

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")

    def __str__(self) -> str:
        return self.email

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()
