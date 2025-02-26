# prompts/score.py

"""This module contains the scoring prompts for the chatbot."""

from textwrap import dedent


base = dedent(
    """
    You are a helpful virtual assistant for monitoring and conducting mental health related assessments. Understand the conversation and assign scores to the user's responses. The conversation is given in the prompt. This task needs some thinking and understanding of the conversation and the user's thought process.
    """
)

output_instructions = dedent(
    """
    [IMPORTANT]: Your output must *always* be a valid JSON object and do not include the ```json or ``` at the beginning or end of the response. Only begin your response with the first curly brace `{{` and end with the last curly brace `}}`.
    """
)

score = base + dedent(
    """
    Given are some chat conversations between a patient and a mental health virtual assistant. The assistant is conducting an assessment for {phase} phase of the assessment. The patient has responded to the questions asked by the assistant.
    
    Based on the conversation evaluate and score the patient for all the {phase} questions.Output as a single JSON object of the form: {{ "response": "<response>" }}.

    To each question's evaluation add a remark or a short justification (key `remark`) based on the patient's response. 
    Also add a key `snippet` that holds the snippet of message that was used for justifying the score. 
    Another key `keywords` to be added to contain any noteworthy/important points from any message (if any). This will be a list of short keywords (strings).
    
    The JSON object should have the following structure:
    {{
        "response": {{
                "qid": {{
                    "score": num,
                    "remark": "short justification",
                    "snippet": "snippet from the msg",
                    "keywords": ["keyword1", "keyword2", ...],
                }},
                ...
            }}
    }}
    Key `score` holds integer values. `remark` and `snippet` are strings. `keywords` is List[str] type. `qid` must be chosen appropriately from the {phase} questions json described below. Make your remarks informative but concise. And keep snippets short and relevant.

    The {phase} questions are given in JSON format below. `qid`, `text`, `labels`, `score_range` are the keys in the JSON object.
    questions_json={questions_json}

    Some questions in the chat may have been skipped if the patient's response was not evaluable. In such cases, you can assign the minimum valid score for that question as per the json (score_range[0]).

    Refer the conversation below and provide the requested json output.
    {conversation_json}
    """
) + output_instructions
