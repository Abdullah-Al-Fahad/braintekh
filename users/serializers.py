from rest_framework import serializers
from .models import RoleChoices, User


class UserDetailsSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for the authenticated user's core info.
    Used by dj-rest-auth's `/user/` endpoint and JWT payload.
    """

    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = ("id", "first_name", "last_name", "full_name", "email", "role", "is_email_verified", "push_notifications_enabled", "subscription_tier")
        read_only_fields = ("id", "email", "is_email_verified")


class UserMeSerializer(serializers.ModelSerializer):
    """
    Serializer for the GET /me/ endpoint. Includes nested profiles and stats.
    """
    profile = serializers.SerializerMethodField()
    stats = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ("id", "first_name", "last_name", "email", "role", "is_email_verified", 
                  "push_notifications_enabled", "subscription_tier", "profile", "stats")
        read_only_fields = ("id", "email", "is_email_verified", "profile", "stats")
        
    def get_profile(self, obj):
        from profiles.serializers import InvestorProfileSerializer, SponsorProfileSerializer
        
        if obj.role == RoleChoices.INVESTOR and hasattr(obj, 'investor_profile'):
            return InvestorProfileSerializer(obj.investor_profile).data
        elif obj.role == RoleChoices.SPONSOR and hasattr(obj, 'sponsor_profile'):
            return SponsorProfileSerializer(obj.sponsor_profile).data
        return None
        
    def get_stats(self, obj):
        if obj.role == RoleChoices.SPONSOR:
            projects_count = obj.projects.count()
            requests_count = sum(p.collaboration_requests.count() for p in obj.projects.all())
            # Dummy logic for funded
            funded = sum(p.raised_amount for p in obj.projects.all() if p.raised_amount)
            
            return {
                "projects": projects_count,
                "requests": requests_count,
                "funded": funded
            }
        elif obj.role == RoleChoices.INVESTOR:
            requests = obj.investor_profile.collaboration_requests.all() if hasattr(obj, 'investor_profile') else []
            
            total_committed = sum(r.proposed_budget for r in requests if r.status == 'CONFIRMED')
            active_projects = sum(1 for r in requests if r.status == 'CONFIRMED')
            pending_ndas = sum(1 for r in requests if not r.nda_signed)
            
            return {
                "saved_projects": obj.saved_projects.count(),
                "total_committed": total_committed,
                "active_projects": active_projects,
                "pending_ndas": pending_ndas
            }
        return {}


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)
    
    def validate_current_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is not correct.")
        return value
