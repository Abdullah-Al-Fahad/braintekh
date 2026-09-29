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
