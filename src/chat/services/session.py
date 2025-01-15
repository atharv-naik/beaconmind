import json

from django.db import transaction
from django.utils import timezone
from langchain_core.messages.ai import AIMessage
from langchain_core.runnables.history import RunnableWithMessageHistory

from assessments.definitions import PhaseMap
from assessments.models import Assessment, AssessmentRecord

from ..chains import ChainStore
from ..models import ChatMessage, ChatSession, Conversation
from .constants import ChatStates
from .conversation import ConversationManager, HistoryManager


class SessionPipeline:

    def __init__(self, conversation: Conversation, chat_session: ChatSession = None):
        self.conversation = conversation
        self.conversation_id = conversation.id
        self.chat_session = chat_session
        self.history_manager = HistoryManager(
            self.conversation, self.chat_session)
        self.patient = conversation.user.patient
        self.phase = PhaseMap.get(self.patient.phase)

    def trigger_pipeline(self, user_response: str) -> str:
        formated_user_response = ConversationManager.format_msg(user_response)
        prev_decision_result = self.history_manager.get_last_decision()

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
            assessment, _ = Assessment.objects.get_or_create(
                self.patient, self.phase.name, "pending")
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
            interpretation_result["chat_status"] = ChatStates.CONCLUDE
            # TODO:
            # 1. Add chain to re-evaluate assessment and assign final scores
            # 2. Compute and assign total final score and severity (AssessmentResult)
            # 3. Mark assessment as "completed"
            # 4. Update patient.phase to point to next phase (if any)
            # 5. Add a conclude chain; invoke with new phase info; return response

        # unevaluated metrics
        u_metrics = [k for k, v in metrics.items() if v == -1]

        # decision chain
        decision_response = self.run_chain(
            mode="decision",
            data={
                "input": formated_user_response,
                "u_metrics": str(u_metrics),
                "evaluation": json.dumps(interpretation_result),
                "prev_decision_result": prev_decision_result,

                # TODO: below changes might improve control & stability of chat
                # replace `evaluation` key with interpretation_result["chat_status"]
                # replace `u_metrics` with random.choice(u_metrics)
            }
        )
        decision_result = json.loads(decision_response.content)
        response_to_user = decision_result.get("response_to_user", "")

        with transaction.atomic():
            msg = self.save_user_message(
                user_response, marker=interpretation_result)
            self.save_ai_message(
                msg,
                decision_response,
                parse=True,
                marker=decision_result
            )
        return response_to_user

    def run_chain(self, mode, data: dict) -> AIMessage:
        assert "input" in data, "Input message is required"

        chain = RunnableWithMessageHistory(
            ChainStore.get(self.phase.short_name, mode),
            self.history_manager.get_full,
            input_messages_key="input",
            history_messages_key="history",
        )
        response: AIMessage = chain.invoke(
            data,
            config={"configurable": {"session_id": self.conversation_id}},
        )
        return response

    def get_patient_metrics(self) -> dict:
        assessment, _ = Assessment.objects.get_or_create(
            patient=self.patient, type=self.phase.name, status="pending")

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
