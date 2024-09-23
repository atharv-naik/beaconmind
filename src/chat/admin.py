from django.contrib import admin
from .models import Conversation, ChatMessage, ChatSession


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'total_sessions', 'total_messages')
    search_fields = ('user__username',)
    readonly_fields = ('id', 'user')
    list_filter = ('user__is_active',)
    ordering = ('-user__date_joined',)

    def total_sessions(self, obj):
        return obj.chatsession_set.count()
    total_sessions.short_description = 'Total Sessions'

    def total_messages(self, obj):
        return obj.chatmessage_set.count()
    total_messages.short_description = 'Total Messages'


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'conversation', 'chat_session', 'user_response_excerpt',
                    'ai_response_excerpt', 'user_response_timestamp', 'ai_response_timestamp', 'timestamp')
    search_fields = ('user_response', 'ai_response',
                     'conversation__user__username')
    readonly_fields = ('id', 'conversation', 'chat_session', 'timestamp')
    list_filter = ('conversation__user__is_active',
                   'timestamp', 'chat_session')
    ordering = ('-timestamp',)

    def user_response_excerpt(self, obj):
        u_resp = obj.user_response
        if u_resp:
            return u_resp[:50] + ('...' if len(u_resp) > 50 else '')
        return 'No Response'
    user_response_excerpt.short_description = 'User Response Excerpt'

    def ai_response_excerpt(self, obj):
        ai_resp = obj.ai_response
        if ai_resp:
            return ai_resp[:50] + ('...' if len(ai_resp) > 50 else '')
        return 'No Response'
    ai_response_excerpt.short_description = 'AI Response Excerpt'


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'conversation', 'total_messages',
                    'timestamp', 'session_duration')
    search_fields = ('conversation__user__username',)
    readonly_fields = ('id', 'conversation', 'timestamp')
    list_filter = ('timestamp',)
    ordering = ('-timestamp',)

    def total_messages(self, obj):
        return obj.chatmessage_set.count()
    total_messages.short_description = 'Total Messages'

    def session_duration(self, obj):
        # get the first and last message of the session; in minutes
        chat_messages = obj.chatmessage_set.order_by('timestamp')
        if chat_messages:
            first_message = chat_messages.first()
            last_message = chat_messages.last()
            duration = last_message.ai_response_timestamp - \
                first_message.user_response_timestamp
            hrs = duration.seconds // 3600
            mins = (duration.seconds // 60) % 60
            secs = duration.seconds % 60
            if hrs:
                return f"{hrs}:{mins:02d}:{secs:02d}s"
            return f"{mins}:{secs:02d}s"
        return 'No Messages'
    session_duration.short_description = 'Session duration'
