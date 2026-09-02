"""
Custom throttle classes for authentication endpoints.

We enforce a stricter rate limit on sensitive auth routes (login, OTP, etc.)
to protect against brute-force and enumeration attacks.
"""

from rest_framework.throttling import AnonRateThrottle


class AuthRateThrottle(AnonRateThrottle):
    """
    Throttle applied to all authentication endpoints.
    Rate defined in settings.DEFAULT_THROTTLE_RATES['auth'].
    """
    scope = 'auth'
