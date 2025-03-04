import json

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from assessments import definitions
from assessments.definitions import PhaseMap, BaseAssessmentPhase
from assessments.models import Assessment, AssessmentRecord, AssessmentResult

from ..chains import ChainStore
from ..models import ChatMessage, ChatSession, Conversation
from .constants import ChatStates
from .conversation import ConversationManager, HistoryManager


class SessionPipeline:

    def __init__(self, conversation: Conversation, chat_session: ChatSession = None):
        self.conversation = conversation
        self.session = chat_session
        self.history_manager = HistoryManager(
            self.conversation, self.session)
        self.patient = conversation.user.patient


        self.curr_phase = PhaseMap.get(self.session.phase)
        self.curr_node = self.curr_phase.get(self.session.node_id)
        self.chat_status = ChatStates.NORMAL

    @transaction.atomic
    def trigger_pipeline(self, user_msg: str) -> str:
        user_msg_f = ConversationManager.format_msg(user_msg)
        user_msg_timestamp = timezone.now()

        meta = {}

        meta["eval"] = {"meta": {}}

        user_marker = {
            "phase": self.curr_phase.name,
            "init": self.session.init,
        }

        msg = ChatMessage.objects.create(
            user_response=user_msg.strip(),
            conversation=self.conversation,
            chat_session=self.session,
            user_response_timestamp=user_msg_timestamp,
            user_marker=user_marker,
            meta_data=meta
        )

        if self.session.init:

            response = self.run_dec_routine(
                msg, user_msg_f, ChatStates.INIT
            )

        else:
            
            msg = self.run_eval_routine(msg, user_msg_f)

            response = self.run_dec_routine(
                msg, user_msg_f, self.chat_status
            )

        return response


    def run_eval_routine(self, msg: ChatMessage, user_msg: str) -> str:
        """
        Method to run the evaluation routine
        """

        user_msg = user_msg.strip()

        # invoke eval chain
        eval_response = ChainStore.eval_chain.invoke(
            input={
                "message": user_msg,
                "phase": self.curr_phase.verbose_name,
                "question_original": self.curr_node.text,
                "question": self.session.last_msg,
                "conversation": self.history_manager.get_full_list_from_session(),
            }
        )

        eval_meta = eval_response.response_metadata
        meta = {
            "eval": {
                "meta": eval_meta,
            }
        }

        state = json.loads(eval_response.content)["response"]

        assert state in [
            "NORMAL_y", 
            "NORMAL_n", 
            "DRIFT", 
            "AMBIGUOUS", 
            "CLARIFY"
        ], f"Invalid state: {state} returned by eval chain"

        if state in ["NORMAL_y", "NORMAL_n"]: 
            
            self.chat_status = ChatStates.NORMAL
            tr = state[-1]

            # reset retries set by earlier states
            self.session.retries = 0
            self.session.save(update_fields=["retries"])

        else: 
            if state in ["DRIFT", "AMBIGUOUS"]:
                self.chat_status = getattr(ChatStates, state)

                tr = "o"

                # increment retries
                self.session.retries += 1
                self.session.save(update_fields=["retries"])

            else:
                self.chat_status = ChatStates.CLARIFY

                tr = "c"

                # reset retries set by earlier states
                self.session.retries = 0
                self.session.save(update_fields=["retries"])

        user_marker = {
            "phase": self.curr_phase.name,
            "init": False,
            "question": self.curr_node.text,
            "node_id": self.curr_node.node_id,
            "tr": tr,
        }

        # transition to next node if any
        next_node = self.curr_phase.next_q(node_id=self.session.node_id, tr=tr, r=self.session.retries)

        # IMPORTANT set chat_status to SKIPPED if retries exceed limit set for the node
        # else the dec chains would be out of sync with the current state
        if self.session.retries > self.curr_node.r:
            self.chat_status = ChatStates.SKIPPED
            
            # reset retries
            self.session.retries = 0
            self.session.save(update_fields=["retries"])

        if next_node == definitions.END:

            # SCORING HAPPENS HERE ///////////////////////////////////////
            if self.curr_phase.supports_scoring:
                self.run_score_routine(self.curr_phase)

            # check for next phase
            next_phase = PhaseMap.next(self.session.phase)

            # TODO: check if phase needs to be skipped for current session 
            # MonitoringPhase to be skipped in 1st session of patient; 
            # enable in subsequent sessions

            if next_phase == definitions.END:
                # enter CONCLUDE state
                self.chat_status = ChatStates.CONCLUDE
            else:
                assert self.chat_status in [ChatStates.NORMAL, ChatStates.SKIPPED], f"Invalid chat status: {self.chat_status} for phase transition tr={tr}"

                # update session phase
                self.session.phase = next_phase
                self.session.node_id = PhaseMap.get(next_phase).base_node_id
                self.session.retries = 0
                self.session.save(update_fields=["phase", "node_id", "retries"])

                self.curr_phase = PhaseMap.get(self.session.phase)
                self.curr_node = self.curr_phase.get(self.session.node_id)

        else:
            # update session node
            self.session.node_id = next_node.node_id
            self.session.save(update_fields=["node_id"])

            self.curr_node = self.curr_phase.get(self.session.node_id)

        # save message
        msg.user_marker.update(user_marker)
        msg.meta_data.update(meta)
        msg.save(update_fields=["user_marker", "meta_data"])

        return msg


    def run_dec_routine(self, msg: ChatMessage, user_msg: str, chat_state: str) -> str:
        """
        Method to run the decision routine at a given chat_state
        """

        # invoke dec.{state} chain
        dec_response = getattr(ChainStore, f"dec_{chat_state.lower()}_chain").invoke(
            input={
                "message": user_msg.strip(),
                "phase": self.curr_phase.verbose_name,
                "question": self.curr_node.text,
                "conversation": self.history_manager.get_full_list(),
            }
        )

        response = json.loads(dec_response.content).get("response", "")
        dec_meta = dec_response.response_metadata
        meta = {
            "dec": {
                "type": chat_state.lower(),
                "meta": dec_meta,
            }
        }
        ai_marker = {
            "phase": self.curr_phase.name,
            "question": self.curr_node.text,
            "node_id": self.curr_node.node_id,
            "chat_status": chat_state,
        }

        # save message
        msg.ai_response = response
        msg.ai_response_timestamp = timezone.now()
        msg.ai_marker = ai_marker
        msg.meta_data.update(meta)
        msg.save(
            update_fields=[
                "ai_response",
                "ai_response_timestamp",
                "ai_marker",
                "meta_data",
            ]
        )

        self.session.last_msg = response
        self.session.init = False
        self.session.save(update_fields=["init", "last_msg"])

        if chat_state == ChatStates.CONCLUDE:
            self.session.status = "closed"
            self.session.save(update_fields=["status"])

        return response
    
    def run_score_routine(self, phase: BaseAssessmentPhase) -> None:
        """
        Method to run the scoring routine
        """
        
        qs = self.history_manager.filter_by(
            Q(chat_session_id=self.session.id),
            Q(ai_marker__phase=phase.name) | Q(user_marker__phase=phase.name)
        )

        # invoke the score chain
        score_response = ChainStore.score_chain.invoke(
            input={
                "phase": phase.verbose_name,
                "questions_json": json.dumps(phase.get_questions_dict()),
                "conversation_json": json.dumps(self.history_manager.qs_to_dict(qs)),
            }
        )
        
        score_meta = score_response.response_metadata
        meta = {
            "score": {
                "meta": score_meta,
            }
        }
        data = json.loads(score_response.content)["response"]

        # save assessment records
        assessment = Assessment.objects.create(
            patient=self.patient,
            session=self.session,
            type=phase.name,
        )
        q_data = phase.get_questions_dict()
        for qid, record in data.items():
            AssessmentRecord.objects.create(
                assessment=assessment,
                question_id=qid,
                question_text=q_data[qid]["text"],
                score=record["score"],
                remark=record["remark"],
                snippet=record["snippet"],
                keywords=record["keywords"],
            )

        # save assessment result
        score = phase.total_score(data)
        severity = phase.severity(data)
        AssessmentResult.objects.create(
            assessment=assessment,
            score=score,
            severity=severity,
        )
        assessment.status = "completed"
        assessment.completed_at = timezone.now()
        assessment.save(update_fields=["status", "completed_at"])
        return


