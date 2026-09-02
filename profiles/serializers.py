"""
Profile serializers.

Each serializer is focused and has a single responsibility.
User field updates (first_name, last_name) are handled via a mixin
to eliminate the DRY violation that existed in the previous version.
"""

from django.contrib.auth import get_user_model
from rest_framework import serializers

from users.models import RoleChoices
from .models import Document, Industry, InvestorProfile, SponsorProfile

User = get_user_model()


# ---------------------------------------------------------------------------
# Mixins
# ---------------------------------------------------------------------------

class UserFieldsMixin:
    """
    Mixin that adds writable first_name/last_name to a profile serializer
    and handles updating the related User in `.update()`.

    Eliminates the copy-paste update logic between Investor and Sponsor serializers.
    """

    def update(self, instance, validated_data: dict):
        user_data = validated_data.pop("user", {})
        user = instance.user

        # Update User fields if provided
        user_update_fields = []
        for field in ("first_name", "last_name"):
            if field in user_data:
                setattr(user, field, user_data[field])
                user_update_fields.append(field)

        if user_update_fields:
            user.save(update_fields=user_update_fields)

        # Handle M2M separately (cannot use setattr)
        if "industries" in validated_data:
            instance.industries.set(validated_data.pop("industries"))

        # Update remaining profile fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance


# ---------------------------------------------------------------------------
# Serializers
# ---------------------------------------------------------------------------

class SetRoleSerializer(serializers.Serializer):
    """Validates the role selection request."""

    role = serializers.ChoiceField(
        choices=[c for c in RoleChoices.choices if c[0] != RoleChoices.NONE],
        required=True,
    )


class IndustrySerializer(serializers.ModelSerializer):
    """Read-only serializer for listing available industries."""

    class Meta:
        model = Industry
        fields = ("id", "name")


class DocumentSerializer(serializers.ModelSerializer):
    """Handles document uploads and listing."""

    class Meta:
        model = Document
        fields = ("id", "document_type", "file", "created_at")
        read_only_fields = ("id", "created_at")


class InvestorProfileSerializer(UserFieldsMixin, serializers.ModelSerializer):
    """
    Full read/write serializer for the InvestorProfile.

    - first_name / last_name are sourced from User but writable here.
    - email is sourced from User and is always read-only.
    - verification_status is read-only (managed internally by admin/compliance).
    """

    first_name = serializers.CharField(source="user.first_name", required=False)
    last_name = serializers.CharField(source="user.last_name", required=False)
    email = serializers.EmailField(source="user.email", read_only=True)
    industries = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Industry.objects.all(),
        required=False,
    )

    class Meta:
        model = InvestorProfile
        fields = (
            "investor_type",
            "first_name", "last_name", "email",
            "phone", "country", "location",
            "company_name", "position_title", "bio",
            "profile_photo", "industries",
            "verification_status",
            "created_at", "updated_at",
        )
        read_only_fields = ("verification_status", "created_at", "updated_at")


class SponsorProfileSerializer(UserFieldsMixin, serializers.ModelSerializer):
    """
    Full read/write serializer for the SponsorProfile.

    Documents are embedded as read-only nested objects.
    """

    first_name = serializers.CharField(source="user.first_name", required=False)
    last_name = serializers.CharField(source="user.last_name", required=False)
    email = serializers.EmailField(source="user.email", read_only=True)
    documents = DocumentSerializer(source="user.documents", many=True, read_only=True)

    class Meta:
        model = SponsorProfile
        fields = (
            "first_name", "last_name", "email",
            "legal_company_name", "registration_number",
            "business_address", "company_website",
            "phone", "country", "position_title",
            "profile_photo", "verification_status",
            "documents",
            "created_at", "updated_at",
        )
        read_only_fields = ("verification_status", "documents", "created_at", "updated_at")
