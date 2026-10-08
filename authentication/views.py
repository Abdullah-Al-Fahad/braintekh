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
from drf_spectacular.utils import extend_schema, OpenApiResponse

from core.responses import success_response, created_response, error_response
from core.throttles import AuthRateThrottle
from users.serializers import UserDetailsSerializer
from .models import OTPRecord, OTPPurpose
from .serializers import (
    RegisterSerializer,
    VerifyOTPSerializer,
    ResendOTPSerializer,
    ForgotPasswordSerializer,
    ResetPasswordSerializer,
)
from .services import send_otp_email
from .social import verify_google_token, verify_apple_token

logger = logging.getLogger(__name__)
User = get_user_model()


@extend_schema(
    tags=["Authentication"],
    summary="Register a new user",
    description="Creates a new user account and triggers an email verification OTP. The password should be strong and include at least 8 characters.",
    responses={
        201: OpenApiResponse(description="User registered successfully. An OTP has been sent."),
        400: OpenApiResponse(description="Validation Error")
    }
)
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


@extend_schema(
    tags=["Authentication"],
    summary="Verify Email OTP",
    description="Verifies the OTP sent to the user's email during registration, login, or password reset.",
    request=VerifyOTPSerializer,
    responses={
        200: OpenApiResponse(description="OTP verified successfully. Returns JWT access and refresh tokens if it's a login/registration OTP."),
        400: OpenApiResponse(description="Invalid OTP or expired")
    }
)
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
                "user": UserDetailsSerializer(user, context={"request": request}).data,
            },
            message="Email verified successfully.",
        )


@extend_schema(
    tags=["Authentication"],
    summary="Resend OTP",
    description="Resends a 6-digit OTP to the user's email address if the previous one expired.",
    request=ResendOTPSerializer,
    responses={
        200: OpenApiResponse(description="OTP resent successfully."),
        400: OpenApiResponse(description="Validation error or user not found")
    }
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


@extend_schema(
    tags=["Authentication"],
    summary="Request Password Reset",
    description="Sends an OTP to the user's email address to initiate a password reset process.",
    request=ForgotPasswordSerializer,
    responses={
        200: OpenApiResponse(description="Password reset OTP sent to email."),
        400: OpenApiResponse(description="Validation error")
    }
)
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


@extend_schema(
    tags=["Authentication"],
    summary="Reset Password with OTP",
    description="Resets the user's password using the OTP received via email.",
    request=ResetPasswordSerializer,
    responses={
        200: OpenApiResponse(description="Password has been reset successfully."),
        400: OpenApiResponse(description="Invalid OTP or passwords do not match")
    }
)
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

class GoogleLoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]

    def post(self, request, *args, **kwargs):
        id_token_str = request.data.get('id_token')
        if not id_token_str:
            return error_response("id_token is required", status=status.HTTP_400_BAD_REQUEST)
            
        idinfo = verify_google_token(id_token_str)
        if not idinfo:
            return error_response("Invalid Google token", status=status.HTTP_401_UNAUTHORIZED)
            
        email = idinfo.get('email')
        first_name = idinfo.get('given_name', '')
        last_name = idinfo.get('family_name', '')
        
        # Link or create user
        user, created = User.objects.get_or_create(email=email, defaults={
            'first_name': first_name,
            'last_name': last_name,
            'is_email_verified': True,
            'auth_provider': 'google'
        })
        
        if not user.is_email_verified:
            user.is_email_verified = True
            user.save(update_fields=["is_email_verified"])
            
        refresh = RefreshToken.for_user(user)
        return success_response(data={
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "role": user.role,
            "user": UserDetailsSerializer(user).data
        })

class AppleLoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]

    def post(self, request, *args, **kwargs):
        id_token_str = request.data.get('id_token')
        if not id_token_str:
            return error_response("id_token is required", status=status.HTTP_400_BAD_REQUEST)
            
        idinfo = verify_apple_token(id_token_str)
        if not idinfo:
            return error_response("Invalid Apple token", status=status.HTTP_401_UNAUTHORIZED)
            
        email = idinfo.get('email')
        
        # Apple only sends name on the FIRST ever login in a 'user' object
        import json
        first_name = ""
        last_name = ""
        name_json = request.data.get('name_json')
        if name_json:
            try:
                name_data = json.loads(name_json)
                first_name = name_data.get('name', {}).get('firstName', '')
                last_name = name_data.get('name', {}).get('lastName', '')
            except json.JSONDecodeError:
                pass
                
        user, created = User.objects.get_or_create(email=email, defaults={
            'first_name': first_name,
            'last_name': last_name,
            'is_email_verified': True,
            'auth_provider': 'apple'
        })
        
        if not user.is_email_verified:
            user.is_email_verified = True
            user.save(update_fields=["is_email_verified"])
            
        refresh = RefreshToken.for_user(user)
        return success_response(data={
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "role": user.role,
            "user": UserDetailsSerializer(user).data
        })
