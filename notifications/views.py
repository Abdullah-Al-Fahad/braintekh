import logging
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import JSONParser
from core.responses import success_response, error_response, created_response
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from projects.models import Project
from .models import Notification, Message, Conversation, ConversationParticipant, NotificationType
from .serializers import NotificationSerializer, MessageSerializer, ConversationSerializer
from .services import ChatService

User = get_user_model()
logger = logging.getLogger(__name__)

class NotificationListView(APIView):
    """
    GET /api/v1/notifications/
    Fetch all notifications for the current user.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        notifications = Notification.objects.filter(recipient=request.user)
        # Note: Pagination should be applied here globally or manually
        serializer = NotificationSerializer(notifications, many=True)
        return success_response(data=serializer.data)

class MarkAllReadView(APIView):
    """
    POST /api/v1/notifications/mark-all-read/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
        return success_response(message="All notifications marked as read.")

class MarkReadView(APIView):
    """
    POST /api/v1/notifications/<id>/read/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
        notification.is_read = True
        notification.save(update_fields=['is_read'])
        return success_response(message="Notification marked as read.")

class ConversationListView(APIView):
    """
    GET /api/v1/chat/conversations/
    List all conversations the user is a part of.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        conversations = Conversation.objects.filter(participants=request.user).prefetch_related('participants')
        serializer = ConversationSerializer(conversations, many=True, context={'request': request})
        return success_response(data=serializer.data)

class ConversationDetailView(APIView):
    """
    GET /api/v1/chat/conversations/<id>/
    Fetch a specific conversation (includes messages via a separate endpoint typically, but we can just return conversation details).
    """
    permission_classes = [IsAuthenticated]
    serializer_class = ConversationSerializer

    def get_queryset(self):
        return Conversation.objects.filter(participants=self.request.user)
        
    def get(self, request, pk):
        conversation = get_object_or_404(self.get_queryset(), pk=pk)
        return success_response(data=self.serializer_class(conversation, context={'request': request}).data)

class MessageListView(APIView):
    """
    GET /api/v1/chat/conversations/<id>/messages/
    Fetch messages for a conversation.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, conversation_id):
        get_object_or_404(Conversation, id=conversation_id, participants=self.request.user)
        messages = Message.objects.filter(conversation_id=conversation_id)
        serializer = MessageSerializer(messages, many=True)
        return success_response(data=serializer.data)

class ConversationCreateView(APIView):
    """
    POST /api/v1/chat/conversations/
    Start a new conversation (1-on-1 or group).
    Payload: { "target_user_id": 123 } OR { "project_id": 456 }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        target_user_id = request.data.get('target_user_id')
        project_id = request.data.get('project_id')
        
        target_user = get_object_or_404(User, id=target_user_id) if target_user_id else None
        project = get_object_or_404(Project, id=project_id) if project_id else None
        
        try:
            conversation = ChatService.start_conversation(
                creator=request.user,
                is_group=bool(project),
                project=project,
                target_user=target_user
            )
            return success_response(data=ConversationSerializer(conversation, context={'request': request}).data)
        except ValueError as e:
            return error_response(str(e))

class MessageCreateView(APIView):
    """
    POST /api/v1/chat/conversations/<id>/messages/
    Send a message to a conversation.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        conversation = get_object_or_404(Conversation, id=pk, participants=request.user)
        content = request.data.get('content')
        
        if not content:
            return error_response("Content is required.")
            
        message = ChatService.send_message(
            sender=request.user,
            conversation=conversation,
            content=content
        )
        
        return success_response(data=MessageSerializer(message).data)
