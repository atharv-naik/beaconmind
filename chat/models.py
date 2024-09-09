from django.db import models
from django.conf import settings
from shortuuid.django_fields import ShortUUIDField
from django.utils import timezone


class Conversation(models.Model):
    id = ShortUUIDField(primary_key=True, prefix='conv_')
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    def __str__(self):
        return f"Conversation with {self.user.username}"

class ChatMessage(models.Model):
    id = ShortUUIDField(primary_key=True, prefix='msg_')
    conversation = models.ForeignKey(Conversation, default=None, on_delete=models.CASCADE)
    chat_session = models.ForeignKey('ChatSession', default=None, on_delete=models.CASCADE, null=True)
    user_response = models.TextField(null=True, default='')
    ai_response = models.TextField(null=True, default='')
    user_response_timestamp = models.DateTimeField(null=True)
    ai_response_timestamp = models.DateTimeField(null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    meta_data = models.JSONField(null=True, default=dict)

    def __str__(self):
        user_response_excerpt = self.user_response[:50] + ('...' if len(self.user_response) > 50 else '')
        return f"Message in {self.conversation.user.username}'s conversation: '{user_response_excerpt}'"

class ChatSession(models.Model):
    id = ShortUUIDField(primary_key=True, prefix='sess_')
    conversation = models.ForeignKey(Conversation, default=None, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True, editable=True)

    def __str__(self):
        return f"Session at {timezone.localtime(self.timestamp).strftime('%Y-%m-%d %H:%M:%S')} for {self.conversation.user.username}"
