import json

from accounts.models import PHQ9Assessment, PHQ9Question
from .models import ChatMessage, Conversation, ChatSession
from .chains import ChainStore
from langchain.memory.chat_message_histories.in_memory import ChatMessageHistory
from langchain.memory import ConversationBufferMemory
from langchain_core.messages.ai import AIMessage
from langchain_core.runnables.history import RunnableWithMessageHistory
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models.query import QuerySet
from django.contrib.auth.base_user import AbstractBaseUser
from django.db import transaction


class ChatConfig:

    LAST_N_CONVERSATIONS = 4
    LAST_N_HRS = 600
    SESSION_TIMEOUT = 30  # in minutes


class ChatHistoryService:

    def __init__(self, conversation: Conversation, chat_session: ChatSession = None):
        self.conversation = conversation
        self.conversation_id = conversation.id
        self.chat_session = chat_session

    def get_conversation_history(self) -> ChatMessageHistory:
        """
        Retrieves the full conversation history of user
        """

        memory = ConversationBufferMemory(human_prefix="Patient")
        conversation_context = ChatMessage.objects.filter(
            conversation_id=self.conversation_id
        ).order_by('-timestamp')
        for msg in conversation_context:
            memory.save_context(
                {"input": f"{msg.timestamp.strftime('%Y-%m-%d %H:%M')} -\n {msg.user_response}"},
                {"output": msg.ai_response}
            )
        retrieved_chat_history = ChatMessageHistory(
            messages=memory.chat_memory.messages
        )
        return retrieved_chat_history

    def retrieve_chat_history(self, N: int = ChatConfig.LAST_N_HRS) -> QuerySet[ChatMessage]:
        """
        Retrieves chat history of user for the last N hours
        """

        time_limit = timezone.now() - timedelta(hours=N)
        chat_obj = ChatMessage.objects.filter(conversation_id=self.conversation_id).order_by(
            'timestamp').filter(timestamp__gte=time_limit)
        return chat_obj
    
    def retrieve_chat_history_from_session(self) -> QuerySet[ChatMessage]:
        """
        Retrieves chat history of user for the current session
        """

        chat_obj = ChatMessage.objects.filter(conversation=self.conversation, chat_session=self.chat_session).order_by('timestamp')
        return chat_obj
    
    def chat_filter(self, filters: dict = {}) -> QuerySet[ChatMessage]:
        """
        Filters chat messages based on the given filters

        The `filters` key-value pairs need to be valid django query parameters

        Example usage:
        ```
        chat_filter(
            filters={
                "chat_session_id": chat_session_id,
                "timestamp__gte": timezone.now() - timedelta(hours=1),
                ...
                }
        )
        ```
        """

        if 'conversation_id' in filters or 'conversation' in filters:
            filters.pop('conversation_id', None)
            filters.pop('conversation', None)
        chat_obj = ChatMessage.objects.filter(conversation_id=self.conversation_id).filter(**filters)
        return chat_obj
    
    def get_prev_decision_result(self) -> dict:
        """
        Retrieves the latest decision result from the chat history
        """

        chat_obj = ChatMessage.objects.filter(conversation_id=self.conversation_id).order_by('-timestamp').first()
        return chat_obj.ai_marker if chat_obj else {}


