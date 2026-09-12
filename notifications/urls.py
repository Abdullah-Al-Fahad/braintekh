from django.urls import path
from .views import (
    NotificationListView, MarkAllReadView, MarkReadView,
    ConversationListView, ConversationDetailView, MessageListView,
    ConversationCreateView, MessageCreateView
)

app_name = 'notifications'

urlpatterns = [
    # Notifications
    path('', NotificationListView.as_view(), name='notification-list'),
    path('mark-all-read/', MarkAllReadView.as_view(), name='notification-mark-all-read'),
    path('<int:pk>/read/', MarkReadView.as_view(), name='notification-mark-read'),
    
    # Chat / Conversations
    path('chat/conversations/', ConversationListView.as_view(), name='conversation-list'),
    path('chat/conversations/start/', ConversationCreateView.as_view(), name='conversation-start'),
    path('chat/conversations/<int:pk>/', ConversationDetailView.as_view(), name='conversation-detail'),
    path('chat/conversations/<int:pk>/messages/', MessageListView.as_view(), name='conversation-messages'),
    path('chat/conversations/<int:pk>/messages/send/', MessageCreateView.as_view(), name='conversation-message-send'),
]
