import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from profiles.models import InvestorProfile, SponsorProfile, InvestorTypeChoices, SponsorTypeChoices, VerificationStatusChoices

User = get_user_model()

email = "dual@example.com"
password = "password123"

# 1. Create or get user
user, created = User.objects.get_or_create(email=email)
if created:
    user.set_password(password)
    user.first_name = "Dual"
    user.last_name = "Persona"
    user.role = "INVESTOR"
    user.is_email_verified = True
    user.save()
    print(f"Created user {email}")
else:
    print(f"User {email} already exists. Updating profiles...")

# 2. Create Investor Profile
investor, _ = InvestorProfile.objects.update_or_create(
    user=user,
    defaults={
        "investor_type": InvestorTypeChoices.INDIVIDUAL,
        "verification_status": VerificationStatusChoices.APPROVED,
        "location": "New York, NY",
        "bio": "I am an investor looking for startups.",
    }
)

# 3. Create Sponsor Profile
sponsor, _ = SponsorProfile.objects.update_or_create(
    user=user,
    defaults={
        "sponsor_type": SponsorTypeChoices.COMPANY,
        "verification_status": VerificationStatusChoices.APPROVED,
        "legal_company_name": "Dual Tech LLC",
        "bio": "I also raise money for my tech startup.",
    }
)

print(f"Done! Test account ready:\nEmail: {email}\nPassword: {password}")