class ChatbotService:

    def __init__(self, conversation: Conversation, chat_session: ChatSession = None):
        self.conversation = conversation
        self.conversation_id = conversation.id
        self.chat_session = chat_session
        self.chat_history_service = ChatHistoryService(self.conversation, self.chat_session)
        try:
            self.patient = conversation.user.patient
        except AttributeError:
            self.patient = None
    
    def get_patient_metrics(self) -> dict:
        assert self.patient, "Patient not found"
        assessment, _ = PHQ9Assessment.objects.get_or_create(patient=self.patient)

        phq9_metrics = {}
        for question_id in range(1, 10):
            question = PHQ9Question.objects.filter(
                assessment=assessment,
                question_id=question_id
            ).order_by('-timestamp').first()
            phq9_metrics[question_id] = question.score if question else -1

        return phq9_metrics

    def invoke_chains(self, user_response: str) -> str:
        assert self.patient, "Patient not found"
        formated_user_response = f"{datetime.now().strftime("%Y-%m-%d %H:%M")} - {user_response}"

        # PHQ9 eval chain
        eval_chain = RunnableWithMessageHistory(
            ChainStore.phq9_eval_chain,
            self.chat_history_service.get_conversation_history,
            input_messages_key="input",
            history_messages_key="history",
        )
        prev_decision_result = self.chat_history_service.get_prev_decision_result()
        interpretation_result = eval_chain.invoke(
            {
                "input": formated_user_response,
                "decision_result": prev_decision_result,
            },
            config={"configurable": {"session_id": self.conversation_id}},
        )
        print("\n\n", interpretation_result.content, "\n\n")
        evaluation = {}
        try:
            evaluation = json.loads(interpretation_result.content)
        except json.JSONDecodeError:
            print("Error decoding json")
        
        # Update patient metrics
        if evaluation.get("evaluation"):
            e = evaluation["evaluation"]
            assert 0 <= e["score"] <= 3, f"Invalid score: {e['score']}"
            assert 1 <= e["id"] <= 9, f"Invalid question_id: {e['id']}"
            assessment, _ = PHQ9Assessment.objects.get_or_create(patient=self.patient)
            question = PHQ9Question.objects.create(
                assessment=assessment,
                question_id=e["id"],
                question_text=e["question"],
                score=e["score"]
            )
            if question: question.save()
        patient_metrics = self.get_patient_metrics()
        
        # PHQ9 decision chain
        decision_chain = RunnableWithMessageHistory(
            ChainStore.phq9_decision_chain,
            self.chat_history_service.get_conversation_history,
            input_messages_key="input",
            history_messages_key="history",
        )
        ai_response = decision_chain.invoke(
            {
                "input": formated_user_response,
                "patient_metrics": json.dumps(patient_metrics),
                "evaluation": interpretation_result.content,
                "prev_decision_result": prev_decision_result,
            },
            config={"configurable": {"session_id": self.conversation_id}},
        )
        print("\n\n", ai_response.content, "\n\n")
        decision_result = {}
        try:
            decision_result = json.loads(ai_response.content)
        except json.JSONDecodeError:
            print("Error decoding json")
        response_to_user = decision_result.get("response_to_user", "")
        with transaction.atomic():
            chat_message = self.save_user_message(user_response, marker=evaluation)
            self.save_ai_message(chat_message, ai_response, parse=True, marker=decision_result)
        return response_to_user

    # NOTE depricated
    def generate_ai_response(self, user_response: str) -> AIMessage:
        runnable_with_message_history = RunnableWithMessageHistory(
            ChainStore.default_chain,
            self.chat_history_service.get_conversation_history,
            input_messages_key="input",
            history_messages_key="history",
        )
        user_response = f"{datetime.now().strftime("%Y-%m-%d %H:%M")} - {user_response}"
        ai_response = runnable_with_message_history.invoke(
            {"input": user_response},
            config={"configurable": {"session_id": self.conversation_id}},
        )
        return ai_response

    # NOTE depricated: use save_user_message and save_ai_message instead
    def save_chat_message(self, user_response: str, ai_response: AIMessage) -> ChatMessage:
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

    def save_user_message(self, user_response: str, marker: dict = {}) -> ChatMessage:
        chat_message = ChatMessage.objects.create(
            user_response=user_response,
            conversation=self.conversation,
            chat_session=self.chat_session,
            user_response_timestamp=timezone.now(),
            user_marker=marker
        )
        return chat_message

    def save_ai_message(self, chat_message: ChatMessage, ai_response: AIMessage, parse: bool = True, marker: dict = {}) -> ChatMessage:
        if parse:
            try:
                content = json.loads(ai_response.content)
            except json.JSONDecodeError:
                print("Error decoding json")
            chat_message.ai_response = content.get("response_to_user", "")
        else: chat_message.ai_response = ai_response.content
        chat_message.meta_data = ai_response.response_metadata
        chat_message.ai_response_timestamp = timezone.now()

        marker.pop("response_to_user", None)
        chat_message.ai_marker = marker
        chat_message.save(
            update_fields=["ai_response", "meta_data", "ai_response_timestamp", "ai_marker"]
        )
        return chat_message


class ConversationService:

    @staticmethod
    def get_or_create_conversation(user: AbstractBaseUser) -> tuple[Conversation, bool]:
        conversation, created = Conversation.objects.get_or_create(user=user)
        return conversation, created

    @staticmethod
    def get_or_create_chat_session(conversation: Conversation) -> tuple[ChatSession, bool]:
        last_message = ChatMessage.objects.filter(
            conversation=conversation).order_by('-timestamp').first()
        created = False
        if last_message:
            if last_message.user_response_timestamp:
                time_inactive = timezone.now() - last_message.user_response_timestamp
            else:
                time_inactive = timezone.now() - last_message.timestamp
            if time_inactive.total_seconds() / 60 > ChatConfig.SESSION_TIMEOUT:
                # check if there is an existing valid session
                last_session = ChatSession.objects.filter(conversation=conversation).order_by('-timestamp').first()
                if last_session and last_session.timestamp > last_message.timestamp:
                    chat_session = last_session
                    chat_session.timestamp = timezone.now()
                    chat_session.save(update_fields=['timestamp'])
                else:
                    chat_session = ChatSession.objects.create(conversation=conversation)
                    created = True
            else:
                chat_session = last_message.chat_session
        else:
            chat_session, created = ChatSession.objects.get_or_create(conversation=conversation)
            if created:
                chat_session.timestamp = timezone.now()
                chat_session.save(update_fields=['timestamp'])
        return chat_session, created
