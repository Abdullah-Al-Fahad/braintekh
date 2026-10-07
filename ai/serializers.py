from rest_framework import serializers
from .models import AIConversation, AIMessage

class AIMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIMessage
        fields = ['id', 'role', 'content', 'suggestions', 'timestamp']

class AIConversationSerializer(serializers.ModelSerializer):
    messages = AIMessageSerializer(many=True, read_only=True)
    message = serializers.SerializerMethodField()
    draft = serializers.SerializerMethodField()
    
    class Meta:
        model = AIConversation
        fields = ['conversation_id', 'step', 'step_index', 'total_steps', 'step_title', 'message', 'messages', 'extracted_data', 'draft']

    def get_conversation_id(self, obj):
        return str(obj.id)
        
    def get_step_title(self, obj):
        if obj.step == 'industry': return 'Select Industry'
        if obj.step == 'description': return 'Project Concept'
        if obj.step == 'funding': return 'Funding Goals'
        return 'Blueprint Ready!'

    def get_message(self, obj):
        # The frontend wants the LATEST assistant message in this field
        latest = obj.messages.filter(role='assistant').order_by('-timestamp').first()
        if latest:
            return AIMessageSerializer(latest).data
        return None
        
    def get_draft(self, obj):
        if obj.step == 'done':
            # This is where we format the extracted data into a full draft
            return obj.extracted_data.get('draft', None)
        return None
