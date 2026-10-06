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
        if not hasattr(request.user, 'sponsor_profile') or conversation.project.created_by_id != request.user.id:
            return error_response(
                message="Only the project sponsor who created this project can perform this action.",
                status=403,
                errors={"code": "PERMISSION_DENIED"}
            )
            
        participant_to_remove = get_object_or_404(User, id=user_id)
        if participant_to_remove == request.user:
            return error_response(
                message="Project creator cannot be removed from their own project group chat.",
                status=400,
                errors={"code": "INVALID_TARGET"}
            )
            
        cp = get_object_or_404(ConversationParticipant, conversation=conversation, user=participant_to_remove)
        cp.is_active = False
        cp.save(update_fields=['is_active'])
        
        # System message
        system_msg = Message.objects.create(
            conversation=conversation,
            sender=None,
            message_type=MessageType.SYSTEM,
            content=f"{participant_to_remove.first_name} {participant_to_remove.last_name} was removed from the group by the owner."
        )
        
        # Broadcast
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"chat_{conversation.id}",
            {
                "type": "chat_message",
                "event_type": "participant_removed",
                "conversation_id": conversation.id,
                "removed_user_id": participant_to_remove.id,
                "system_message_id": system_msg.id
            }
        )
        
        return success_response(
            message="Participant removed from group chat.",
            data={
                "conversation_id": conversation.id,
                "removed_user_id": participant_to_remove.id,
                "remaining_member_count": conversation.participants.filter(conversationparticipant__is_active=True).count(),
                "system_message_id": system_msg.id
            }
        )

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

@extend_schema(
    tags=["Chat & Messages"],
    summary="Group Chat Header",
    description="Returns metadata for the top bar: project title, active member count, caller ownership flag, and list of participants.",
    responses={200: OpenApiResponse(description="Header metadata fetched")}
)
class ConversationHeaderView(APIView):
    """
    GET /api/v1/notifications/chat/conversations/{conversation_id}/header/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        conversation = get_object_or_404(Conversation, id=pk)
        
        # Must be an active participant
        if not conversation.conversationparticipant_set.filter(user=request.user, is_active=True).exists():
            return error_response("You must be an active participant.", status=403)
            
        project = conversation.project
        is_owner = project and project.created_by_id == request.user.id
        
        active_participants = conversation.conversationparticipant_set.filter(is_active=True).select_related('user')
        
        participants_data = []
        for cp in active_participants:
            u = cp.user
            p_is_owner = project and project.created_by_id == u.id
            avatar_url = None
            if hasattr(u, 'sponsor_profile') and u.sponsor_profile.profile_photo:
                avatar_url = request.build_absolute_uri(u.sponsor_profile.profile_photo.url)
            elif hasattr(u, 'investor_profile') and u.investor_profile.profile_photo:
                avatar_url = request.build_absolute_uri(u.investor_profile.profile_photo.url)
                
            participants_data.append({
                "user_id": u.id,
                "name": f"{u.first_name} {u.last_name}".strip(),
                "role": u.role,
                "is_owner": p_is_owner,
                "avatar_url": avatar_url,
                "initials": f"{u.first_name[0] if u.first_name else ''}{u.last_name[0] if u.last_name else ''}".upper()
            })
            
        return success_response(data={
            "conversation_id": conversation.id,
            "project_id": project.id if project else None,
            "project_title": project.title if project else "Direct Message",
            "is_owner": is_owner,
            "active_member_count": active_participants.count(),
            "participants": participants_data
        })

@extend_schema(
    tags=["Chat & Messages"],
    summary="Leave Group Chat",
    description="Allows an investor to leave a group chat.",
    responses={200: OpenApiResponse(description="Left the group chat")}
)
class ConversationLeaveView(APIView):
    """
    POST /api/v1/notifications/chat/conversations/{conversation_id}/leave/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        conversation = get_object_or_404(Conversation, id=pk)
        
        if conversation.project and conversation.project.created_by_id == request.user.id:
            return error_response(
                message="Project owners cannot leave their project group chat.",
                status=400,
                errors={"code": "OWNER_CANNOT_LEAVE"}
            )
            
        cp = get_object_or_404(ConversationParticipant, conversation=conversation, user=request.user)
        if not cp.is_active:
            return error_response("You are not an active participant of this chat.")
            
        cp.is_active = False
        cp.save(update_fields=['is_active'])
        
        system_msg = Message.objects.create(
            conversation=conversation,
            sender=None,
            message_type=MessageType.SYSTEM,
            content=f"{request.user.first_name} {request.user.last_name} left the group."
        )
        
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"chat_{conversation.id}",
            {
                "type": "chat_message",
                "event_type": "participant_left",
                "conversation_id": conversation.id,
                "left_user_id": request.user.id,
                "system_message_id": system_msg.id
            }
        )
        
        return success_response(
            message="You have left the group chat.",
            data={
                "conversation_id": conversation.id,
                "is_active": False
            }
        )

