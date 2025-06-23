from django.db import models
from django.contrib.auth.models import User
import uuid

class ChatSession(models.Model):
    session_id = models.UUIDField(default=uuid.uuid4, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)  # Make this required
    title = models.CharField(max_length=200, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        # Auto-generate title from first user message if not set
        if not self.title and self.pk:
            first_message = self.messages.filter(message_type='user').first()
            if first_message:
                self.title = first_message.content[:50] + "..." if len(first_message.content) > 50 else first_message.content
        super().save(*args, **kwargs)
    
    class Meta:
        ordering = ['-updated_at']

class ChatMessage(models.Model):
    MESSAGE_TYPES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
    ]
    
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    message_type = models.CharField(choices=MESSAGE_TYPES, max_length=10)
    content = models.TextField()
    mermaid_code = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['timestamp']

class DiagramHistory(models.Model):
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, null=True, blank=True)
    user_prompt = models.TextField()
    mermaid_code = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
