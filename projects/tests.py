import pytest
from decimal import Decimal
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from users.models import RoleChoices
from profiles.models import InvestorProfile, SponsorProfile
from projects.models import Project, ProjectStatusChoices, CollaborationRequest

User = get_user_model()

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def sponsor_user():
    user = User.objects.create_user(email="sponsor@example.com", password="password123", role=RoleChoices.SPONSOR, is_email_verified=True)
    SponsorProfile.objects.create(user=user, legal_company_name="Acme Corp")
    return user

@pytest.fixture
def investor_user():
    user = User.objects.create_user(email="investor@example.com", password="password123", role=RoleChoices.INVESTOR, is_email_verified=True)
    InvestorProfile.objects.create(user=user)
    return user

@pytest.fixture
def sample_project(sponsor_user):
    return Project.objects.create(
        sponsor=sponsor_user.sponsor_profile,
        title="Test Project",
        short_description="Test",
        funding_goal=Decimal("1000000.00"),
        minimum_investment=Decimal("50000.00"),
        target_roi=Decimal("15.00"),
        timeline_months=24,
        status=ProjectStatusChoices.ACTIVE
    )

@pytest.mark.django_db
class TestProjects:
    def test_public_project_list(self, api_client, sample_project):
        url = reverse('projects:public-project-list')
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['data']) == 1
        assert response.data['data'][0]['title'] == "Test Project"

    def test_investor_collaboration_request(self, api_client, investor_user, sample_project):
        api_client.force_authenticate(user=investor_user)
        url = reverse('projects:investor-request-create', kwargs={'project_id': sample_project.id})
        data = {
            "proposed_budget": "100000.00",
            "proposal_text": "I am very interested."
        }
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED
        assert CollaborationRequest.objects.count() == 1
        assert CollaborationRequest.objects.first().proposed_budget == Decimal("100000.00")

    def test_sponsor_bulk_confirm(self, api_client, sponsor_user, investor_user, sample_project):
        # Create an APPROVED request first
        req = CollaborationRequest.objects.create(
            project=sample_project,
            investor=investor_user.investor_profile,
            proposed_budget=Decimal("50000.00"),
            status='APPROVED'
        )
        
        api_client.force_authenticate(user=sponsor_user)
        url = reverse('projects:sponsor-bulk-confirm', kwargs={'pk': sample_project.id})
        data = {
            "request_ids": [req.id]
        }
        response = api_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_200_OK
        
        req.refresh_from_db()
        assert req.status == 'CONFIRMED'
