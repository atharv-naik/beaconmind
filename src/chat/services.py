import json
from datetime import datetime, timedelta

from django.contrib.auth.base_user import AbstractBaseUser
from django.db import transaction
from django.db.models.query import QuerySet
from django.utils import timezone
from langchain.memory import ConversationBufferMemory
from langchain.memory.chat_message_histories.in_memory import \
    ChatMessageHistory
from langchain_core.messages.ai import AIMessage
from langchain_core.runnables.history import RunnableWithMessageHistory

from assessments.models import Assessment, AssessmentRecord
from assessments.definitions import PhaseMap

from .chains import ChainStore
from .models import ChatMessage, ChatSession, Conversation


class ChatConfig:

    LAST_N_CONVERSATIONS = 4
    LAST_N_HRS = 600
    SESSION_TIMEOUT = 60 * 24  # in minutes


class ChatHistoryService:

    def __init__(self, conversation: Conversation, chat_session: ChatSession = None):
        self.conversation = conversation
        self.conversation_id = conversation.id
        self.chat_session = chat_session

    def get_chat_history(self) -> ChatMessageHistory:
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
        self.patient = conversation.user.patient
        self.phase = PhaseMap.get(self.patient.phase)
    
    def get_or_create_assessment(self, type: str) -> tuple[Assessment, bool]:
        assessments = Assessment.objects.filter(patient=self.patient, type=type)
        if assessments.exists():
            assessment = assessments.last()
            created = False
        else:
            assessment = Assessment.objects.create(patient=self.patient, type=type)
            created = True
        return assessment, created

    def get_patient_metrics(self) -> dict:
        assessment, _ = self.get_or_create_assessment(self.phase.verbose_name)

        metrics = {}
        for q_id in range(1, self.phase.N + 1):
            record = AssessmentRecord.objects.filter(
                assessment=assessment,
                question_id=q_id
            ).order_by('-timestamp').first()
            if record:
                metrics[q_id] = record.score 
            else:
                metrics[q_id] = -1
        return metrics

    def invoke_chains(self, user_response: str) -> str:
        formated_user_response = f"{datetime.now().strftime("%Y-%m-%d %H:%M")} - {user_response}"
        prev_decision_result = self.chat_history_service.get_prev_decision_result()

        # PHQ9 eval chain
        eval_chain = RunnableWithMessageHistory(
            ChainStore.phq9_eval_chain,
            self.chat_history_service.get_chat_history,
            input_messages_key="input",
            history_messages_key="history",
        )
        eval_response: AIMessage = eval_chain.invoke(
            {
                "input": formated_user_response,
                "patient_metrics": json.dumps(self.get_patient_metrics()),
                "decision_result": prev_decision_result,
            },
            config={"configurable": {"session_id": self.conversation_id}},
        )
        interpretation_result = json.loads(eval_response.content)

        # Update patient metrics
        if interpretation_result.get("evaluation"):
            e = interpretation_result["evaluation"]
            assessment, _ = self.get_or_create_assessment(self.phase.verbose_name)
            record = AssessmentRecord.objects.create(
                assessment=assessment,
                question_id=e["id"],
                question_text=e["question"],
                score=e["score"]
            )
            if record:
                record.save()
        metrics = self.get_patient_metrics()
        if len([v for v in metrics.values() if v != -1]) == self.phase.N:
            interpretation_result["chat_status"] = "CONCLUDE"
        u_metrics = [k for k, v in metrics.items() if v == -1] # unevaluated metrics
    
        # PHQ9 decision chain
        decision_chain = RunnableWithMessageHistory(
            ChainStore.phq9_decision_chain,
            self.chat_history_service.get_chat_history,
            input_messages_key="input",
            history_messages_key="history",
        )
        decision_response: AIMessage = decision_chain.invoke(
            {
                "input": formated_user_response,
                "u_metrics": str(u_metrics),
                "evaluation": json.dumps(interpretation_result),
                "prev_decision_result": prev_decision_result,
            },
            config={"configurable": {"session_id": self.conversation_id}},
        )
        decision_result = json.loads(decision_response.content)
        response_to_user = decision_result.get("response_to_user", "")

        with transaction.atomic():
            msg = self.save_user_message(user_response, marker=interpretation_result)
            self.save_ai_message(
                msg,
                decision_response,
                parse=True,
                marker=decision_result
            )
        return response_to_user

    def save_user_message(self, user_response: str, marker: dict = {}) -> ChatMessage:
        msg = ChatMessage.objects.create(
            user_response=user_response,
            conversation=self.conversation,
            chat_session=self.chat_session,
            user_response_timestamp=timezone.now(),
            user_marker=marker
        )
        return msg

    @staticmethod
    def save_ai_message(
            chat_message: ChatMessage,
            ai_response: AIMessage,
            parse: bool = True,
            marker: dict = {}
        ) -> ChatMessage:
        if parse:
            content = json.loads(ai_response.content)
            chat_message.ai_response = content.get("response_to_user", "")
        else:
            chat_message.ai_response = ai_response.content
        chat_message.meta_data = ai_response.response_metadata
        chat_message.ai_response_timestamp = timezone.now()

        marker.pop("response_to_user", None)
        chat_message.ai_marker = marker
        chat_message.save(
            update_fields=[
                "ai_response",
                "meta_data",
                "ai_response_timestamp", 
                "ai_marker",
            ]
        )
        return chat_message


class ConversationService:

    @staticmethod
    def get_or_create_conversation(user: AbstractBaseUser) -> tuple[Conversation, bool]:
        conversation, created = Conversation.objects.get_or_create(user=user)
        return conversation, created

    @staticmethod
    def get_or_create_chat_session(conversation: Conversation) -> tuple[ChatSession, bool]:
        last_message = ChatMessage.objects.filter(conversation=conversation).order_by('-timestamp').first()
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
