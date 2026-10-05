import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Conversation, Message, MessageType
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.room_group_name = f'chat_{self.conversation_id}'
        self.user = self.scope['user']

        if self.user.is_anonymous:
            await self.close(code=4003)
            return

        # Check if user is participant
        is_participant = await self.is_user_in_conversation()
        if not is_participant:
            await self.close(code=4003)
            return

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # Receive message from WebSocket
    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return

        event_type = data.get('type')

        if event_type == 'ping':
            await self.send(text_data=json.dumps({'type': 'pong'}))
            
        elif event_type == 'typing':
            is_typing = data.get('is_typing', False)
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'user_typing',
                    'user_id': self.user.id,
                    'user_name': self.user.full_name or self.user.email,
                    'is_typing': is_typing
                }
            )

        elif event_type == 'mark_read':
            last_message_id = data.get('last_message_id')
            await self.update_last_read(last_message_id)
            
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'messages_read',
                    'conversation_id': int(self.conversation_id),
                    'reader_id': self.user.id,
                    'reader_name': self.user.full_name or self.user.email,
                    'last_read_message_id': last_message_id
                }
            )

        elif event_type == 'send_message':
            message_type = data.get('message_type', 'text')
            text = data.get('text', '')
            media_url = data.get('media_url')
            voice_duration = data.get('voice_duration')

            msg = await self.save_message(message_type, text, media_url, voice_duration)
            
            # Send message to room group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': msg
                }
            )

    # Handlers for messages broadcasted via group_send

    async def user_typing(self, event):
        # Don't echo back to the sender
        if event['user_id'] != self.user.id:
            await self.send(text_data=json.dumps(event))

    async def messages_read(self, event):
        if event['reader_id'] != self.user.id:
            await self.send(text_data=json.dumps(event))

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'new_message',
            'message': event['message']
        }))
        
    async def ai_suggestion(self, event):
        # Only send AI suggestions to Sponsors
        if hasattr(self.user, 'sponsor_profile'):
            await self.send(text_data=json.dumps(event))

    async def participant_removed(self, event):
        await self.send(text_data=json.dumps(event))

    # --- Database Operations ---

    @database_sync_to_async
    def is_user_in_conversation(self):
        try:
            conv = Conversation.objects.get(id=self.conversation_id)
            return conv.participants.filter(id=self.user.id).exists()
        except Conversation.DoesNotExist:
            return False

    @database_sync_to_async
    def update_last_read(self, message_id):
        # Update the ConversationParticipant last_read_at
        try:
            conv = Conversation.objects.get(id=self.conversation_id)
            participant = conv.conversationparticipant_set.get(user=self.user)
            participant.last_read_at = timezone.now()
            participant.save(update_fields=['last_read_at'])
        except Exception:
            pass

    @database_sync_to_async
    def save_message(self, msg_type, text, media_url, voice_duration):
        msg = Message.objects.create(
            conversation_id=self.conversation_id,
            sender=self.user,
            message_type=msg_type,
            content=text,
            media_url=media_url,
            voice_duration=voice_duration
        )
        
        # Determine avatar type
        role = "User"
        avatar_type = "user"
        if hasattr(self.user, 'sponsor_profile'):
            role = "Sponsor"
            avatar_type = "sponsor"
        elif hasattr(self.user, 'investor_profile'):
            role = "Investor"
            avatar_type = "investor"
            
        initials = (self.user.first_name[0] if self.user.first_name else "") + (self.user.last_name[0] if self.user.last_name else "")
        if not initials:
            initials = self.user.email[0].upper()

        return {
            'id': msg.id,
            'conversation_id': int(self.conversation_id),
            'sender_id': self.user.id,
            'sender_name': self.user.full_name or self.user.email,
            'sender_role': role,
            'avatar_initials': initials.upper(),
            'avatar_type': avatar_type,
            'is_ai': False,
            'is_me': False, # the client will determine this by comparing sender_id
            'message_type': msg_type,
            'text': text,
            'media_url': media_url,
            'voice_duration': voice_duration,
            'created_at': msg.created_at.isoformat()
        }
