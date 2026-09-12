from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from core.responses import success_response, error_response
from django.contrib.auth import get_user_model
from .serializers import UserMeSerializer, ChangePasswordSerializer

User = get_user_model()

class MeView(APIView):
    """
    GET /api/v1/users/me/
    PATCH /api/v1/users/me/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserMeSerializer(request.user, context={'request': request})
        return success_response(data=serializer.data)

    def patch(self, request):
        serializer = UserMeSerializer(request.user, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return success_response(data=serializer.data, message="Settings updated successfully.")
        return error_response("Invalid data provided.", data=serializer.errors)

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

class DeleteAccountView(APIView):
    """
    DELETE /api/v1/users/me/
    """
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        user = request.user
        user.delete()
        return success_response(message="Account deleted successfully.")
