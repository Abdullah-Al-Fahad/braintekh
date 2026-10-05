import logging
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import JSONParser
from drf_spectacular.utils import extend_schema, OpenApiResponse

from core.responses import created_response, error_response, success_response
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.core.files.storage import default_storage
from projects.models import Project
from .models import Notification, Message, Conversation, ConversationParticipant, NotificationType, FCMDevice
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
    tags=["Notifications"],
    summary="Delete Single Notification",
    description="Deletes a specific notification by its ID.",
    responses={200: OpenApiResponse(description="Notification deleted.")}
)
class NotificationDeleteView(APIView):
    """
    DELETE /api/v1/notifications/<pk>/
    """
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
        notification.delete()
        return success_response(message="Notification deleted successfully.")

@extend_schema(
    tags=["Notifications"],
    summary="Clear All Notifications",
    description="Deletes all notifications for the authenticated user.",
    responses={200: OpenApiResponse(description="All notifications deleted.")}
)
class NotificationClearAllView(APIView):
    """
    DELETE /api/v1/notifications/clear-all/
    """
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        deleted_count, _ = Notification.objects.filter(recipient=request.user).delete()
        return success_response(message=f"Successfully deleted {deleted_count} notifications.")

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

    def get(self, request, pk):
        get_object_or_404(Conversation, id=pk, participants=self.request.user)
        messages = Message.objects.filter(conversation_id=pk)
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

@extend_schema(
    tags=["Chat & Messages"],
    summary="Upload Chat Media",
    description="Uploads an image or voice note to receive a public URL before sending a WebSocket message.",
    request={"multipart/form-data": {"type": "object", "properties": {"file": {"type": "string", "format": "binary"}, "type": {"type": "string"}, "voice_duration": {"type": "string"}}}},
    responses={201: OpenApiResponse(description="Media uploaded successfully")}
)
class ChatUploadView(APIView):
    """
    POST /api/v1/notifications/chat/upload/
    """
    permission_classes = [IsAuthenticated]
    from rest_framework.parsers import MultiPartParser, FormParser
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        uploaded_file = request.FILES.get('file')
        media_type = request.data.get('type')
        voice_duration = request.data.get('voice_duration')
        
        if not uploaded_file:
            return error_response("No file uploaded.")
            
        # Save file (In production, this would go to S3)
        file_path = default_storage.save(f"chat/{media_type}s/{uploaded_file.name}", uploaded_file)
        media_url = request.build_absolute_uri(default_storage.url(file_path))
        
        return created_response(
            message="Media uploaded successfully",
            data={
                "media_url": media_url,
                "type": media_type,
                "voice_duration": voice_duration
            }
        )

@extend_schema(
    tags=["Chat & Messages"],
    summary="Mark Conversation as Read",
    description="Resets the authenticated user's unread count for this conversation via REST.",
    responses={200: OpenApiResponse(description="Conversation marked as read")}
)
class ConversationMarkReadView(APIView):
    """
    POST /api/v1/notifications/chat/conversations/{id}/read/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        from django.utils import timezone
        conversation = get_object_or_404(Conversation, id=pk, participants=request.user)
        participant = conversation.conversationparticipant_set.get(user=request.user)
        participant.last_read_at = timezone.now()
        participant.save(update_fields=['last_read_at'])
        return success_response(message="Conversation marked as read")

@extend_schema(
    tags=["Chat & Messages"],
    summary="Remove Participant",
    description="Allows project sponsors to remove a member from a group chat.",
    responses={200: OpenApiResponse(description="Participant removed successfully")}
)
class ConversationRemoveParticipantView(APIView):
    """
    DELETE /api/v1/notifications/chat/conversations/{conversation_id}/participants/{user_id}/
    """
    permission_classes = [IsAuthenticated]

    def delete(self, request, conversation_id, user_id):
        conversation = get_object_or_404(Conversation, id=conversation_id, participants=request.user)
        
        # Only Sponsor can remove participants
        if not hasattr(request.user, 'sponsor_profile') or conversation.project.sponsor != request.user.sponsor_profile:
            return error_response("Only the Sponsor can remove participants.", status_code=403)
            
        participant_to_remove = get_object_or_404(User, id=user_id)
        if participant_to_remove == request.user:
            return error_response("Cannot remove yourself.")
            
        conversation.participants.remove(participant_to_remove)
        
        # System message and broadcast handled by ChatService ideally, but for now we just remove
        return success_response(message="Participant removed successfully")

@extend_schema(
    tags=["Notifications"],
    summary="Register FCM Device Token",
    description="Register a Firebase Cloud Messaging device token to receive push notifications.",
    request={"application/json": {"type": "object", "properties": {"token": {"type": "string"}, "device_name": {"type": "string"}}}},
    responses={200: OpenApiResponse(description="Token registered successfully")}
)
class FCMDeviceCreateView(APIView):
    """
    POST /api/v1/notifications/device-token/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        token = request.data.get('token')
        device_name = request.data.get('device_name', '')
        
        if not token:
            return error_response("Firebase token is required.")
            
        # Create or update token for user
        device, created = FCMDevice.objects.update_or_create(
            token=token,
            defaults={
                'user': request.user,
                'device_name': device_name,
                'is_active': True
            }
        )
        
        return success_response(message="Device token registered successfully.")

@extend_schema(
    tags=["Notifications"],
    summary="Send Test Push Notification",
    description="Sends a test Firebase push notification to the authenticated user's registered devices. Useful for frontend testing.",
    request={"application/json": {"type": "object", "properties": {"title": {"type": "string"}, "body": {"type": "string"}}}},
    responses={200: OpenApiResponse(description="Test notification sent")}
)
class TestPushNotificationView(APIView):
    """
    POST /api/v1/notifications/test-push/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        import firebase_admin
        from firebase_admin import messaging
        
        title = request.data.get('title', 'Test Notification')
        body = request.data.get('body', 'This is a test push notification from Braintekh!')
        
        devices = FCMDevice.objects.filter(user=request.user, is_active=True)
        if not devices.exists():
            return error_response("You don't have any registered Firebase devices. Call /device-token/ first.")
            
        success_count = 0
        errors = []
        
        for device in devices:
            try:
                message = messaging.Message(
                    notification=messaging.Notification(
                        title=title,
                        body=body,
                    ),
                    token=device.token,
                )
                response = messaging.send(message)
                success_count += 1
            except Exception as e:
                errors.append(str(e))
                # Optional: if token is unregistered, deactivate it.
                if 'not-found' in str(e) or 'unregistered' in str(e).lower():
                    device.is_active = False
                    device.save()
                    
        if success_count == 0 and errors:
            return error_response(f"Failed to send notifications. Errors: {errors}")
            
        return success_response(message=f"Successfully sent {success_count} test notification(s)!")
