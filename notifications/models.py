from django.db import models
from django.utils.translation import gettext_lazy as _
from core.models import TimeStampedModel
from django.contrib.auth import get_user_model

User = get_user_model()

class NotificationType(models.TextChoices):
    COLLAB_REQUEST = 'COLLAB_REQUEST', _('Collaboration Request')
    MESSAGE = 'MESSAGE', _('New Message')
    NDA_APPROVED = 'NDA_APPROVED', _('NDA Approved')
    PROFILE_VERIFIED = 'PROFILE_VERIFIED', _('Profile Verified')
    SYSTEM = 'SYSTEM', _('System Notification')

class Notification(TimeStampedModel):
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(max_length=50, choices=NotificationType.choices, default=NotificationType.SYSTEM)
    is_read = models.BooleanField(default=False)
    
    # Optional link to related object (e.g. Project ID or Message ID)
    related_object_id = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.recipient.email}"

class Message(TimeStampedModel):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    content = models.TextField()

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Message from {self.sender.email} to {self.recipient.email}"
