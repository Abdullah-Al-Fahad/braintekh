import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from users.models import RoleChoices

User = get_user_model()

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def test_user():
    return User.objects.create_user(
        email="test@example.com",
        password="password123",
        first_name="Test",
        last_name="User",
        role=RoleChoices.NONE
    )

@pytest.mark.django_db
class TestAuthentication:
    def test_user_registration(self, api_client):
        url = reverse('authentication:register')
        data = {
            "email": "newuser@example.com",
            "password": "strongpassword123",
            "first_name": "New",
            "last_name": "User",
            "role": "INVESTOR"
        }
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['status'] == 'success'
        assert "check your email" in response.data['message']
        assert User.objects.filter(email="newuser@example.com").exists()

    def test_user_login(self, api_client, test_user):
        url = reverse('authentication:login')
        data = {
            "email": "test@example.com",
            "password": "password123"
        }
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data

@pytest.mark.django_db
class TestUserSettings:
    def test_get_me_view(self, api_client, test_user):
        api_client.force_authenticate(user=test_user)
        url = reverse('users:me')
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['data']['email'] == "test@example.com"
        assert response.data['data']['push_notifications_enabled'] is True

    def test_update_settings(self, api_client, test_user):
        api_client.force_authenticate(user=test_user)
        url = reverse('users:me')
        data = {
            "push_notifications_enabled": False,
            "subscription_tier": "PRO"
        }
        response = api_client.patch(url, data)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['data']['push_notifications_enabled'] is False
        assert response.data['data']['subscription_tier'] == "PRO"
        
        test_user.refresh_from_db()
        assert test_user.subscription_tier == "PRO"
