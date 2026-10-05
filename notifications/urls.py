from django.urls import path
from .views import (
    NotificationListView, MarkAllReadView, MarkReadView,
    NotificationDeleteView, NotificationClearAllView,
    ConversationListView, ConversationDetailView, MessageListView,
    ConversationCreateView, MessageCreateView,
    ChatUploadView, ConversationMarkReadView, ConversationRemoveParticipantView,
    FCMDeviceCreateView, TestPushNotificationView
)

app_name = 'notifications'

urlpatterns = [
    # Notifications
    path('', NotificationListView.as_view(), name='notification-list'),
    path('mark-all-read/', MarkAllReadView.as_view(), name='notification-mark-all-read'),
    path('clear-all/', NotificationClearAllView.as_view(), name='notification-clear-all'),
    path('<int:pk>/', NotificationDeleteView.as_view(), name='notification-delete'),
    path('<int:pk>/read/', MarkReadView.as_view(), name='notification-mark-read'),
    path('device-token/', FCMDeviceCreateView.as_view(), name='fcm-device-token'),
    path('test-push/', TestPushNotificationView.as_view(), name='fcm-test-push'),
    
    # Chat / Conversations
    path('chat/conversations/', ConversationListView.as_view(), name='conversation-list'),
    path('chat/conversations/start/', ConversationCreateView.as_view(), name='conversation-start'),
    path('chat/conversations/<int:pk>/', ConversationDetailView.as_view(), name='conversation-detail'),
    path('chat/conversations/<int:pk>/messages/', MessageListView.as_view(), name='conversation-messages'),
    path('chat/conversations/<int:pk>/messages/send/', MessageCreateView.as_view(), name='conversation-message-send'),
    
    path('chat/upload/', ChatUploadView.as_view(), name='chat-upload'),
    path('chat/conversations/<int:pk>/read/', ConversationMarkReadView.as_view(), name='conversation-mark-read'),
    path('chat/conversations/<int:conversation_id>/participants/<int:user_id>/', ConversationRemoveParticipantView.as_view(), name='conversation-remove-participant'),
]
