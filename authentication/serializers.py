"""
Authentication serializers.

Each serializer has one clear job. Validation logic lives here, not in views.
Views stay thin — they only wire serializers to responses.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.utils.translation import gettext_lazy as _
from dj_rest_auth.serializers import LoginSerializer as BaseLoginSerializer
from rest_framework import serializers

User = get_user_model()


class LoginSerializer(BaseLoginSerializer):
    """
    Extends the base dj-rest-auth LoginSerializer.
    Removes the `username` field since we use email-only auth.
    """

    username = None  # Remove the username field entirely


class RegisterSerializer(serializers.ModelSerializer):
    """Validates and creates a new user account."""

    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={"input_type": "password"},
    )

    class Meta:
        model = User
        fields = ("first_name", "last_name", "email", "password")
        extra_kwargs = {
            "first_name": {"required": True},
            "last_name": {"required": True},
        }

    def create(self, validated_data: dict) -> User:
        return User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            first_name=validated_data["first_name"],
            last_name=validated_data["last_name"],
        )


class VerifyOTPSerializer(serializers.Serializer):
    """Validates the fields needed to verify an OTP code."""

    email = serializers.EmailField(required=True)
    code = serializers.CharField(max_length=6, min_length=6, required=True)


class ResendOTPSerializer(serializers.Serializer):
    """Validates the email for which to resend an OTP."""

    email = serializers.EmailField(required=True)


class ForgotPasswordSerializer(serializers.Serializer):
    """Validates the email for a password-reset OTP request."""

    email = serializers.EmailField(required=True)


class ResetPasswordSerializer(serializers.Serializer):
    """Validates the OTP and new password for a password reset."""

    email = serializers.EmailField(required=True)
    code = serializers.CharField(max_length=6, min_length=6, required=True)
    new_password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={"input_type": "password"},
    )
