from rest_framework import serializers
from .models import ChatMessage, Conversation, ChatSession


class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = [
            'id',
            'conversation',
            'chat_session',
            'user_response',
            'ai_response',
            'user_response_timestamp',
            'ai_response_timestamp',
            'timestamp',
        ]

class ConversationSerializer(serializers.ModelSerializer):
    class Meta:
        model= Conversation
        fields= '__all__'

class ChatSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model= ChatSession
        fields= '__all__'
