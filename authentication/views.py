"""
Authentication views.

Design principles applied:
- Views are thin — validation in serializers, business logic in services.
- All responses use `core.responses` helpers for a consistent envelope.
- `AuthRateThrottle` is applied to every endpoint to prevent brute-force.
- `get_user_model()` is used, never a direct import of User.
- User enumeration is prevented on ForgotPassword (always returns 200).
"""

import logging

from django.contrib.auth import get_user_model
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from core.responses import success_response, created_response, error_response
from core.throttles import AuthRateThrottle
from .models import OTPRecord, OTPPurpose
from .serializers import (
    RegisterSerializer,
    VerifyOTPSerializer,
    ResendOTPSerializer,
    ForgotPasswordSerializer,
    ResetPasswordSerializer,
)
from .services import send_otp_email

logger = logging.getLogger(__name__)
User = get_user_model()


class RegisterView(generics.CreateAPIView):
    """
    POST /api/v1/auth/register/

    Creates a new user and sends a verification OTP to their email.
    """

    queryset = User.objects.all()
    permission_classes = (AllowAny,)
    throttle_classes = (AuthRateThrottle,)
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        send_otp_email(user, purpose=OTPPurpose.REGISTRATION)
        logger.info("New user registered: %s", user.email)
        return created_response(message="Account created. Please check your email for the verification code.")


class VerifyOTPView(APIView):
    """
    POST /api/v1/auth/verify-otp/

    Verifies the registration OTP. On success, marks the email as verified
    and returns a fresh JWT token pair.
    """

    permission_classes = (AllowAny,)
    throttle_classes = (AuthRateThrottle,)

    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        code = serializer.validated_data["code"]

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return error_response("No account found with this email address.", status=status.HTTP_404_NOT_FOUND)

        otp_record = (
            OTPRecord.objects
            .filter(user=user, code=code, purpose=OTPPurpose.REGISTRATION, is_used=False)
            .last()
        )

        if not otp_record or not otp_record.is_valid():
            return error_response("Invalid or expired verification code.")

        otp_record.is_used = True
        otp_record.save(update_fields=["is_used"])

        user.is_email_verified = True
        user.save(update_fields=["is_email_verified"])

        refresh = RefreshToken.for_user(user)
        logger.info("Email verified for user: %s", user.email)

        return success_response(
            data={
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            },
            message="Email verified successfully.",
        )


class ResendOTPView(APIView):
    """
    POST /api/v1/auth/resend-otp/

    Resends a registration verification OTP.
    """

    permission_classes = (AllowAny,)
    throttle_classes = (AuthRateThrottle,)

    def post(self, request):
        serializer = ResendOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return error_response("No account found with this email address.", status=status.HTTP_404_NOT_FOUND)

        if user.is_email_verified:
            return error_response("This email address is already verified.")

        send_otp_email(user, purpose=OTPPurpose.REGISTRATION)
        return success_response(message="Verification code resent. Please check your email.")


class ForgotPasswordView(APIView):
    """
    POST /api/v1/auth/forgot-password/

    Sends a password-reset OTP.
    Always returns 200 to prevent email enumeration attacks.
    """

    permission_classes = (AllowAny,)
    throttle_classes = (AuthRateThrottle,)

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        try:
            user = User.objects.get(email=email)
            send_otp_email(user, purpose=OTPPurpose.PASSWORD_RESET)
            logger.info("Password reset OTP sent for: %s", email)
        except User.DoesNotExist:
            # Intentionally silent — do not leak whether the email exists
            logger.warning("Password reset attempted for non-existent email: %s", email)

        return success_response(message="If an account with that email exists, a reset code has been sent.")


class ResetPasswordView(APIView):
    """
    POST /api/v1/auth/reset-password/

    Verifies the password-reset OTP and sets the new password.
    """

    permission_classes = (AllowAny,)
    throttle_classes = (AuthRateThrottle,)

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        code = serializer.validated_data["code"]
        new_password = serializer.validated_data["new_password"]

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return error_response("Invalid request.")

        otp_record = (
            OTPRecord.objects
            .filter(user=user, code=code, purpose=OTPPurpose.PASSWORD_RESET, is_used=False)
            .last()
        )

        if not otp_record or not otp_record.is_valid():
            return error_response("Invalid or expired reset code.")

        otp_record.is_used = True
        otp_record.save(update_fields=["is_used"])

        user.set_password(new_password)
        user.save(update_fields=["password"])

        logger.info("Password reset successfully for: %s", user.email)
        return success_response(message="Password has been reset. You can now log in with your new password.")
