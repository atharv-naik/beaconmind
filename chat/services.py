from .models import ChatMessage, Conversation
from .chains import Chains
from langchain.memory.chat_message_histories.in_memory import ChatMessageHistory
from langchain.memory import ConversationBufferMemory
from langchain_core.runnables.history import RunnableWithMessageHistory
from datetime import timedelta
from django.utils import timezone


class ChatHistoryService:
    
    LAST_N_CONVERSATIONS = 4
    LAST_N_HRS = 60

    def __init__(self, conversation_id):
        self.conversation_id = conversation_id

    def get_session_history(self):
        memory = ConversationBufferMemory()
        conversation_context = ChatMessage.objects.filter(
            conversation_id=self.conversation_id
        ).order_by('-timestamp')[:self.LAST_N_CONVERSATIONS:-1]
        for msg in conversation_context:
            memory.save_context({"input": msg.user_response},
                                {"output": msg.ai_response})
        retrieved_chat_history = ChatMessageHistory(
            messages=memory.chat_memory.messages
        )
        return retrieved_chat_history

    def retrieve_chat_history(self):
        time_limit = timezone.now() - timedelta(hours=self.LAST_N_HRS)
        chat_obj = ChatMessage.objects.filter(conversation_id=self.conversation_id).order_by(
            'timestamp').filter(timestamp__gte=time_limit)
        return chat_obj


class ChatbotService:

    def __init__(self, conversation_id):
        self.conversation_id = conversation_id
        self.chat_history_service = ChatHistoryService(conversation_id)

    def generate_ai_response(self, user_response):
        runnable_with_message_history = RunnableWithMessageHistory(
            Chains.default_chain,
            self.chat_history_service.get_session_history,
            input_messages_key="input",
            history_messages_key="history",
        )
        ai_response = runnable_with_message_history.invoke(
            {"input": user_response},
            config={"configurable": {"session_id": self.conversation_id}},
        )
        return ai_response

    def save_chat_message(self, user_response, ai_response):
        ChatMessage.objects.create(
            user_response=user_response,
            ai_response=ai_response.content,
            conversation_id=self.conversation_id,
            meta_data=ai_response.response_metadata,
        )


class ConversationService:

    @staticmethod
    def get_or_create_conversation(user):
        conversation, _ = Conversation.objects.get_or_create(user=user)
        return conversation
