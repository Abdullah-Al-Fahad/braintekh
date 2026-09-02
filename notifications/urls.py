from django.urls import path
from .views import NotificationListView, MarkAllReadView, MarkReadView, SendMessageView

app_name = 'notifications'

urlpatterns = [
    path('', NotificationListView.as_view(), name='notification-list'),
    path('mark-all-read/', MarkAllReadView.as_view(), name='notification-mark-all-read'),
    path('<int:pk>/read/', MarkReadView.as_view(), name='notification-mark-read'),
    path('messages/', SendMessageView.as_view(), name='send-message'),
]
