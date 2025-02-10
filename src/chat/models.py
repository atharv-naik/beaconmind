from django.conf import settings
from django.db import models
from django.utils import timezone
from shortuuid.django_fields import ShortUUIDField


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
    ai_response = models.TextField(verbose_name="AI response", null=True, default='')
    user_response_timestamp = models.DateTimeField(null=True)
    ai_marker = models.JSONField(verbose_name="AI marker", null=True, default=dict)
    user_marker = models.JSONField(null=True, default=dict)
    ai_response_timestamp = models.DateTimeField(verbose_name="AI response timestamp", null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    meta_data = models.JSONField(null=True, default=dict)

    class Meta:
        ordering = ['timestamp']
        verbose_name = 'Chat Message'
        verbose_name_plural = 'Chat Messages'

    def __str__(self):
        user_response_excerpt = self.user_response[:50] + ('...' if len(self.user_response) > 50 else '')
        return f"{self.conversation.user.username} message: '{user_response_excerpt}'"

class ChatSession(models.Model):
    _status = (
        ('open', 'Open'),
        ('closed', 'Closed'),
        ('aborted', 'Aborted'),
    )
    id = ShortUUIDField(primary_key=True, prefix='sess_')
    conversation = models.ForeignKey(Conversation, default=None, on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=_status, default='open')
    timestamp = models.DateTimeField(auto_now_add=True, editable=True)

    class Meta:
        ordering = ['timestamp']
        verbose_name = 'Chat Session'
        verbose_name_plural = 'Chat Sessions'

    def __str__(self):
        return f"{self.conversation.user.username} - session @ {timezone.localtime(self.timestamp).strftime('%b. %d, %Y, %I:%M %p').lower().capitalize()}"
