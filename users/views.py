from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from core.responses import success_response, error_response
from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema, OpenApiResponse
from .serializers import UserDetailsSerializer, UserMeSerializer, ChangePasswordSerializer

User = get_user_model()

@extend_schema(
    tags=["User Settings"],
    summary="Get Current User Profile & Stats",
    description="Returns the current authenticated user's core data, nested role-specific profile (Sponsor or Investor), and aggregated platform statistics.",
    responses={200: UserMeSerializer}
)
class MeView(APIView):
    """
    GET /api/v1/users/me/
    PATCH /api/v1/users/me/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserMeSerializer(request.user, context={'request': request})
        return success_response(data=serializer.data)

    @extend_schema(
        tags=["User Settings"],
        summary="Update Current User Settings",
        description="Updates core user settings like push notifications and subscription tier.",
        request=UserDetailsSerializer,
        responses={200: UserDetailsSerializer}
    )
    def patch(self, request):
        serializer = UserMeSerializer(request.user, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return success_response(data=serializer.data, message="Settings updated successfully.")
        return error_response("Invalid data provided.", data=serializer.errors)

@extend_schema(
    tags=["User Settings"],
    summary="Change Password",
    description="Changes the authenticated user's password. Requires the old password and a new, strong password.",
    request=ChangePasswordSerializer,
    responses={
        200: OpenApiResponse(description="Password changed successfully."),
        400: OpenApiResponse(description="Invalid old password or weak new password.")
    }
)
class ChangePasswordView(APIView):
    """
    POST /api/v1/users/change-password/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            request.user.set_password(serializer.validated_data['new_password'])
            request.user.save()
            return success_response(message="Password changed successfully.")
        return error_response("Password change failed.", data=serializer.errors)

@extend_schema(
    tags=["User Settings"],
    summary="Delete Account",
    description="Permanently deletes the authenticated user's account and all associated data.",
    responses={200: OpenApiResponse(description="Account deleted successfully.")}
)
class DeleteAccountView(APIView):
    """
    DELETE /api/v1/users/me/
    """
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        user = request.user
        user.delete()
        return success_response(message="Account deleted successfully.")

@extend_schema(
    tags=["User Settings"],
    summary="Switch Active Role",
    description="Switches the user's active role between SPONSOR and INVESTOR. Returns a specific error code if the requested profile doesn't exist yet, prompting the frontend to launch the onboarding flow.",
    request={"application/json": {"type": "object", "properties": {"role": {"type": "string", "enum": ["SPONSOR", "INVESTOR"]}}}},
    responses={
        200: OpenApiResponse(description="Role switched successfully."),
        400: OpenApiResponse(description="Invalid role or missing profile. (Check error_code='PROFILE_MISSING')")
    }
)
class SwitchRoleView(APIView):
    """
    POST /api/v1/users/switch-role/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        new_role = request.data.get('role')
        
        if new_role not in ['SPONSOR', 'INVESTOR']:
            return error_response("Invalid role. Must be SPONSOR or INVESTOR.")
            
        if new_role == request.user.role:
            return success_response(message=f"Role is already {new_role}.")
            
        is_onboarded = True
        
        # Check and bootstrap profile if missing
        if new_role == 'SPONSOR' and not hasattr(request.user, 'sponsor_profile'):
            from profiles.models import SponsorProfile
            SponsorProfile.objects.create(user=request.user)
            is_onboarded = False
            
        elif new_role == 'INVESTOR' and not hasattr(request.user, 'investor_profile'):
            from profiles.models import InvestorProfile
            InvestorProfile.objects.create(user=request.user)
            is_onboarded = False
            
        # Switch the active role
        request.user.role = new_role
        request.user.save(update_fields=['role'])
        
        # Generate new tokens since role changed
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(request.user)
        
        # Get profile data for the new role
        profile = getattr(request.user, f"{new_role.lower()}_profile")
        account_type = getattr(profile, f"{new_role.lower()}_type", "NONE")
        
        # Override is_onboarded if they have an empty profile but we didn't just create it
        if account_type == "NONE":
            is_onboarded = False
            
        from .serializers import UserMeSerializer
        
        return success_response(
            message=f"Switched to {new_role} mode successfully.",
            data={
                "active_role": new_role,
                "is_onboarded": is_onboarded,
                "verification_status": profile.verification_status,
                "account_type": account_type,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": UserMeSerializer(request.user, context={'request': request}).data
            }
        )

@extend_schema(
    tags=["Auth & Users"],
    summary="Delete Account",
    description="Soft-deletes the user's account and anonymizes data. Also terminates active projects for sponsors.",
    request={"application/json": {"type": "object", "properties": {"password": {"type": "string"}, "confirmation": {"type": "string"}}}},
    responses={200: OpenApiResponse(description="Account deleted successfully.")}
)
class DeleteAccountView(APIView):
    """
    POST /api/v1/users/delete-account/
    """
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        user = request.user
        password = request.data.get("password")
        
        if not password:
            return error_response("Password is required to delete your account.", status=400)
            
        if not user.check_password(password):
            return error_response("Incorrect password. Please verify and try again.", status=400)
            
        # Terminate active projects if Sponsor
        if user.role == 'SPONSOR':
            from projects.models import Project, ProjectStatusChoices
            from django.utils import timezone
            active_projects = Project.objects.filter(sponsor__user=user, status=ProjectStatusChoices.ACTIVE)
            for project in active_projects:
                project.status = ProjectStatusChoices.TERMINATED
                project.termination_reason = "Account deleted by sponsor."
                project.terminated_at = timezone.now()
                project.save(update_fields=['status', 'termination_reason', 'terminated_at'])
                
        # Soft delete and anonymize
        from django.utils import timezone
        import uuid
        
        user.is_active = False
        user.deleted_at = timezone.now()
        user.email = f"deleted_{uuid.uuid4().hex[:8]}_{user.email}"
        # Clear push notifications tokens if using FCMDevice
        try:
            from notifications.models import FCMDevice
            FCMDevice.objects.filter(user=user).delete()
        except ImportError:
            pass
            
        user.save()
        
        return success_response(message="Account has been deleted successfully. You have been logged out.")