@extend_schema(
    tags=["Chat & Messages"],
    summary="Report Group Chat",
    description="Report a group chat for spam or misconduct.",
    responses={201: OpenApiResponse(description="Report submitted")}
)
class ConversationReportView(APIView):
    """
    POST /api/v1/notifications/chat/conversations/{conversation_id}/report/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        conversation = get_object_or_404(Conversation, id=pk)
        if not conversation.conversationparticipant_set.filter(user=request.user, is_active=True).exists():
            return error_response("You must be an active participant.", status=403)
            
        # In a real app, save report to DB.
        import random
        report_id = f"REP-{random.randint(10000, 99999)}"
        return created_response(
            message="Report submitted successfully. Our compliance team will review this chat.",
            data={"report_id": report_id}
        )

@extend_schema(
    tags=["Chat & Messages"],
    summary="Confirm Investors",
    description="Sponsor action to confirm funds and add investors to the project.",
    responses={200: OpenApiResponse(description="Investors confirmed")}
)
class ConversationConfirmInvestorsView(APIView):
    """
    POST /api/v1/projects/{project_id}/confirm-investors/
    (Aliased via chat for convenience)
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        conversation = get_object_or_404(Conversation, id=pk)
        project = conversation.project
        
        if not project:
            return error_response("This conversation is not linked to a project.")
            
        if project.created_by_id != request.user.id:
            return error_response(
                message="Only the project sponsor who created this project can confirm investors.",
                status=403,
                errors={"code": "PERMISSION_DENIED"}
            )
            
        investors_data = request.data.get('investors', [])
        if not investors_data:
            return error_response("Investors array is required.")
            
        total_added = 0
        names = []
        for inv in investors_data:
            amount = inv.get('confirmed_amount', 0)
            name = inv.get('name', 'Unknown Investor')
            # Mocking the actual DB update since InvestmentRecord/ProjectContribution 
            # model isn't fully defined yet in our quick phase. We just bump the total.
            project.raised_amount += amount
            total_added += amount
            names.append(f"{name} (${amount:,.2f})")
            
        project.save(update_fields=['raised_amount'])
        
        names_str = " and ".join(names)
        msg_text = f"🎉 Confirmed investors: {names_str} have officially joined the project!"
        
        system_msg = Message.objects.create(
            conversation=conversation,
            sender=None,
            message_type=MessageType.SYSTEM,
            content=msg_text
        )
        
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"chat_{conversation.id}",
            {
                "type": "chat_message",
                "event_type": "investor_confirmed",
                "conversation_id": conversation.id,
                "project_id": project.id,
                "confirmed_investors": investors_data,
                "system_message_id": system_msg.id
            }
        )
        
        return success_response(
            message=f"{len(investors_data)} investors confirmed successfully.",
            data={
                "project_id": project.id,
                "total_raised": f"${project.raised_amount:,.2f}",
                "confirmed_investors_count": len(investors_data),
                "system_message": {
                    "id": system_msg.id,
                    "conversation_id": conversation.id,
                    "sender_id": None,
                    "sender_role": "System",
                    "message_type": MessageType.SYSTEM,
                    "text": msg_text,
                    "created_at": system_msg.created_at.isoformat()
                }
            }
        )
