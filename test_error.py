import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from rest_framework.test import APIRequestFactory, force_authenticate
from profiles.views import SponsorOnboardingView
from users.models import User, RoleChoices
from profiles.models import SponsorProfile

user = User.objects.get(email="admin@damani.ai")
user.role = RoleChoices.SPONSOR
user.is_email_verified = True
user.save()
SponsorProfile.objects.get_or_create(user=user)

factory = APIRequestFactory()
request = factory.patch('/api/v1/profiles/sponsor/onboarding/', {"sponsor_type": "INDIVIDUAL"}, format='json')
force_authenticate(request, user=user)

view = SponsorOnboardingView.as_view()
try:
    response = view(request)
    print("STATUS:", response.status_code)
    try:
        print("DATA:", response.data)
    except:
        pass
except Exception as e:
    import traceback
    traceback.print_exc()
