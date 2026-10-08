from django.urls import path
from .views import (
    AIConversationView, 
    AIConversationDetailView, 
    AIMessageView,
    CopilotInitialView,
    CopilotMessageView,
    CopilotClearView
)

app_name = 'ai'

urlpatterns = [
    path('projects/conversations/', AIConversationView.as_view(), name='conversations'),
    path('projects/conversations/<str:pk>/', AIConversationDetailView.as_view(), name='conversation-detail'),
    path('projects/conversations/<str:pk>/messages/', AIMessageView.as_view(), name='messages'),
    
    # Copilot Chat Endpoints
    path('chat/initial/', CopilotInitialView.as_view(), name='chat-initial'),
    path('chat/conversations/<str:conversation_id>/messages/', CopilotMessageView.as_view(), name='chat-messages'),
    path('chat/conversations/<str:conversation_id>/clear/', CopilotClearView.as_view(), name='chat-clear'),
]
