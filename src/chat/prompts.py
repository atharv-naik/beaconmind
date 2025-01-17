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

    GAD7_INIT = textwrap.dedent(
        """
        Please play a role of an empathetic and kind psychiatrist. Your role is to assess the patient's mental health over time based on their responses to the GAD-7 questionnaire.

        GAD-7 Questions (Henceforth referred to as the `assessment questionaire`):
        1. Feeling nervous, anxious, or on edge?
        2. Not being able to stop or control worrying?
        3. Worrying too much about different things?
        4. Trouble relaxing?
        5. Being so restless that it is hard to sit still?
        6. Becoming easily annoyed or irritable?
        7. Feeling afraid as if something awful might happen?

        Each question has a scale from 0 to 3 (`assessment questionaire` scoring guide) -> 0: Not at all, 1: Several days, 2: More than half the days, 3: Nearly every day.

        The following is the conversation between you and the patient till now:\n
        """
    )

    EVAL = textwrap.dedent(
        """
        Use the following pseudo-code as a reference to understand the interpretation logic. Follow these steps to generate the interpretation result as JSON object.
        
        VAR patient_metrics = {patient_metrics}  # Dictionary containing the patient's evaluation scores
        DEFINE FUNCTION evaluate_response(latest_response, previous_response, conversation_context, patient_metrics):
            # Step 1: Check if the conversation is "BEGIN"
            IF is_first_message(latest_response) OR is_new_conversation(latest_response, conversation_context) OR is_new_phase(latest_response, conversation_context):
                RETURN {{
                    "chat_status": "BEGIN",
                    "evaluation": null
                }}

            # Step 2: Check for "AMBIGUOUS" state
            IF is_ambiguous(latest_response):
                RETURN {{
                    "chat_status": "AMBIGUOUS",
                    "evaluation": null
                }}

            # Step 3: Check if the conversation has "DRIFT"
            IF has_drifted(latest_response, previous_response, conversation_context):
                RETURN {{
                    "chat_status": "DRIFT",
                    "evaluation": null
                }}

            # Step 4: Evaluate the patient's response against the last question asked
            VAR decision_result = {decision_result}  # Decision context containing the last question asked

            score = evaluate_against_last_decision(latest_response, decision_result)

            IF score IS NOT NULL:
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
        
        FUNCTION is_new_phase(response, conversation_context):
            RETURN prev_phase_concluded() AND new_phase_started()

        FUNCTION is_ambiguous(response):
            RETURN response.content IS NULL OR response IS unclear ("hmm...", "ok", etc.)

        FUNCTION has_drifted(response, previous_response, conversation_context):
            // Simple 'yes' or 'no' responses are NOT considered DRIFT; they are AMBIGUOUS
            RETURN response IS NOT related_to(previous_response.question) AND NOT hardship_related(response)

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
        The latest patient response was interpreted against your last message (if any). 

        Description of `chat_status` values:
        BEGIN: The conversation has just initiated (no prior evaluation).
        DRIFT: The patient's response has drifted from the conversation context or question asked.
        AMBIGUOUS: The patient's response was unclear or not evaluable.
        NORMAL: The patient's response was evaluated, and the next question can now be asked.
        CONCLUDE: The assessment is complete (all questions in the patient metrics have been evaluated).

        chat_status={evaluation}

        Below are a list of unevaluated questions's `q_ids` till now (possibly empty if all evaluated):
        u_metrics={u_metrics}

        The previous decision result which contains the last question asked to the patient in json format is:
        prev_decision_result={prev_decision_result}

        Task:
        - Select a random question (referred to as `q_i`) from the `u_metrics`. `q_i` *MUST* be picked from the `u_metrics` if it is not empty; otherwise, there are no more questions to ask.
        - Prepare a response for the patient based on the `chat_status` as follows:

        Chat Status Handling:
        1. **BEGIN**:
            - Initiate the conversation with a friendly greeting or acknowledgment or introduction. And then say something like "lets start the assessment" or similar.
            - Craft a response that naturally introduces `q_i` into the conversation.
            - Avoid directly asking `q_i`; integrate it into the context.

        2. **DRIFT**:
            - Gently steer the conversation back to the previously asked question (`q_prev` in `prev_decision_result`).
            - Weave `q_prev` into the conversation naturally, without directly asking.

        3. **AMBIGUOUS**:
            - Request clarification on the patient's last response in a friendly and natural way.
            - Avoid moving to a new question until the response is clarified (focus remains on `q_prev`).

        4. **NORMAL**:
            - Craft a response that introduces `q_i` naturally based on `chat_status` and `u_metrics`. [NOTE THAT `q_i` MUST BE FROM `u_metrics` AND NOT PREVIOUSLY EVALUATED.]
            - Avoid directly asking `q_i`.

        5. **CONCLUDE**:
            - Acknowledge the completion of the assessment empathetically.
            - Provide a closing response to the patient.
            - Avoid asking any new questions.

        Response Format:
        {{ 
            "response_to_user"(str): "Your response to the patient here.",  
            "question_id"(int): "The ID of the question being asked (i.e., `q_i`).",  
            "question"(str): "The original `assessment questionnaire` question being asked (i.e., `q_i`)."  
        }}
        """
    ) + Meta.IMPORTANT

    SCORE = textwrap.dedent(
        """
        The above are some chat conversations between a bot designed to conduct a {assessment_name} assessment and a patient. Based on the conversation evaluate and score the patient for all the {assessment_name} questions. Output as a single JSON object. To each question's evaluation add a remark or a short justification (key `remark`) based on the patient's response. Also add a key `snippet` that holds the snippet of message that was used for justifying the score. Another key (optional) `keywords` to be added to contain any noteworthy/important points from any message (if any). This will be a list of short keywords (strings).
        The JSON object should have the following structure:
        {{
            "q_id": {{
                "score": num,
                "remark": "short justification",
                "snippet": "snippet from the msg",
                "keywords": ["keyword1", "keyword2", ...],
            }},
            ...
        }}
        ex. json.:
        {{
            "1": {{
                "score": 2,
                "remark": "some remark...",
                "snippet": "msg snippet supporting remark...",
                "keywords": ["keyword1", "keyword2", ...],
            }},
            ...
        }}
        Key `score` holds integer values. `remark` and `snippet` are strings. `keywords` is List[str] type. `q_id` must be chosen appropriately from the {assessment_name} questions described earlier. Make your remarks discriptive but concise. And keep snippets short and relevant.
        """
    ) + Meta.IMPORTANT

    CONCLUDE = textwrap.dedent(
        """
        The assessment is now complete. The patient has been evaluated for all the {prev_assessment_name} questions. The next phase is {next_assessment_name}. Prepare a closing message for the patient. Based on the previous assessment, write a closing message that is empathetic and supportive. The closing message should acknowledge conclusion of current assessment and prepare the patient for the next phase. The next phase of {next_assessment_name} can be introduced and begin whenever the patient is ready. 
        Output as a single JSON object with the following structure:
        {{
            "response_to_user"(str): "Your closing message here."
        }}
        """
    ) + Meta.IMPORTANT

    EVAL2 = textwrap.dedent(
        """
Given the discussion categorize the latest patient response against the last paraphrased question asked (original: {decision_result}) into chat statuses (name it chat_status) as described below:

        BEGIN: The conversation has just initiated (no prior evaluation).
        DRIFT: The patient's response has drifted from the conversation context or question asked.
        AMBIGUOUS: The patient's response was unclear or not evaluable.
        NORMAL: The patient's response was evaluated, and the next question can now be asked.
        CONCLUDE: The assessment is complete (all questions in the patient metrics have been evaluated).

patient_metrics: {patient_metrics} # Dictionary containing the patient's evaluation scores

You may include optional key (name it keywords [comma seperated string] should be short) that would hold any noteworthy deductions from the discussion so far if any else null.

a key for evaluation (name it evaluation [dict: default null]): in that holds the score key (described below), the original question text key (name it question[str]) and the quistion id key (name it question_id[int]). both question and question_id is given above in the original question dict above.
score key (name it score [int: default -1]) should hold a score for the latest patient response against the asked question. if not scorable for any reason such as drift or ambiguous etc. default it. 

output a single json object.
example output: {
  "chat_status": "NORMAL",
  "keywords": "interest, football, watching",
  "evaluation": {
    "score": 0,
    "question": "Little interest or pleasure in doing things?",
    "question_id": 1
  }
}
        """
    ) + Meta.IMPORTANT + Meta.CHAT_STATUS_INFO
