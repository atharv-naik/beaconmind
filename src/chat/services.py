import json
from datetime import timedelta
from typing import Union

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

    def get_full(self) -> ChatMessageHistory:
        """
        Retrieves the full conversation history of user
        """
        memory = ConversationBufferMemory(human_prefix="Patient")
        conversation_context = ChatMessage.objects.filter(
            conversation_id=self.conversation_id
        ).order_by('-timestamp')
        for msg in conversation_context:
            memory.save_context(
                {"input": self.format_msg(msg)},
                {"output": msg.ai_response}
            )
        retrieved_chat_history = ChatMessageHistory(
            messages=memory.chat_memory.messages
        )
        return retrieved_chat_history

    def get_recent(self, N: int = ChatConfig.LAST_N_HRS) -> QuerySet[ChatMessage]:
        """
        Retrieves chat history of user for the last N hours
        """

        time_limit = timezone.now() - timedelta(hours=N)
        chat_obj = ChatMessage.objects.filter(conversation_id=self.conversation_id).order_by(
            'timestamp').filter(timestamp__gte=time_limit)
        return chat_obj

    def get_from_session(self) -> QuerySet[ChatMessage]:
        """
        Retrieves chat history of user for the current session
        """

        chat_obj = ChatMessage.objects.filter(conversation=self.conversation, chat_session=self.chat_session).order_by('timestamp')
        return chat_obj

    def filter_by(self, filters: dict = {}) -> QuerySet[ChatMessage]:
        """
        Filters chat messages based on the given filters

        The `filters` key-value pairs need to be valid django query parameters

        Example usage:
        ```
        filter_by(
            filters={
                "chat_session_id": chat_session_id,
                "timestamp__gte": timezone.now() - timedelta(hours=1), # last 1 hour
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

    def get_last_decision(self) -> dict:
        """
        Retrieves the latest decision result from the chat history.
        """
        chat_obj = (
            ChatMessage.objects.filter(conversation_id=self.conversation_id)
            .values('ai_marker')
            .order_by('-timestamp')
            .first()
        )
        return chat_obj["ai_marker"] if chat_obj else {}

    @staticmethod
    def format_msg(msg: Union[str, ChatMessage]) -> str:
        if isinstance(msg, ChatMessage):
            return f"{timezone.localtime(msg.timestamp).strftime("%-d %b %Y %-I:%M%p").lower()} -\n {msg.user_response}"
        return f"{timezone.localtime(timezone.now()).strftime("%-d %b %Y %-I:%M%p").lower()} -\n {msg}"

class ChatbotService:

    def __init__(self, conversation: Conversation, chat_session: ChatSession = None):
        self.conversation = conversation
        self.conversation_id = conversation.id
        self.chat_session = chat_session
        self.chat_history_service = ChatHistoryService(self.conversation, self.chat_session)
        self.patient = conversation.user.patient
        self.phase = PhaseMap.get(self.patient.phase)
    

    def get_patient_metrics(self) -> dict:
        assessment, _ = Assessment.objects.get_or_create(patient=self.patient, type=self.phase.name, status="pending")

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
    
    def run_chain(self, mode, data: dict) -> AIMessage:
        assert "input" in data, "Input message is required"
        
        chain = RunnableWithMessageHistory(
            ChainStore.get(self.phase.short_name, mode),
            self.chat_history_service.get_full,
            input_messages_key="input",
            history_messages_key="history",
        )
        response: AIMessage = chain.invoke(
            data,
            config={"configurable": {"session_id": self.conversation_id}},
        )
        return response

    def trigger_pipeline(self, user_response: str) -> str:
        formated_user_response = self.chat_history_service.format_msg(user_response)
        prev_decision_result = self.chat_history_service.get_last_decision()

        # eval chain
        eval_response = self.run_chain(
            mode="eval",
            data={
                "input": formated_user_response,
                "patient_metrics": json.dumps(self.get_patient_metrics()),
                "decision_result": prev_decision_result,
            }
        )
        interpretation_result = json.loads(eval_response.content)

        # Update patient metrics
        if e := interpretation_result.get("evaluation"):
            assessment, _ = Assessment.objects.get_or_create(self.patient, self.phase.name, "pending")
            record, _ = AssessmentRecord.objects.update_or_create(
                assessment=assessment,
                question_id=e["id"],
                defaults={
                    "question_id": e["id"],
                    "question_text": self.phase.get(e["id"]),
                    "score": e["score"]
                }
            )
        
        metrics = self.get_patient_metrics()
        if len([v for v in metrics.values() if v != -1]) == self.phase.N:
            interpretation_result["chat_status"] = "CONCLUDE"
            # TODO: 
            # 1. Add chain to re-evaluate assessment and assign final scores
            # 2. Compute and assign total final score and severity (AssessmentResult)
            # 3. Mark assessment as "completed"
            # 4. Update patient.phase to point to next phase (if any)
            # 5. Add a conclude chain; invoke with new phase info; return response
        
        u_metrics = [k for k, v in metrics.items() if v == -1] # unevaluated metrics
    
        # decision chain
        decision_response = self.run_chain(
            mode="decision",
            data={
                "input": formated_user_response,
                "u_metrics": str(u_metrics),
                "evaluation": json.dumps(interpretation_result),
                "prev_decision_result": prev_decision_result,
            }
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
