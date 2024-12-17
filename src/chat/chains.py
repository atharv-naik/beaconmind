from typing import Union
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_community.chat_models.ollama import ChatOllama
from langchain_openai.chat_models import ChatOpenAI
from langchain_core.language_models.chat_models import BaseChatModel
from .prompts import PromptStore
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field


class BaseModel:

    def __init__(self, model, **kwargs):
        self.model = model
        self.kwargs = kwargs

    def get_model(self):
        return self.model(**self.kwargs)


class Models:

    @staticmethod
    def get_model(model_name, **kwargs) -> BaseChatModel:
        model_map = {
            # local models
            "orca-mini": lambda: ChatOllama(model="orca-mini", **kwargs),
            "llama3": lambda: ChatOllama(model="llama3", **kwargs),

            # openai models
            "gpt-3.5-turbo": lambda: ChatOpenAI(model="gpt-3.5-turbo", **kwargs),
            "gpt-4o-mini": lambda: ChatOpenAI(model="gpt-4o-mini", **kwargs),
            "gpt-4-turbo": lambda: ChatOpenAI(model="gpt-4-turbo", **kwargs),
            "gpt-4o-2024-08-06": lambda: ChatOpenAI(model="gpt-4o-2024-08-06", **kwargs),
            "gpt-4o": lambda: ChatOpenAI(model="gpt-4o", **kwargs),

            # Add more models as needed
        }
        return model_map.get(model_name, lambda: None)()


class BasePrompt:

    def __init__(
        self,
        system_init_message,
        human_message="{input}",
        system_post_message=None
    ):
        self.system_init_message = system_init_message
        self.human_message = human_message
        self.system_post_message = system_post_message

    def create_prompt(self):
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", self.system_init_message),
                MessagesPlaceholder(variable_name="history", optional=True),
                ("human", self.human_message),
            ]
        )
        if self.system_post_message:
            prompt.append(("system", self.system_post_message))
        return prompt


class Prompts:

    @staticmethod
    def get_prompt(prompt_type, **kwargs):
        prompts_map = {
            "test": lambda: BasePrompt(
                system_init_message="You are a helpful virtual assistant.",
                **kwargs
            ),
            "default": lambda: BasePrompt(
                system_init_message=(
                    """
                    You are an empathetic and understanding virtual therapist. You subtly guide conversations and infer key emotional, social, and behavioral patterns from the user's responses without making them feel like they are being assessed.
                    
                    Based on the below conversation, subtly probe the user about:
                    - Social interactions over the past week.
                    - How they've been feeling emotionally.
                    - How they've been sleeping lately.
                    - Their recent stress levels.
                    
                    Respond empathetically and naturally.

                    Conversation:
                    """
                ),
                **kwargs
            ),
            "phq9.evaluation": lambda: BasePrompt(
                system_init_message=PromptStore.PHQ9_INIT,
                system_post_message=PromptStore.EVALUATION,
                **kwargs
            ),
            "phq9.response": lambda: BasePrompt(
                system_init_message=PromptStore.PHQ9_INIT,
                system_post_message=PromptStore.RESPONSE,
                **kwargs
            ),
            "phq9.eval": lambda: BasePrompt(
                system_init_message=PromptStore.PHQ9_INIT,
                system_post_message=PromptStore.EVAL,
                **kwargs
            ),
            "phq9.decision": lambda: BasePrompt(
                system_init_message=PromptStore.PHQ9_INIT,
                system_post_message=PromptStore.DECISION,
                **kwargs
            ),
        }
        return prompts_map.get(prompt_type, lambda: None)().create_prompt()


class OutputParsers:

    class ConversationalResponse(BaseModel):
        """Respond in a conversational manner. Be kind and helpful."""

        response: str = Field(
            description="A conversational response to the user's query")

    class ResponseSchema(BaseModel):
        response_for_user: str = Field(
            description="The response message that should be sent to the patient. Try a follow-up phq-9 question or a supportive message.")
        phq9_question: str = Field(
            description="The original PHQ-9 question being evaluated. -1 if the response is not relevant to any question.")
        score: int = Field(
            description="The score on a scale of 0-3 based on the patient's response. Score -1 if the response is not relevant to any question.")

    class Response(BaseModel):
        output: Union["OutputParsers.ResponseSchema",
                      "OutputParsers.ConversationalResponse"]

    class PHQ9Assessment(BaseModel):
        phq9_question: str = Field(...,
                                   description="The original PHQ-9 question being evaluated.")
        score: int = Field(..., ge=0, le=3,
                           description="The score on a scale of 0-3 based on the patient's response.")

    class AssistantResponse(BaseModel):
        response_for_user: str = Field(...,
                                       description="The assistant's response to the patient.")
        assessment: 'OutputParsers.PHQ9Assessment' = Field(
            ..., description="The PHQ-9 assessment based on the patient's response.")

    @staticmethod
    def get_output_parser(output_parser, **kwargs):
        output_parser_map = {
            "default": lambda: JsonOutputParser(**kwargs),
            "response": lambda: JsonOutputParser(pydantic_object=OutputParsers.Response, **kwargs),
            "response_schema": lambda: JsonOutputParser(pydantic_object=OutputParsers.ResponseSchema, **kwargs),
            "assistant_response": lambda: JsonOutputParser(pydantic_object=OutputParsers.AssistantResponse, **kwargs),
        }
        return output_parser_map.get(output_parser, lambda: None)()


class ChainBuilder:
    """
    Builder class to create a chain of models, prompts, and output parsers

    Example usage:
    ```
    chain = (
        ChainBuilder()
        .with_model("gpt-4o")
        .with_structured_output(OutputParsers.Response, include_raw=True)
        .with_prompt("default")
        .with_output_parser(my_custom_output_parser)
        .add_step(my_custom_step)
        .build()
    )
    ```
    """

    def __init__(self):
        self.model = None
        self.prompt = None
        self.output_parser = None
        self.extra_steps = []

    def with_model(self, model_name, **kwargs):
        self.model = Models.get_model(model_name, **kwargs)
        return self

    def with_structured_output(self, schema, include_raw=False, **kwargs):
        self.model = self.model.with_structured_output(
            schema=schema, include_raw=include_raw, **kwargs)
        return self

    def with_prompt(self, prompt_type, **kwargs):
        self.prompt = Prompts.get_prompt(prompt_type, **kwargs)
        return self

    def with_output_parser(self, output_parser):
        self.output_parser = output_parser
        return self

    def add_step(self, step):
        self.extra_steps.append(step)
        return self

    def build(self):
        if not self.model or not self.prompt:
            raise ValueError("Model and prompt are required to build a chain.")
        chain = self.prompt | self.model
        if self.output_parser:
            chain |= self.output_parser
        for step in self.extra_steps:
            chain = chain | step
        return chain


class ChainStore:
    """
    Predefined chains for convenience
    """

    # test_chain = ChainBuilder().with_model("orca-mini").with_prompt("test").build()
    # default_chain = ChainBuilder().with_model(
    #     "gpt-4o-mini").with_prompt("default").build()
    phq9_eval_chain = ChainBuilder()\
        .with_model("gpt-4o")\
        .with_prompt("phq9.eval")\
        .build()
    phq9_decision_chain = ChainBuilder()\
        .with_model("gpt-4o")\
        .with_prompt("phq9.response")\
        .build()


# test_chain = ChainStore.test_chain
# default_chain = ChainStore.default_chain
