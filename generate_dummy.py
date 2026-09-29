import os
import django
import random
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from users.models import User, RoleChoices
from profiles.models import SponsorProfile, InvestorProfile, Industry, VerificationStatusChoices, InvestorTypeChoices, SponsorTypeChoices
from projects.models import Project, Category, CollaborationRequest, CollaborationRequestStatus, ProjectStatusChoices

def generate():
    try:
        user = User.objects.get(id=28)
    except User.DoesNotExist:
        print("User 28 does not exist!")
        return

    print(f"Generating data for User {user.email} (Role: {user.role})")
    
    # Ensure some industries and categories exist
    ind1, _ = Industry.objects.get_or_create(name="Real Estate")
    ind2, _ = Industry.objects.get_or_create(name="Technology")
    cat1, _ = Category.objects.get_or_create(name="Commercial")
    cat2, _ = Category.objects.get_or_create(name="SaaS")

    # Determine what to generate based on role
    if user.role == RoleChoices.SPONSOR:
        sponsor, _ = SponsorProfile.objects.get_or_create(user=user)
        sponsor.sponsor_type = SponsorTypeChoices.COMPANY
        sponsor.legal_company_name = "Global Ventures LLC"
        sponsor.verification_status = VerificationStatusChoices.APPROVED
        sponsor.save()

        # Generate some dummy projects for this sponsor
        print("Creating dummy projects...")
        for i in range(1, 4):
            proj, created = Project.objects.get_or_create(
                sponsor=sponsor,
                title=f"Dummy Project {i} by {user.first_name}",
                defaults={
                    'location': "Austin, TX",
                    'short_description': "An amazing investment opportunity.",
                    'industry': ind1 if i % 2 == 0 else ind2,
                    'status': ProjectStatusChoices.ACTIVE,
                    'funding_goal': Decimal("1000000.00"),
                    'minimum_investment': Decimal("50000.00"),
                    'target_roi': Decimal("15.5"),
                    'timeline_months': 24
                }
            )
            if created:
                proj.categories.add(cat1)
            print(f"  - Created project: {proj.title}")

        # Add dummy collaboration requests from fake investors
        print("Creating dummy collaboration requests...")
        projects = Project.objects.filter(sponsor=sponsor)
        for i in range(1, 4):
            fake_user, _ = User.objects.get_or_create(
                email=f"fake_investor_{i}@example.com",
                defaults={'first_name': f"Investor {i}", 'last_name': "Fake", 'role': RoleChoices.INVESTOR, 'is_email_verified': True}
            )
            inv_profile, _ = InvestorProfile.objects.get_or_create(user=fake_user)
            inv_profile.investor_type = InvestorTypeChoices.INDIVIDUAL
            inv_profile.save()

            proj = random.choice(projects)
            req, created = CollaborationRequest.objects.get_or_create(
                project=proj,
                investor=inv_profile,
                defaults={
                    'proposed_budget': Decimal("75000.00"),
                    'proposal_text': f"I am very interested in funding {proj.title}.",
                    'status': CollaborationRequestStatus.PENDING,
                }
            )
            if created:
                print(f"  - Created request from {fake_user.email} on {proj.title}")

    elif user.role == RoleChoices.INVESTOR:
        investor, _ = InvestorProfile.objects.get_or_create(user=user)
        investor.investor_type = InvestorTypeChoices.INDIVIDUAL
        investor.verification_status = VerificationStatusChoices.APPROVED
        investor.save()
        
        # Create a fake sponsor and project
        fake_sponsor_user, _ = User.objects.get_or_create(
            email="fake_sponsor@example.com",
            defaults={'first_name': "Sponsor", 'last_name': "Fake", 'role': RoleChoices.SPONSOR, 'is_email_verified': True}
        )
        fake_sponsor_profile, _ = SponsorProfile.objects.get_or_create(user=fake_sponsor_user)
        
        print("Creating dummy projects for investor to request on...")
        for i in range(1, 4):
            proj, _ = Project.objects.get_or_create(
                sponsor=fake_sponsor_profile,
                title=f"Opportunity {i}",
                defaults={
                    'location': "New York, NY",
                    'short_description': "A great startup.",
                    'industry': ind2,
                    'status': ProjectStatusChoices.ACTIVE,
                    'funding_goal': Decimal("500000.00"),
                    'minimum_investment': Decimal("10000.00"),
                    'target_roi': Decimal("12.0"),
                    'timeline_months': 36
                }
            )
            req, created = CollaborationRequest.objects.get_or_create(
                project=proj,
                investor=investor,
                defaults={
                    'proposed_budget': Decimal("20000.00"),
                    'proposal_text': f"I want to invest in {proj.title}.",
                    'status': random.choice([CollaborationRequestStatus.PENDING, CollaborationRequestStatus.APPROVED])
                }
            )
            if created:
                print(f"  - Created request on {proj.title} (Status: {req.status})")
    
    print("Done!")

generate()
