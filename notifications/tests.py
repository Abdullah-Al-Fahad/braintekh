import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from users.models import RoleChoices
from profiles.models import SponsorProfile
from projects.models import Project, ProjectStatusChoices
from notifications.models import Conversation, Message
from decimal import Decimal

User = get_user_model()

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def sponsor_user():
    user = User.objects.create_user(email="sponsor2@example.com", password="password123", role=RoleChoices.SPONSOR, is_email_verified=True)
    SponsorProfile.objects.create(user=user)
    return user

@pytest.fixture
def test_user():
    return User.objects.create_user(email="investor2@example.com", password="password123", role=RoleChoices.INVESTOR, is_email_verified=True)

@pytest.fixture
def sample_project(sponsor_user):
    return Project.objects.create(
        sponsor=sponsor_user.sponsor_profile,
        title="AI Chat Test Project",
        short_description="Test",
        funding_goal=Decimal("10000.00"),
        minimum_investment=Decimal("1000.00"),
        target_roi=Decimal("10.00"),
        timeline_months=12,
        status=ProjectStatusChoices.ACTIVE
    )

@pytest.mark.django_db
class TestChat:
    def test_create_group_chat(self, api_client, test_user, sponsor_user, sample_project):
        api_client.force_authenticate(user=test_user)
        url = reverse('notifications:conversation-start')
        data = {
            "project_id": sample_project.id
        }
        response = api_client.post(url, data)
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]
        assert Conversation.objects.count() == 1
        
        conversation = Conversation.objects.first()
        assert conversation.is_group is True
        
        # Verify both the creator and the project sponsor are in the chat
        participant_ids = list(conversation.participants.values_list('id', flat=True))
        assert test_user.id in participant_ids
        assert sponsor_user.id in participant_ids

    def test_send_message_triggers_ai(self, api_client, test_user, sponsor_user, sample_project):
        # Create group chat
        conversation = Conversation.objects.create(project=sample_project, is_group=True)
        conversation.participants.add(test_user, sponsor_user)
        
        api_client.force_authenticate(user=test_user)
        url = reverse('notifications:conversation-message-send', kwargs={'pk': conversation.id})
        data = {
            "content": "What is the MAU?"
        }
        response = api_client.post(url, data)
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]
        
        # 1 user message + 1 AI generated message (because of '?')
        assert Message.objects.count() == 2
        ai_message = Message.objects.filter(is_ai_generated=True).first()
        assert ai_message is not None
        assert "VentureAI Tip" in ai_message.content
