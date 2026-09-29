"""
Profile models for Investors and Sponsors.

Design decisions:
- All models inherit from `core.TimeStampedModel` (DRY — no repeated created_at/updated_at).
- `VerificationStatusChoices` is shared between both profiles.
- The `Industry` model is normalized so industries can be managed from the admin panel.
- `Document` is linked to the `User`, not a specific profile, to keep things flexible.
- DB indexes are added to all fields used in common query patterns.
"""

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import TimeStampedModel


class VerificationStatusChoices(models.TextChoices):
    PENDING = "PENDING", _("Pending")
    APPROVED = "APPROVED", _("Approved")
    REJECTED = "REJECTED", _("Rejected")


class InvestorTypeChoices(models.TextChoices):
    INDIVIDUAL = "INDIVIDUAL", _("Individual")
    COMPANY = "COMPANY", _("Company")
    NONE = "NONE", _("None")


class SponsorTypeChoices(models.TextChoices):
    INDIVIDUAL = "INDIVIDUAL", _("Individual")
    COMPANY = "COMPANY", _("Company")
    NONE = "NONE", _("None")


class DocumentTypeChoices(models.TextChoices):
    BUSINESS_LICENSE = "BUSINESS_LICENSE", _("Business License")
    TAX_DOCUMENT = "TAX_DOCUMENT", _("Tax Document")
    OTHER = "OTHER", _("Other")


class SavedProfile(TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="saved_profiles",
    )
    saved_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="saved_by_users",
    )

    class Meta:
        verbose_name = _("Saved Profile")
        verbose_name_plural = _("Saved Profiles")
        unique_together = ("user", "saved_user")

    def __str__(self) -> str:
        return f"{self.user.email} saved {self.saved_user.email}"


class Industry(models.Model):
    """
    A normalized list of industries managed from the admin panel.
    Users select from this list during onboarding.
    """

    name = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name = _("Industry")
        verbose_name_plural = _("Industries")
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class InvestorProfile(TimeStampedModel):
    """
    Profile data specific to Investor users.

    Stores both individual and company investor information.
    The `investor_type` field determines which fields are relevant.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="investor_profile",
    )
    investor_type = models.CharField(
        max_length=20,
        choices=InvestorTypeChoices.choices,
        default=InvestorTypeChoices.NONE,
        db_index=True,
    )

    # Company Verification Fields (if investor_type == COMPANY)
    legal_company_name = models.CharField(max_length=255, blank=True)
    registration_number = models.CharField(max_length=100, blank=True)
    business_address = models.TextField(blank=True)
    company_website = models.URLField(max_length=500, blank=True)

    # Contact & Location
    phone = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, blank=True)
    location = models.CharField(max_length=255, blank=True)

    # Professional Info
    company_name = models.CharField(max_length=255, blank=True, help_text="Optional for Individual investors.")
    position_title = models.CharField(max_length=255, blank=True)
    bio = models.TextField(blank=True)
    profile_photo = models.ImageField(upload_to="profile_photos/investors/", null=True, blank=True)

    # Platform preferences
    industries = models.ManyToManyField(Industry, blank=True, related_name="investors")

    # Compliance
    verification_status = models.CharField(
        max_length=20,
        choices=VerificationStatusChoices.choices,
        default=VerificationStatusChoices.PENDING,
        db_index=True,
    )

    class Meta:
        verbose_name = _("Investor Profile")
        verbose_name_plural = _("Investor Profiles")

    def __str__(self) -> str:
        return f"Investor Profile — {self.user.email}"


class SponsorProfile(TimeStampedModel):
    """
    Profile data specific to Sponsor (project publisher) users.

    Contains company verification data required by compliance.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sponsor_profile",
    )
    sponsor_type = models.CharField(
        max_length=20,
        choices=SponsorTypeChoices.choices,
        default=SponsorTypeChoices.NONE,
        db_index=True,
    )

    # Company Verification Fields
    legal_company_name = models.CharField(max_length=255, blank=True)
    registration_number = models.CharField(max_length=100, blank=True)
    business_address = models.TextField(blank=True)
    company_website = models.URLField(max_length=500, blank=True)

    # Personal / Contact Info
    phone = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, blank=True)
    location = models.CharField(max_length=255, blank=True)
    position_title = models.CharField(max_length=255, blank=True)
    bio = models.TextField(blank=True)
    profile_photo = models.ImageField(upload_to="profile_photos/sponsors/", null=True, blank=True)

    # Compliance
    verification_status = models.CharField(
        max_length=20,
        choices=VerificationStatusChoices.choices,
        default=VerificationStatusChoices.PENDING,
        db_index=True,
    )

    class Meta:
        verbose_name = _("Sponsor Profile")
        verbose_name_plural = _("Sponsor Profiles")

    def __str__(self) -> str:
        return f"Sponsor Profile — {self.user.email}"


class Document(TimeStampedModel):
    """
    Uploaded verification documents (e.g., business license, tax documents).

    Linked to the User rather than a specific profile for flexibility.
    The `document_type` distinguishes between document categories.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    document_type = models.CharField(max_length=50, choices=DocumentTypeChoices.choices, db_index=True)
    file = models.FileField(upload_to="documents/%Y/%m/")  # Organised by year/month

    class Meta:
        verbose_name = _("Document")
        verbose_name_plural = _("Documents")
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.get_document_type_display()} — {self.user.email}"
