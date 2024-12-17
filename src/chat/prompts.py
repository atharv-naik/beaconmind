import textwrap

class PromptStore:
    """
    Store for all the prompts used in the chatbot.
    """

    class Meta:
        CHAT_STATUS_INFO = textwrap.dedent(
            """
            Some clarifications on the definitions of the terms used in the JSON objects:
            1. `chat_status`(str): The current state of the conversation. Possible values are:
                - `BEGIN`: When does the conversation start? It starts when either of the following is true about the patient's latest response:
                    - It is the first and only message in the conversation so far.
                    - It indicates a new conversation:
                        - A different topic from previous conversations.
                        - A large gap in the timestamps [>1 day].
                        - Greetings, salutations, or similar messages.
                - `DRIFT`: When does the conversation drift? It drifts when any of the following is true about the patient's latest response:
                    - The response does not directly or indirectly relate/answer your last question.
                    - It does not relate to any of the `assessment questionnaire` questions.
                    [IMPORTANT] Discussing personal hardships or similar mental struggles related to the patient's health is NOT considered drifting.
                - `AMBIGUOUS`: When is the response ambiguous? It is ambiguous when the patient's latest response is unclear or incomplete, making it difficult to assign a score. For example, responses like "hmm..." or "not sure" are ambiguous.
                - `NORMAL`: When is the conversation status normal? The conversation is considered normal when the patient's response has been successfully evaluated against the last question asked, and the assessment can continue to the next question.
                - `CONCLUDE`: When does the assessment conclude? It concludes when all questions in the `assessment questionnaire` have been evaluated, and the patient metrics are complete.

            2. `evaluation`(dict|null): When does the evaluation happen? Evaluation happens when the `chat_status` is `NORMAL`. The patient's latest response is assessed based on the `assessment questionnaire` scoring guide and the last question asked. 
                [IMPORTANT] Note that the patient response may not directly answer the question you asked in a simple yes/no format; you should gauge the intensity and frequency of the patient's experiences based on their response and assign a score accordingly.
            """
        )

        IMPORTANT = textwrap.dedent(
            """
            [IMPORTANT]: Your output must *always* be a valid JSON object and do not include the ```json or ``` at the beginning or end of the response. Only begin your response with the first curly brace `{{` and end with the last curly brace `}}`.
            """
        )

    PHQ9_INIT = textwrap.dedent(
        """
        Please play a role of an empathetic and kind psychiatrist. Your role is to assess the patient's mental health over time based on their responses to the PHQ-9 questionnaire.

        PHQ-9 Questions (Henceforth referred to as the `assessment questionaire`):
        1. Little interest or pleasure in doing things?
        2. Feeling down, depressed, or hopeless?
        3. Trouble falling/staying asleep, or sleeping too much?
        4. Feeling tired or having little energy?
        5. Poor appetite or overeating?
        6. Feeling bad about yourself or that you are a failure or have let yourself or your family down?
        7. Trouble concentrating on things, such as reading the newspaper or watching TV?
        8. Moving or speaking so slowly that others notice, or the opposite - being so fidgety or restless that you have been moving around a lot more than usual?
        9. Thoughts of being better off dead or self-harm?

        Each question has a scale from 0 to 3 (`assessment questionaire` scoring guide) -> 0: Not at all, 1: Several days, 2: More than half the days, 3: Nearly every day.

        The following is the conversation between you and the patient till now:\n
        """
    )

    EVAL = textwrap.dedent(
        """
        Use the following pseudo-code as a reference to understand the interpretation logic. Follow these steps to generate the interpretation result as JSON object.
        
        DEFINE FUNCTION evaluate_response(latest_response, previous_response, conversation_context, patient_metrics):
            # Step 1: Check if the conversation is "BEGIN"
            IF is_first_message(latest_response) OR is_new_conversation(latest_response, conversation_context):
                RETURN {{
                    "chat_status": "BEGIN",
                    "evaluation": null
                }}

            # Step 2: Check if the conversation has "DRIFT"
            IF has_drifted(latest_response, previous_response, conversation_context):
                RETURN {{
                    "chat_status": "DRIFT",
                    "evaluation": null
                }}

            # Step 3: Check for "AMBIGUOUS" state
            IF is_ambiguous(latest_response):
                RETURN {{
                    "chat_status": "AMBIGUOUS",
                    "evaluation": null
                }}

            # Step 4: Evaluate the patient's response against the last question asked
            VAR decision_result = {decision_result}  # Decision context containing the last question asked

            score = evaluate_against_last_decision(latest_response, decision_result)

            IF score IS NOT NULL:
                # Step 5: Check if the assessment is complete ("CONCLUDE")
                IF unevaluated_questions.count() <= 1 AND patient_metrics.unevaluated_question.id == decision_result.question_id:
                            # CONCLUDE if all questions except current questions are evaluated (as the current question is going to be evaluated now)
                    RETURN {{
                        "chat_status": "CONCLUDE",
                        "evaluation": {{
                            "question": decision_result.question,
                            "id": decision_result.question_id,
                            "score": score
                        }}
                    }}

                # Default state: "NORMAL"
                RETURN {{
                    "chat_status": "NORMAL",
                    "evaluation": {{
                        "question": decision_result.question,
                        "id": decision_result.question_id,
                        "score": score
                    }}
                }}

            # Fallback for unclear cases
            RETURN {{
                "chat_status": "AMBIGUOUS",
                "evaluation": null
            }}

        # Supporting Helper Functions
        FUNCTION is_first_message(response):
            RETURN response IS ONLY message in conversation history

        FUNCTION is_new_conversation(response, conversation_context):
            RETURN large_time_gap(response.timestamp, conversation_context) [>1 day] OR new_topic_detected(response)

        FUNCTION has_drifted(response, previous_response, conversation_context):
            RETURN response IS NOT related_to(previous_response.question) AND NOT hardship_related(response)

        FUNCTION is_ambiguous(response):
            RETURN response.content IS NULL OR response IS unclear ("hmm...", "ok", etc.)

        FUNCTION evaluate_against_last_decision(response, decision_result):
            original_question = map_to_original_question(response, decision_result.context)
            IF original_question IS NOT NULL:
                score = calculate_score(response, original_question.scoring_guide)
                RETURN score
            RETURN NULL

        FUNCTION all_questions_completed(patient_metrics, current_question_id):
            IF unevaluated_questions.count() > 1:
                RETURN FALSE
            FOR question_id, score IN patient_metrics.items():
                IF score == -1:
                    RETURN !(question_id == current_question_id)
            RETURN TRUE

        FUNCTION map_to_original_question(response, context):
            # Map paraphrased question to original assessment questionnaire question
            RETURN matched_question OR NULL

        FUNCTION calculate_score(response, scoring_guide):
            RETURN score BASED ON response content and scoring guide
        """
    ) + Meta.CHAT_STATUS_INFO + Meta.IMPORTANT

    DECISION = textwrap.dedent(
        """
        The latest patient response was interpreted against your last message (if any). The interpretation result object schema is as follows:
        {{ 
            "chat_status"(str): "The current status of the conversation. Possible values are BEGIN, DRIFT, AMBIGUOUS, NORMAL, or CONCLUDE.",  
            "evaluation"(dict|null): {{  
                "question"(str): "The original `assessment questionnaire` question being evaluated.",  
                "id"(int): "The ID of the question being evaluated.",  
                "score"(int): "The score on a scale of 0-3 based on the patient's response."  
            }}
        }}\n
        Here, the `evaluation` key tells that you had asked the patient about the question `question` and the patient's response was evaluated to have a score of `score` based on the `assessment questionnaire` scoring guide. The `id` key tells the ID of the question that was evaluated. The `chat_status` key indicates the current conversation state:

        BEGIN: The conversation has just initiated (no prior evaluation).
        DRIFT: The patient's response has drifted from the conversation context or question asked.
        AMBIGUOUS: The patient's response was unclear or not evaluable.
        NORMAL: The patient's response was evaluated, and the next question can now be asked.
        CONCLUDE: The assessment is complete (all questions in the patient metrics have been evaluated).

        The following json contains the interpretation result object for the latest patient response:
        interpretation_result={evaluation}

        The patient metrics on the `assessment questionnaire` i.e. (question_id, score) mappings in json form has a schema as follows:
        {{
            "question_id"(int): "score"(int, 0-3, -1 if not evaluated),  
            ...  
        }} 
        The following is the updated patient metrics after adding the latest evaluation (above):
        patient_metrics={patient_metrics}

        The following is the previous decision result that holds the last question asked to the patient:
        prev_decision_result={prev_decision_result}

        Based on the above two jsons as context, your task is to pick any random question (henceforth referred to as `q_i` - the i-th question in the `assessment questionnaire`, i is the question_id) which is NOT evaluated yet (i.e., the score is -1 in `patient_metrics`). Do not pick sequentially; randomize the selection.

        Your task is to prepare a response for the patient by considering the following:

        - If the chat_status is BEGIN, prepare a response that seeks input to `q_i` from the patient but also considers the context of the conversation. Avoid directly asking `q_i`; instead, weave it into a natural conversation.
        - If the chat_status is DRIFT, prepare a response that gently steers the conversation back to the previously asked question in the `prev_decision_result` json (`q_prev`). Weave this into a natural conversation and avoid directly asking `q_prev`.
        - If the chat_status is AMBIGUOUS, request clarification on the patient's last response in a friendly way to keep the conversation natural. You should avoid jumping to a new question until the response is clarified. Here the question would remain the previously asked question in the `prev_decision_result` json (`q_prev`).
        - If the chat_status is NORMAL, prepare a response that seeks input to `q_i` from the patient based on the `interpretation_result` and `patient_metrics` jsons, but weave it naturally into the conversation without directly asking `q_i`.
        If the chat_status is CONCLUDE, acknowledge the completion of the assessment in a natural, empathetic way and provide a closing response.
        Your response should be in the following format:
        {{
            "response_to_user"(str): "Your response to the patient here.",  
            "question_id"(int): "The ID of the question being asked. (the i in `q_i`)",  
            "question"(str): "The original `assessment questionnaire` question being asked. (the `q_i`)",  
        }} 
        """
    ) + Meta.CHAT_STATUS_INFO + Meta.IMPORTANT
