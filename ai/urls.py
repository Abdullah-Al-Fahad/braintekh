from django.urls import path
from .views import AIConversationView, AIConversationDetailView, AIMessageView

app_name = 'ai'

urlpatterns = [
    path('projects/conversations/', AIConversationView.as_view(), name='conversations'),
    path('projects/conversations/<str:pk>/', AIConversationDetailView.as_view(), name='conversation-detail'),
    path('projects/conversations/<str:pk>/messages/', AIMessageView.as_view(), name='messages'),
]
