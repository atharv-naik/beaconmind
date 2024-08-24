from .models import ChatMessage, Conversation
from .chains import Chains
from langchain.memory.chat_message_histories.in_memory import ChatMessageHistory
from langchain.memory import ConversationBufferMemory
from langchain_core.runnables.history import RunnableWithMessageHistory
from datetime import timedelta
from django.utils import timezone
from django.db.models.query import QuerySet
from django.contrib.auth.base_user import AbstractBaseUser


class BaseService:

    LAST_N_CONVERSATIONS = 4
    LAST_N_HRS = 60


class ChatHistoryService(BaseService):

    def __init__(self, conversation_id):
        self.conversation_id = conversation_id

    def get_conversation_history(self) -> ChatMessageHistory:
        """
        Retrieves the full conversation history of user
        """

        memory = ConversationBufferMemory()
        conversation_context = ChatMessage.objects.filter(
            conversation_id=self.conversation_id
        ).order_by('-timestamp')
        for msg in conversation_context:
            memory.save_context({"input": msg.user_response},
                                {"output": msg.ai_response})
        retrieved_chat_history = ChatMessageHistory(
            messages=memory.chat_memory.messages
        )
        return retrieved_chat_history

    def retrieve_chat_history(self, N: int = BaseService.LAST_N_HRS) -> QuerySet[ChatMessage]:
        """
        Retrieves chat history of user for the last N hours
        """

        time_limit = timezone.now() - timedelta(hours=N)
        chat_obj = ChatMessage.objects.filter(conversation_id=self.conversation_id).order_by(
            'timestamp').filter(timestamp__gte=time_limit)
        return chat_obj


class ChatbotService:

    def __init__(self, conversation_id):
        self.conversation_id = conversation_id
        self.chat_history_service = ChatHistoryService(conversation_id)

    def generate_ai_response(self, user_response: str) -> dict:
        runnable_with_message_history = RunnableWithMessageHistory(
            Chains.default_chain,
            self.chat_history_service.get_conversation_history,
            input_messages_key="input",
            history_messages_key="history",
        )
        ai_response = runnable_with_message_history.invoke(
            {"input": user_response},
            config={"configurable": {"session_id": self.conversation_id}},
        )
        return ai_response

    # NOTE depricated: use save_user_message and save_ai_message instead
    def save_chat_message(self, user_response: str, ai_response: dict) -> ChatMessage:
        """
        NOTE: This method is deprecated. Use save_user_message and save_ai_message instead.
        
        Saves the full chat message (user + ai response) in the database.
        Does not account for the timestamp of user response
        """

        chat_message = ChatMessage.objects.create(
            user_response=user_response,
            ai_response=ai_response.content,
            conversation_id=self.conversation_id,
            meta_data=ai_response.response_metadata,
        )
        return chat_message

    def save_user_message(self, user_response: str) -> ChatMessage:
        chat_message = ChatMessage.objects.create(
            user_response=user_response,
            conversation_id=self.conversation_id,
            user_response_timestamp=timezone.now()
        )
        return chat_message

    def save_ai_message(self, chat_message: ChatMessage, ai_response: dict) -> ChatMessage:
        chat_message.ai_response = ai_response.content
        chat_message.meta_data = ai_response.response_metadata
        chat_message.ai_response_timestamp = timezone.now()
        chat_message.save(
            update_fields=["ai_response", "meta_data", "ai_response_timestamp"]
        )
        return chat_message


class ConversationService:

    @staticmethod
    def get_or_create_conversation(user: AbstractBaseUser) -> Conversation:
        conversation, _ = Conversation.objects.get_or_create(user=user)
        return conversation
