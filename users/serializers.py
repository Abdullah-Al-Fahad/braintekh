from rest_framework import serializers
from .models import User


class UserDetailsSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for the authenticated user's core info.
    Used by dj-rest-auth's `/user/` endpoint and JWT payload.
    """

    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = ("id", "email", "first_name", "last_name", "full_name", "role", "is_email_verified")
        read_only_fields = fields  # This endpoint is read-only; updates go through profile endpoints
