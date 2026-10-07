from django.urls import path
from .views import MeView, ChangePasswordView, DeleteAccountView, SwitchRoleView

app_name = 'users'

urlpatterns = [
    path('me/', MeView.as_view(), name='me'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('switch-role/', SwitchRoleView.as_view(), name='switch-role'),
    path('delete-account/', DeleteAccountView.as_view(), name='delete-account'),
]
