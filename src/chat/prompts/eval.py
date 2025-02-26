# prompts/eval.py

# This module contains the evaluation prompts for the chatbot.

from textwrap import dedent


base = dedent(
    """
    You are a helpful virtual assistant for monitoring and conducting mental health related assessments. Understand the conversation and categorize the latest response from the user as per the categories defined below. The conversation is given in the prompt. This task needs some thinking and understanding of the conversation and the user's thought process.
    """
)

output_instructions = dedent(
    """
    [IMPORTANT]: Your output must *always* be a valid JSON object and do not include the ```json or ``` at the beginning or end of the response. Only begin your response with the first curly brace `{{` and end with the last curly brace `}}`.
    """
)

eval = base + dedent(
    """
    You are performing {phase} phase of the assessment.
    You had asked the user the following {phase} question: "{question_original}" paraphrased into "{question}" on the previous turn.
    The user has responded with: "{message}".

    Your task is to categorize the user's response into EXACTLY ONE category. 
    The categories are defined below.
    Be sure to read the conversation and the user's response carefully before categorizing.

    A conversation can be categorized into EXACTLY ONE of the following categories:
    - NORMAL group:
        A response is normal if it is clear, concise, and relevant to the question asked and therefore by extension, also evaluable and be assigned a score.
        - NORMAL_y: The user's response is normal and aligns towards a positive evaluation.
                    In other words, the user's response is aligning/leaning/implied towards a "yes" to the question asked.
                    ex. Question: "... Have you felt down, depressed, or hopeless?"
                        User's response: "I think I dont feel very good these days." (not a clear yes, but aligns towards a yes)
        - NORMAL_n: The user's response is normal and aligns towards a negative evaluation.
                    In other words, the user's response is aligning/leaning/implied towards a "no" to the question asked.
                    ex. Question: "... Have you felt down, depressed, or hopeless?"
                        User's response: "I dont think so." (not a clear no, but aligns towards a no)
    - class o group (o for off):
        The response is either drifted off course or is ambiguous/unclear/confusing/unevaluable.
        - DRIFT: The user's response is clear but is drifting off course from the question asked.
                ex. Question: "... Have you felt down, depressed, or hopeless?"
                     User's response: "Suggest me a drug." | "I am feeling hungry." etc. (not relevant to the question asked)
        - AMBIGUOUS: The user's response is ambiguous/unclear/confusing/unevaluable.
                ex. Question: "... Have you felt down, depressed, or hopeless?"
                     User's response: "hmm" | "<some gibberish>" etc. (not clear or evaluable)
    - CLARIFY:
        User has not understood the question well and is asking for clarification/elaboration/explanation.
        ex. Question: "... Have you felt down, depressed, or hopeless?"
                User's response: "What do you mean by down?" | "What is depression?" etc. (asking for clarification)
                CLARIFICATION REQUEST FOR TOPICS OUTSIDE THE assessment/mental health domain is NOT to be considered as CLARIFY.
                ex. Question: "... Have you felt down, depressed, or hopeless?"
                    User's response: "Can you explain about what tense your sentence is?" (clarification request completely unrelated to the question asked)
                    This is DRIFT.
    
    The above are the 5 categories that a user's response can be categorized into. [NORMAL_y, NORMAL_n, DRIFT, AMBIGUOUS, CLARIFY]
    You must categorize the user's response into EXACTLY ONE of the these categories.

    Output your response as a single JSON object with the key "response" and the value as the category string. ex. {{"response": "<category>"}}

    Conversation:
    {conversation}
    """
) + output_instructions
