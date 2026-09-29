import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from dj_rest_auth.app_settings import api_settings
print("JWT_AUTH_HTTPONLY is:", api_settings.JWT_AUTH_HTTPONLY)
