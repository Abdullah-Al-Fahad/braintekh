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
from rest_framework.parsers import FormParser, MultiPartParser, JSONParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView

from core.permissions import IsEmailVerified, IsInvestor, IsSponsor
from drf_spectacular.utils import extend_schema, OpenApiResponse

from core.responses import created_response, error_response, success_response
from users.models import RoleChoices
from .models import Document, Industry, InvestorProfile, SavedProfile, SponsorProfile, DocumentTypeChoices, VerificationStatusChoices
from .serializers import (
    DocumentSerializer,
    IndustrySerializer,
    InvestorProfileSerializer,
    SetRoleSerializer,
    SponsorProfileSerializer,
)

logger = logging.getLogger(__name__)


@extend_schema(
    tags=["Profiles & Onboarding"],
    summary="Set User Role",
    description="Sets or updates the initial role of a user (INVESTOR or SPONSOR). Safely handles switching roles if the user made a mistake during onboarding.",
    request={"application/json": {"type": "object", "properties": {"role": {"type": "string", "enum": ["INVESTOR", "SPONSOR"]}}}},
    responses={
        200: OpenApiResponse(description="Role set successfully."),
        400: OpenApiResponse(description="Invalid role.")
    }
)
class SetRoleView(APIView):
    """
    POST /api/v1/profiles/set-role/

    Sets the user's role (INVESTOR or SPONSOR) exactly once.
    Creates the corresponding profile automatically.
    Requires email verification.
    """

    permission_classes = (IsAuthenticated, IsEmailVerified)

    def post(self, request):
        serializer = SetRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_role = serializer.validated_data["role"]

        if request.user.role == new_role:
            return success_response(message=f"Role is already set to {new_role}.")

        # Update the user's role
        request.user.role = new_role
        request.user.save(update_fields=["role"])

        # Handle profile swapping to prevent orphaned data
        if new_role == RoleChoices.INVESTOR:
            SponsorProfile.objects.filter(user=request.user).delete()
            InvestorProfile.objects.get_or_create(user=request.user)
        elif new_role == RoleChoices.SPONSOR:
            InvestorProfile.objects.filter(user=request.user).delete()
            SponsorProfile.objects.get_or_create(user=request.user)

        logger.info("User %s switched/selected role: %s", request.user.email, new_role)
        return success_response(message=f"Role set to {new_role}. You can now complete your profile.")


@extend_schema(
    tags=["Profiles & Onboarding"],
    summary="Investor Onboarding",
    description="Completes the onboarding profile for an Investor.",
    request=InvestorProfileSerializer,
    responses={200: InvestorProfileSerializer}
)
class InvestorOnboardingView(APIView):
    """
    GET  /api/v1/profiles/investor/onboarding/  — Fetch investor profile.
    PATCH /api/v1/profiles/investor/onboarding/ — Update investor profile (partial).

    Accepts multipart/form-data to support profile photo upload.
    """

    permission_classes = (IsAuthenticated, IsEmailVerified, IsInvestor)
    parser_classes = (MultiPartParser, FormParser, JSONParser)

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


@extend_schema(
    tags=["Profiles & Onboarding"],
    summary="Sponsor Onboarding",
    description="Completes the onboarding profile for a Sponsor, including company details.",
    request=SponsorProfileSerializer,
    responses={200: SponsorProfileSerializer}
)
class SponsorOnboardingView(APIView):
    """
    GET  /api/v1/profiles/sponsor/onboarding/  — Fetch sponsor profile.
    PATCH /api/v1/profiles/sponsor/onboarding/ — Update sponsor profile (partial).

    Accepts multipart/form-data to support profile photo upload.
    """

    permission_classes = (IsAuthenticated, IsEmailVerified, IsSponsor)
    parser_classes = (MultiPartParser, FormParser, JSONParser)

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


@extend_schema(
    tags=["Profiles & Onboarding"],
    summary="Upload Profile Document",
    description="Uploads a generic document (e.g., pitch deck, portfolio) to the user's profile.",
    request=DocumentSerializer,
    responses={201: DocumentSerializer}
)
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


