"""
OTP email service.

Encapsulates all OTP lifecycle logic:
  - Invalidate any prior active OTPs of the same purpose.
  - Create a new OTP record.
  - Send the appropriate email.

This is a service-layer function, not a utility — it has a single
responsibility and is the only place in the codebase that manages OTPs.
"""

import logging

from django.core.mail import send_mail
from django.conf import settings

from .models import OTPRecord, OTPPurpose

logger = logging.getLogger(__name__)

# Email templates keyed by purpose — extending this in the future only requires
# adding a new entry here, not modifying any control flow.
_EMAIL_TEMPLATES: dict[str, dict[str, str]] = {
    OTPPurpose.REGISTRATION: {
        "subject": "Verify your email — Damani AI",
        "body_template": (
            "Hello {name},\n\n"
            "Your email verification code is:\n\n"
            "    {code}\n\n"
            "This code expires in {expiry} minutes.\n\n"
            "If you did not create an account, please ignore this email.\n\n"
            "— The Damani AI Team"
        ),
    },
    OTPPurpose.PASSWORD_RESET: {
        "subject": "Reset your password — Damani AI",
        "body_template": (
            "Hello {name},\n\n"
            "Your password reset code is:\n\n"
            "    {code}\n\n"
            "This code expires in {expiry} minutes.\n\n"
            "If you did not request a password reset, please ignore this email.\n\n"
            "— The Damani AI Team"
        ),
    },
}


def send_otp_email(user, purpose: str = OTPPurpose.REGISTRATION) -> OTPRecord:
    """
    Invalidate existing OTPs, create a new one, and send it to the user.

    Args:
        user: The User instance to send the OTP to.
        purpose: One of OTPPurpose.REGISTRATION or OTPPurpose.PASSWORD_RESET.

    Returns:
        The newly created OTPRecord instance.
    """
    # Step 1: Invalidate all active OTPs of the same purpose for this user
    OTPRecord.objects.filter(user=user, purpose=purpose, is_used=False).update(is_used=True)

    # Step 2: Create a fresh OTP
    otp = OTPRecord.objects.create(user=user, purpose=purpose)

    # Step 3: Build and send the email
    template = _EMAIL_TEMPLATES[purpose]
    body = template["body_template"].format(
        name=user.first_name or user.email,
        code=otp.code,
        expiry=settings.OTP_EXPIRY_MINUTES,
    )

    send_mail(
        subject=template["subject"],
        message=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )

    logger.info("OTP sent to %s for purpose=%s", user.email, purpose)
    return otp
