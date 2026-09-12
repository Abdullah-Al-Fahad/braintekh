from django.urls import path
from .views import MeView, ChangePasswordView, DeleteAccountView

app_name = 'users'

urlpatterns = [
    path('me/', MeView.as_view(), name='me'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
]
