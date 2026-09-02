from rest_framework import serializers
from .models import Notification, Message

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'title', 'message', 'notification_type', 'is_read', 'related_object_id', 'created_at']
        read_only_fields = ['id', 'created_at']

class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.full_name', read_only=True)
    
    class Meta:
        model = Message
        fields = ['id', 'sender_name', 'recipient', 'content', 'created_at']
        read_only_fields = ['id', 'sender_name', 'created_at']
