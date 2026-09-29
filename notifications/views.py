import logging
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import JSONParser
from drf_spectacular.utils import extend_schema, OpenApiResponse

from core.responses import created_response, error_response, success_response
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from projects.models import Project
from .models import Notification, Message, Conversation, ConversationParticipant, NotificationType
from .serializers import NotificationSerializer, MessageSerializer, ConversationSerializer
from .services import ChatService

User = get_user_model()
logger = logging.getLogger(__name__)

@extend_schema(
    tags=["Notifications"],
    summary="List Notifications",
    description="Returns a list of all notifications for the authenticated user, ordered by most recent.",
    responses={200: NotificationSerializer(many=True)}
)
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

@extend_schema(
    tags=["Notifications"],
    summary="Mark All Notifications as Read",
    description="Marks all unread notifications for the user as read.",
    responses={200: OpenApiResponse(description="All notifications marked as read.")}
)
class MarkAllReadView(APIView):
    """
    POST /api/v1/notifications/mark-all-read/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
        return success_response(message="All notifications marked as read.")

@extend_schema(
    tags=["Notifications"],
    summary="Mark Single Notification as Read",
    description="Marks a specific notification as read by its ID.",
    responses={200: OpenApiResponse(description="Notification marked as read.")}
)
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

@extend_schema(
    tags=["Chat & Messages"],
    summary="List Conversations",
    description="Returns a list of all chat conversations the user is a participant in.",
    responses={200: ConversationSerializer(many=True)}
)
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

@extend_schema(
    tags=["Chat & Messages"],
    summary="Get Conversation Details",
    description="Returns details about a specific conversation.",
    responses={200: ConversationSerializer}
)
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

@extend_schema(
    tags=["Chat & Messages"],
    summary="List Messages in Conversation",
    description="Returns all messages in a specific conversation ordered by creation time.",
    responses={200: MessageSerializer(many=True)}
)
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

@extend_schema(
    tags=["Chat & Messages"],
    summary="Start Conversation",
    description="Starts a new conversation. Can be 1-on-1 (target_user_id) or a group chat (project_id).",
    request={"application/json": {"type": "object", "properties": {"target_user_id": {"type": "integer"}, "project_id": {"type": "integer"}}}},
    responses={201: ConversationSerializer}
)
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

@extend_schema(
    tags=["Chat & Messages"],
    summary="Send Message",
    description="Sends a new message in a conversation. May trigger VentureAI if it's a group chat.",
    request={"application/json": {"type": "object", "properties": {"content": {"type": "string"}}}},
    responses={201: MessageSerializer}
)
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
