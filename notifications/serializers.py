from rest_framework import serializers
from .models import Notification, Message, Conversation, ConversationParticipant

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'title', 'message', 'notification_type', 'is_read', 'related_object_id', 'created_at']
        read_only_fields = ['id', 'created_at']

class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.full_name', read_only=True)
    sender_email = serializers.CharField(source='sender.email', read_only=True)
    
    class Meta:
        model = Message
        fields = ['id', 'conversation', 'sender_name', 'sender_email', 'content', 'is_ai_generated', 'created_at']
        read_only_fields = ['id', 'conversation', 'sender_name', 'sender_email', 'is_ai_generated', 'created_at']

class ConversationSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = ['id', 'project', 'is_group', 'name', 'last_message', 'updated_at']
        
    def get_name(self, obj):
        if obj.is_group and obj.project:
            return f"{obj.project.title} || Group Chat"
            
        # For 1-to-1, return the other person's name
        request = self.context.get('request')
        if request and request.user:
            other_participant = obj.participants.exclude(id=request.user.id).first()
            if other_participant:
                return other_participant.full_name or other_participant.email
        return "Conversation"
        
    def get_last_message(self, obj):
        last_msg = obj.messages.last()
        if last_msg:
            return MessageSerializer(last_msg).data
        return None
