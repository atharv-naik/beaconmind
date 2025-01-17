import json
from typing import Dict, Union

from django.db import transaction
from django.utils import timezone
from langchain_core.messages.ai import AIMessage
from langchain_core.runnables.history import RunnableWithMessageHistory

from assessments.definitions import PhaseMap
from assessments.models import Assessment, AssessmentRecord, AssessmentResult

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

        assessment, _ = Assessment.objects.get_or_create(
            patient=self.patient, type=self.phase.name, status="pending")
        self.assessment = assessment
        self.BEGIN = False

    def trigger_pipeline(self, user_response: str) -> str:
        formated_user_response = ConversationManager.format_msg(user_response)
        prev_decision_result = self.history_manager.get_last_decision()

        # eval chain
        eval_response = self.run_chain(
            data={
                "input": formated_user_response,
                "patient_metrics": json.dumps(self.get_assessment_progress()),
                "decision_result": prev_decision_result,
            },
            mode="eval",
            phase=self.phase.short_name
        )
        interpretation_result = json.loads(eval_response.content)
        self.BEGIN = interpretation_result["chat_status"] == ChatStates.BEGIN
        # save temp record
        self.save_temp_record(interpretation_result)

        if ChatStates.is_CONCLUDE(self):
            interpretation_result["chat_status"] = ChatStates.CONCLUDE
            # TODO:
            # 1. Add chain to re-evaluate assessment and assign final scores
            score_data = self.run_chain(
                data={
                    "assessment_name": self.phase.verbose_name,
                    "history": self.history_manager.get_full_list(),
                },
                mode="score",
                phase=self.phase.short_name,
                parse=True
            )

            # overwrite AssessmentRecords with final scores
            self.write_final_records(score_data)

            # 2. Compute and assign total final score and severity (AssessmentResult)
            severity = self.phase.severity(score_data)
            total_score = self.phase.total_score(score_data)
            AssessmentResult.objects.create(
                assessment=self.assessment,
                score=total_score,
                severity=severity
            )

            # 3. Mark assessment as "completed"
            self.assessment.status = "completed"
            self.assessment.save(update_fields=["status"])

            # 4. Update patient.phase to point to next phase (if any)
            prev_phase = self.phase
            self.patient.phase = PhaseMap.next(self.patient.phase)
            self.patient.save(update_fields=["phase"])
            self.phase = PhaseMap.get(self.patient.phase)

            # 5. Add a conclude chain; invoke with new phase info; return response
            conclude_response = self.run_chain(
                data={
                    "input": formated_user_response,
                    "prev_assessment_name": prev_phase.verbose_name,
                    "next_assessment_name": self.phase.verbose_name,
                },
                mode="conclude",
                phase=None  # phase agnostic chain
            )
            conclude_result = json.loads(conclude_response.content)
            response_to_user = conclude_result.get("response_to_user", "")

            with transaction.atomic():
                msg = self.save_user_message(
                    user_response, marker=interpretation_result)
                self.save_ai_message(
                    msg,
                    conclude_response,
                    parse=True,
                    marker=conclude_result
                )
            return response_to_user

        # unevaluated metrics
        metrics = self.get_assessment_progress()
        u_metrics = [k for k, v in metrics.items() if v == -1]

        # decision chain
        decision_response = self.run_chain(
            data={
                "input": formated_user_response,
                "u_metrics": str(u_metrics),
                "evaluation": json.dumps(interpretation_result),
                "prev_decision_result": prev_decision_result,

                # TODO: below changes might improve control & stability of chat
                # replace `evaluation` key with interpretation_result["chat_status"]
                # replace `u_metrics` with random.choice(u_metrics)
            },
            mode="decision",
            phase=self.phase.short_name
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

    def run_chain(self, data: dict, mode, phase=None, parse=False) -> Union[AIMessage, Dict]:
        if mode in ["eval", "decision", "conclude"]:
            assert "input" in data, "Input key is required"

            chain = RunnableWithMessageHistory(
                ChainStore.get(mode=mode, phase=phase),
                self.history_manager.get_full,
                input_messages_key="input",
                history_messages_key="history",
            )
            response: AIMessage = chain.invoke(
                data,
                config={"configurable": {"session_id": self.conversation_id}},
            )
        elif mode == "score":
            chain = ChainStore.get(mode=mode, phase=phase)
            response: AIMessage = chain.invoke(input=data)
        if parse:
            response = json.loads(response.content)
        return response

    def get_assessment_progress(self) -> dict:
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

    def save_temp_record(self, data: dict):
        if e := data.get("evaluation"):
            AssessmentRecord.objects.update_or_create(
                assessment=self.assessment,
                question_id=e["id"],
                defaults={
                    "question_id": e["id"],
                    "question_text": self.phase.get(e["id"]),
                    "score": e["score"]
                }
            )

    def write_final_records(self, data: dict):
        records = AssessmentRecord.objects.filter(
            assessment=self.assessment).order_by('question_id')
        for record in records:
            data_dict = data[str(record.question_id)]
            record.dirty = record.score != data_dict["score"]
            record.score = data_dict["score"]
            record.remark = data_dict["remark"]
            record.snippet = data_dict["snippet"]
            record.keywords = data_dict.get("keywords", [])
            record.save(
                update_fields=[
                    "score",
                    "remark",
                    "snippet",
                    "keywords",
                    "dirty"
                ]
            )

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
