"""
Profile views.

Design principles applied:
- Role-based access uses the `IsInvestor` / `IsSponsor` permission classes from
  `core.permissions` — no manual role-checking in view code.
- `get_object_or_404` replaces manual try/except on profile lookups.
- The Investor and Sponsor onboarding views share the same structure — a GET
  to retrieve, a PATCH to update.
- All responses use `core.responses` helpers.
- File uploads are handled via `MultiPartParser` + `FormParser`.
"""

import logging

from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView

from core.permissions import IsEmailVerified, IsInvestor, IsSponsor
from core.responses import created_response, error_response, success_response
from users.models import RoleChoices
from .models import Document, Industry, InvestorProfile, SponsorProfile
from .serializers import (
    DocumentSerializer,
    IndustrySerializer,
    InvestorProfileSerializer,
    SetRoleSerializer,
    SponsorProfileSerializer,
)

logger = logging.getLogger(__name__)


class SetRoleView(APIView):
    """
    POST /api/v1/profiles/set-role/

    Sets the user's role (INVESTOR or SPONSOR) exactly once.
    Creates the corresponding profile automatically.
    Requires email verification.
    """

    permission_classes = (IsAuthenticated, IsEmailVerified)

    def post(self, request):
        if request.user.role != RoleChoices.NONE:
            return error_response("Your role has already been set and cannot be changed.")

        serializer = SetRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        role = serializer.validated_data["role"]

        request.user.role = role
        request.user.save(update_fields=["role"])

        # Create the matching profile — idempotent via get_or_create
        if role == RoleChoices.INVESTOR:
            InvestorProfile.objects.get_or_create(user=request.user)
        elif role == RoleChoices.SPONSOR:
            SponsorProfile.objects.get_or_create(user=request.user)

        logger.info("User %s selected role: %s", request.user.email, role)
        return success_response(message=f"Role set to {role}. You can now complete your profile.")


class InvestorOnboardingView(APIView):
    """
    GET  /api/v1/profiles/investor/onboarding/  — Fetch investor profile.
    PATCH /api/v1/profiles/investor/onboarding/ — Update investor profile (partial).

    Accepts multipart/form-data to support profile photo upload.
    """

    permission_classes = (IsAuthenticated, IsEmailVerified, IsInvestor)
    parser_classes = (MultiPartParser, FormParser)

    def _get_profile(self, user) -> InvestorProfile:
        return get_object_or_404(InvestorProfile, user=user)

    def get(self, request):
        profile = self._get_profile(request.user)
        serializer = InvestorProfileSerializer(profile)
        return success_response(data=serializer.data)

    def patch(self, request):
        profile = self._get_profile(request.user)
        serializer = InvestorProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        logger.info("Investor profile updated for: %s", request.user.email)
        return success_response(data=serializer.data, message="Profile updated successfully.")


class SponsorOnboardingView(APIView):
    """
    GET  /api/v1/profiles/sponsor/onboarding/  — Fetch sponsor profile.
    PATCH /api/v1/profiles/sponsor/onboarding/ — Update sponsor profile (partial).

    Accepts multipart/form-data to support profile photo upload.
    """

    permission_classes = (IsAuthenticated, IsEmailVerified, IsSponsor)
    parser_classes = (MultiPartParser, FormParser)

    def _get_profile(self, user) -> SponsorProfile:
        return get_object_or_404(SponsorProfile, user=user)

    def get(self, request):
        profile = self._get_profile(request.user)
        serializer = SponsorProfileSerializer(profile)
        return success_response(data=serializer.data)

    def patch(self, request):
        profile = self._get_profile(request.user)
        serializer = SponsorProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        logger.info("Sponsor profile updated for: %s", request.user.email)
        return success_response(data=serializer.data, message="Profile updated successfully.")


class DocumentUploadView(APIView):
    """
    POST /api/v1/profiles/documents/upload/

    Uploads a verification document (PDF, JPG, PNG up to 5 MB).
    Requires email verification.
    """

    permission_classes = (IsAuthenticated, IsEmailVerified)
    parser_classes = (MultiPartParser, FormParser)

    MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB
    ALLOWED_CONTENT_TYPES = ("application/pdf", "image/jpeg", "image/png")

    def post(self, request):
        file = request.FILES.get("file")
        if file:
            if file.size > self.MAX_FILE_SIZE_BYTES:
                return error_response("File size must not exceed 5 MB.")
            if file.content_type not in self.ALLOWED_CONTENT_TYPES:
                return error_response("Only PDF, JPG, and PNG files are accepted.")

        serializer = DocumentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)
        logger.info("Document uploaded by: %s", request.user.email)
        return created_response(data=serializer.data, message="Document uploaded successfully.")


class PublicProfileDetailView(APIView):
    """
    GET /api/v1/profiles/<user_id>/
    View another user's public profile information (e.g. before sending a message).
    """
    permission_classes = (AllowAny,)

    def get(self, request, user_id):
        User = get_user_model()
        user = get_object_or_404(User, pk=user_id)
        
        # Determine role and return appropriate serializer
        if user.role == RoleChoices.INVESTOR and hasattr(user, 'investor_profile'):
            data = InvestorProfileSerializer(user.investor_profile).data
            # Filter sensitive fields for public view
            data.pop('ssn_or_ein', None)
        elif user.role == RoleChoices.SPONSOR and hasattr(user, 'sponsor_profile'):
            data = SponsorProfileSerializer(user.sponsor_profile).data
            data.pop('ssn_or_ein', None)
        else:
            return error_response("Profile not found or incomplete.", status_code=status.HTTP_404_NOT_FOUND)
            
        return success_response(data=data)


class IndustryListView(APIView):
    """
    GET /api/v1/profiles/industries/

    Returns all available industries. Used to populate the multi-select
    onboarding screen for investors.
    """

    permission_classes = (IsAuthenticated,)

    def get(self, request):
        industries = Industry.objects.all()
        serializer = IndustrySerializer(industries, many=True)
        return success_response(data=serializer.data)


class VerificationStatusView(APIView):
    """
    GET /api/v1/profiles/verification-status/

    Returns the user's current compliance verification status.
    Maps to the "Verification Pending" screen in the app.
    """

    permission_classes = (IsAuthenticated, IsEmailVerified)

    def get(self, request):
        user = request.user

        if user.role == RoleChoices.INVESTOR:
            profile = get_object_or_404(InvestorProfile, user=user)
        elif user.role == RoleChoices.SPONSOR:
            profile = get_object_or_404(SponsorProfile, user=user)
        else:
            return error_response("Please select your role before checking verification status.")

        return success_response(data={
            "role": user.role,
            "verification_status": profile.verification_status,
        })
