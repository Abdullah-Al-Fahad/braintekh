"""
Custom DRF permissions.

Centralised permission classes make it easy to add, test, and reuse
access-control logic without scattering it across views.
"""

from rest_framework.permissions import BasePermission
from users.models import RoleChoices


class IsEmailVerified(BasePermission):
    """Allow access only to users who have verified their email address."""

    message = "Please verify your email address before proceeding."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_email_verified
        )


class IsInvestor(BasePermission):
    """Allow access only to users with the INVESTOR role."""

    message = "This endpoint is available to investors only."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == RoleChoices.INVESTOR
        )


class IsSponsor(BasePermission):
    """Allow access only to users with the SPONSOR role."""

    message = "This endpoint is available to sponsors only."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == RoleChoices.SPONSOR
        )
