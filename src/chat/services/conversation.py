from datetime import timedelta
from typing import List, Tuple, Union

from django.contrib.auth.base_user import AbstractBaseUser
from django.db.models.query import QuerySet
from django.utils import timezone
from langchain.memory import ConversationBufferMemory
from langchain.memory.chat_message_histories.in_memory import \
    ChatMessageHistory

from ..models import ChatMessage, ChatSession, Conversation
from .config import ChatSettings
from assessments.definitions import PhaseMap


class HistoryManager:

    def __init__(self, conversation: Conversation, chat_session: ChatSession = None):
        self.conversation = conversation
        self.conversation_id = conversation.id
        self.chat_session = chat_session

    def get_full(self) -> ChatMessageHistory:
        """
        Retrieves full chat history of user in `ChatMessageHistory` format
        """
        memory = ConversationBufferMemory(human_prefix="Patient")
        messages = ChatMessage.objects.filter(
            conversation_id=self.conversation_id
        ).order_by('-timestamp')
        for msg in messages:
            memory.save_context(
                {"input": ConversationManager.format_msg(msg)},
                {"output": msg.ai_response}
            )
        retrieved_chat_history = ChatMessageHistory(
            messages=memory.chat_memory.messages
        )
        return retrieved_chat_history
    
    def get_full_list(self) -> List[Tuple[str, str]]:
        """
        Retrieves full chat history of user in list format
        """
        chat_obj = ChatMessage.objects.filter(
            conversation_id=self.conversation_id).order_by('-timestamp')
        chat_history = []
        for msg in chat_obj:
            chat_history.append(
                ("human", ConversationManager.format_msg(msg))
            )
            chat_history.append(
                ("ai", msg.ai_response)
            )
        return chat_history

    def get_full_qs(self) -> QuerySet[ChatMessage]:
        """
        Retrieves full chat history of user in QuerySet format
        """
        chat_obj = ChatMessage.objects.filter(
            conversation_id=self.conversation_id).order_by('timestamp')
        return chat_obj

    def get_recent(self, N: int = ChatSettings.LAST_N_HRS) -> QuerySet[ChatMessage]:
        """
        Retrieves chat messages of user from the last N hours
        """

        time_limit = timezone.now() - timedelta(hours=N)
        chat_obj = ChatMessage.objects.filter(conversation_id=self.conversation_id).order_by(
            'timestamp').filter(timestamp__gte=time_limit)
        return chat_obj

    def get_from_session(self) -> QuerySet[ChatMessage]:
        """
        Retrieves chat messages of user from the current chat session
        """

        chat_obj = ChatMessage.objects.filter(
            conversation=self.conversation, chat_session=self.chat_session).order_by('timestamp')
        return chat_obj

    def filter_by(self, *q_filters, **filters) -> QuerySet[ChatMessage]:
        """
        Filters chat messages based on the given Q objects and filters.

        The Q objects are evaluated with AND logic (unless combined differently)
        and the kwargs are standard Django query parameters.

        Example usage:
        ```
        filter_by(
            Q(chat_session_id=chat_session_id),
            Q(timestamp__gte=timezone.now() - timedelta(hours=1)) | Q(some_field="value"),
            status="active",
            ...
        )
        ```
        """
        # Remove conversation-related filters from kwargs if present.
        filters.pop('conversation_id', None)
        filters.pop('conversation', None)
        
        qs = ChatMessage.objects.filter(conversation_id=self.conversation_id)
        
        # Apply any Q objects passed as positional arguments.
        if q_filters:
            qs = qs.filter(*q_filters)
        
        # Apply the remaining keyword filters.
        qs = qs.filter(**filters)
    
        return qs

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
    def qs_to_list(chat_obj: QuerySet[ChatMessage]) -> List[Tuple[str, str]]:
        chat_history = []
        for msg in chat_obj:
            chat_history.append(
                ("human", ConversationManager.format_msg(msg))
            )
            chat_history.append(
                ("ai", msg.ai_response)
            )
        return chat_history
    
    @staticmethod
    def qs_to_dict(chat_obj: QuerySet[ChatMessage]) -> dict:
        """
        More detailed than `qs_to_list`, returns a dictionary of chat messages. Adds markers and timestamps.
        """
        chat_history = {}
        for msg in chat_obj:
            chat_history[msg.id] = {
                "human": ConversationManager.format_msg(msg),
                "ai": msg.ai_response,
                "ai_marker": msg.ai_marker,
                "user_marker": msg.user_marker,
                "timestamp": msg.timestamp.strftime("%-d %b %Y %-I:%M%p").lower(),
            }
        return chat_history
    
    def get_full_list_from_session(self) -> List[Tuple[str, str]]:
        chat_obj = self.get_from_session()
        return self.qs_to_list(chat_obj)