@extend_schema(
    tags=["Profiles"],
    summary="Get Public Profile",
    description="Retrieves the public profile of any verified user by their ID.",
    responses={
        200: OpenApiResponse(description="Returns InvestorProfileSerializer or SponsorProfileSerializer"),
        404: OpenApiResponse(description="Profile not found or not verified.")
    }
)
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
            
        if request.user.is_authenticated:
            data['is_saved'] = SavedProfile.objects.filter(user=request.user, saved_user=user).exists()
        else:
            data['is_saved'] = False
            
        return success_response(data=data)

@extend_schema(
    tags=["Profiles"],
    summary="Toggle Bookmark / Save Profile",
    description="Saves or unsaves a user's profile. Used for bookmarking investors or sponsors.",
    responses={200: OpenApiResponse(description="Profile saved / removed from saved.")}
)
class ToggleSavedProfileView(APIView):
    """
    POST /api/v1/profiles/<user_id>/save/
    Toggle bookmarking a user profile.
    """
    permission_classes = (IsAuthenticated,)

    def post(self, request, user_id):
        User = get_user_model()
        target_user = get_object_or_404(User, pk=user_id)
        
        if target_user == request.user:
            return error_response("You cannot save your own profile.")
            
        saved_profile, created = SavedProfile.objects.get_or_create(user=request.user, saved_user=target_user)
        
        if not created:
            saved_profile.delete()
            return success_response(message="Profile removed from saved list.")
            
        return success_response(message="Profile saved successfully.")

@extend_schema(
    tags=["Profiles & Onboarding"],
    summary="Upload Verification Document (KYC)",
    description="Uploads identity documents for manual admin KYC verification.",
    request=DocumentSerializer,
    responses={201: OpenApiResponse(description="Document uploaded successfully. Verification is pending.")}
)
class VerificationDocumentUploadView(APIView):
    """
    POST /api/v1/profiles/verification-documents/
    Upload business licenses, tax documents, etc. for compliance.
    """
    permission_classes = (IsAuthenticated, IsEmailVerified, IsSponsor)
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        file_obj = request.data.get('file')
        document_type = request.data.get('document_type')
        
        if not file_obj:
            return error_response("A file is required.")
            
        if document_type not in dict(DocumentTypeChoices.choices):
            return error_response(f"Invalid document_type. Must be one of {list(dict(DocumentTypeChoices.choices).keys())}")
            
        # Create the document linked to the User
        Document.objects.create(
            user=request.user,
            document_type=document_type,
            file=file_obj
        )
        
        # If the Sponsor's verification is PENDING or REJECTED, this might trigger a re-review
        profile = request.user.sponsor_profile
        if profile.verification_status != VerificationStatusChoices.PENDING:
            profile.verification_status = VerificationStatusChoices.PENDING
            profile.save(update_fields=['verification_status'])
            
        return created_response(message="Document uploaded successfully. Verification is pending.")


@extend_schema(
    tags=["Profiles"],
    summary="Get Saved Profiles",
    description="Returns a list of all profiles bookmarked by the current user.",
    responses={200: OpenApiResponse(description="List of saved profiles.")}
)
class SavedProfileListView(APIView):
    """
    GET /api/v1/profiles/saved/
    List all user profiles bookmarked by the user.
    """
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        User = get_user_model()
        saved_users = User.objects.filter(saved_by_users__user=request.user)
        
        results = []
        for user in saved_users:
            if user.role == RoleChoices.INVESTOR and hasattr(user, 'investor_profile'):
                data = InvestorProfileSerializer(user.investor_profile).data
                data.pop('ssn_or_ein', None)
                data['is_saved'] = True
                results.append(data)
            elif user.role == RoleChoices.SPONSOR and hasattr(user, 'sponsor_profile'):
                data = SponsorProfileSerializer(user.sponsor_profile).data
                data.pop('ssn_or_ein', None)
                data['is_saved'] = True
                results.append(data)
                
        return success_response(data=results)


@extend_schema(
    tags=["Profiles"],
    summary="Get Industries List",
    description="Returns a list of available industries for use in profiles and projects.",
    responses={200: IndustrySerializer(many=True)}
)
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


@extend_schema(
    tags=["Profiles & Onboarding"],
    summary="Check KYC Verification Status",
    description="Returns the current KYC verification status of the user (e.g., PENDING, VERIFIED, REJECTED).",
    responses={200: OpenApiResponse(description="Verification status.")}
)
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
