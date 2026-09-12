from typing import Optional
from django.db import transaction
from django.contrib.auth import get_user_model

from projects.models import Project
from .models import (
    Conversation, 
    ConversationParticipant, 
    Message,
    Notification,
    NotificationType
)

User = get_user_model()

class ChatService:
    """
    Business logic for chat and AI features.
    """

    @staticmethod
    @transaction.atomic
    def start_conversation(
        creator: User, 
        is_group: bool = False,
        project: Optional[Project] = None, 
        target_user: Optional[User] = None
    ) -> Conversation:
        """
        Initializes a conversation and its participants.
        """
        if project:
            conversation, created = Conversation.objects.get_or_create(
                project=project,
                is_group=True
            )
            if created:
                conversation.participants.add(project.sponsor.user)
                if creator != project.sponsor.user:
                    conversation.participants.add(creator)
            else:
                conversation.participants.add(creator)
            return conversation
            
        elif target_user:
            if target_user == creator:
                raise ValueError("Cannot start a conversation with yourself.")
                
            conversations = Conversation.objects.filter(is_group=False, participants=creator).filter(participants=target_user)
            if conversations.exists():
                return conversations.first()
                
            conversation = Conversation.objects.create(is_group=False)
            conversation.participants.add(creator, target_user)
            return conversation
            
        raise ValueError("Provide either target_user_id or project_id.")

    @staticmethod
    @transaction.atomic
    def send_message(sender: User, conversation: Conversation, content: str) -> Message:
        """
        Sends a user message and triggers VentureAI response logic.
        """
        # Save user message
        message = Message.objects.create(
            conversation=conversation,
            sender=sender,
            content=content,
            is_ai_generated=False
        )
        
        conversation.save() # Touch updated_at
        
        # Notify other participants (simplified)
        participants = conversation.participants.exclude(id=sender.id)
        for participant in participants:
            Notification.objects.create(
                recipient=participant,
                notification_type=NotificationType.MESSAGE,
                title="New Message" if not conversation.is_group else f"New message in {conversation.project.title}",
                message=f"{sender.full_name or sender.email}: {content[:50]}...",
                related_object_id=str(conversation.id)
            )
            
        # Simulate AI Agent response if it's a group chat and question is asked
        if conversation.is_group and "?" in content:
            Message.objects.create(
                conversation=conversation,
                sender=sender, # Ideally system sender, but we flag it
                content=f"💡 VentureAI Tip: Consider discussing your active user metrics and retention rate next.",
                is_ai_generated=True
            )
            
        return message
