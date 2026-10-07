import uuid
from django.db import models
from django.conf import settings

class AIConversation(models.Model):
    id = models.CharField(max_length=50, primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ai_conversations")
    step = models.CharField(max_length=50, default="industry")
    step_index = models.IntegerField(default=1)
    total_steps = models.IntegerField(default=4)
    extracted_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Conversation {self.id} (User: {self.user.email})"

class AIMessage(models.Model):
    ROLE_CHOICES = (
        ('assistant', 'Assistant'),
        ('user', 'User'),
    )
    id = models.CharField(max_length=50, primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(AIConversation, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()
    suggestions = models.JSONField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.role.capitalize()}: {self.content[:50]}..."