class ConversationManager:

    @staticmethod
    def format_msg(msg: Union[str, ChatMessage]) -> str:
        if isinstance(msg, ChatMessage):
            return f"{timezone.localtime(msg.timestamp).strftime("%-d %b %Y %-I:%M%p").lower()} -\n {msg.user_response}"
        return f"{timezone.localtime(timezone.now()).strftime("%-d %b %Y %-I:%M%p").lower()} -\n {msg}"

    @staticmethod
    def get_or_create_conversation(user: AbstractBaseUser) -> tuple[Conversation, bool]:
        conversation, created = Conversation.objects.get_or_create(user=user)
        return conversation, created

    @staticmethod
    def get_or_create_chat_session(conversation: Conversation) -> tuple[ChatSession, bool]:
        # last_message = ChatMessage.objects.filter(
        #     conversation=conversation).order_by('-timestamp').first()
        # created = False
        # if last_message:
        #     if last_message.user_response_timestamp:
        #         time_inactive = timezone.now() - last_message.user_response_timestamp
        #     else:
        #         time_inactive = timezone.now() - last_message.timestamp
        #     if time_inactive.total_seconds() / 60 > ChatSettings.SESSION_TIMEOUT:
        #         # check if there is an existing valid session
        #         last_session = ChatSession.objects.filter(
        #             conversation=conversation).order_by('-timestamp').first()
        #         if last_session and last_session.timestamp > last_message.timestamp:
        #             chat_session = last_session
        #             chat_session.timestamp = timezone.now()
        #             chat_session.save(update_fields=['timestamp'])
        #         else:
        #             chat_session = ChatSession.objects.create(
        #                 conversation=conversation)
        #             created = True
        #     else:
        #         chat_session = last_message.chat_session
        # else:
        #     chat_session, created = ChatSession.objects.get_or_create(
        #         conversation=conversation)
        #     if created:
        #         chat_session.timestamp = timezone.now()
        #         chat_session.save(update_fields=['timestamp'])
        # return chat_session, created

        chat_session, created = ChatSession.objects.get_or_create(
            conversation=conversation, 
            status='open',
            defaults={
                'init': True,
                'phase': PhaseMap.first(),
                'node_id': PhaseMap.get(PhaseMap.first()).base_node_id,
                'retries': 0,
                'last_msg': None
            }
        )
        if not created:
            first_msg = chat_session.chatmessage_set.first()
            if first_msg:
                time_inactive = timezone.now() - first_msg.user_response_timestamp
                if time_inactive.total_seconds() / 60 > ChatSettings.SESSION_TIMEOUT:
                    chat_session.status = 'aborted'
                    chat_session.save(update_fields=['status'])
                    assessments = chat_session.assessments.filter(status='pending')
                    for assessment in assessments:
                        assessment.status = 'aborted'
                        assessment.save(update_fields=['status'])
                    # reset patient phase
                    # conversation.user.patient.phase = PhaseMap.first()
                    # conversation.user.patient.save(update_fields=['phase'])
                    ic(PhaseMap.get(PhaseMap.first()).base_node_id)
                    chat_session, created = ChatSession.objects.get_or_create(
                        conversation=conversation, 
                        status='open',
                        defaults={
                            'init': True,
                            'phase': PhaseMap.first(),
                            'node_id': PhaseMap.get(PhaseMap.first()).base_node_id,
                            'retries': 0,
                            'last_msg': None
                        }
                    )
        return chat_session, created
