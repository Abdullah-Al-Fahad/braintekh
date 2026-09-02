from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from core.responses import success_response, created_response, error_response
from .models import Notification, Message, NotificationType
from .serializers import NotificationSerializer, MessageSerializer

class NotificationListView(generics.ListAPIView):
    """
    GET /api/v1/notifications/
    List all notifications for the authenticated user.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationSerializer

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)


class MarkAllReadView(APIView):
    """
    PATCH /api/v1/notifications/mark-all-read/
    Marks all notifications for the user as read.
    """
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
        return success_response(message="All notifications marked as read.")


class MarkReadView(APIView):
    """
    PATCH /api/v1/notifications/<id>/read/
    Marks a single notification as read.
    """
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        try:
            notification = Notification.objects.get(pk=pk, recipient=request.user)
            notification.is_read = True
            notification.save(update_fields=['is_read'])
            return success_response(message="Notification marked as read.")
        except Notification.DoesNotExist:
            return error_response("Notification not found.", status_code=status.HTTP_404_NOT_FOUND)


class SendMessageView(generics.CreateAPIView):
    """
    POST /api/v1/messages/
    Send a message to another user. Automatically creates a notification for them.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = MessageSerializer

    def perform_create(self, serializer):
        message = serializer.save(sender=self.request.user)
        
        # Create a notification for the recipient
        Notification.objects.create(
            recipient=message.recipient,
            title="New Message",
            message=f"{self.request.user.full_name or self.request.user.email} sent you a message.",
            notification_type=NotificationType.MESSAGE,
            related_object_id=str(message.id)
        )
