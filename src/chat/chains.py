from langchain_community.chat_models.ollama import ChatOllama
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai.chat_models import ChatOpenAI

from .prompts import PromptStore


class Models:

    @staticmethod
    def get(model_name, **kwargs) -> BaseChatModel:
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

    def create_prompt(self) -> ChatPromptTemplate:
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
    def get(prompt_type, **kwargs) -> ChatPromptTemplate:
        prompts_map = {
            "test": lambda: BasePrompt(
                system_init_message="You are a helpful virtual assistant.",
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


class ChainBuilder:
    """
    Builder class to create a chain of models, prompts, and output parsers

    Example usage:
    ```
    chain = (
        ChainBuilder()
        .with_model("gpt-4o")
        .with_prompt("default")
        .add_step(my_custom_step)
        .build()
    )
    ```
    """

    def __init__(self):
        self.model = None
        self.prompt = None
        self.extra_steps = []

    def with_model(self, model_name, **kwargs):
        self.model = Models.get(model_name, **kwargs)
        return self

    def with_prompt(self, prompt_type, **kwargs):
        self.prompt = Prompts.get(prompt_type, **kwargs)
        return self

    def add_step(self, step):
        self.extra_steps.append(step)
        return self

    def build(self):
        if not self.model or not self.prompt:
            raise ValueError("Model and prompt are required to build a chain.")
        chain = self.prompt | self.model
        for step in self.extra_steps:
            chain = chain | step
        return chain


class ChainStore:
    """
    Predefined chains for convenience
    """

    phq9_eval_chain = (
        ChainBuilder()
        .with_model("gpt-4o")
        .with_prompt("phq9.eval")
        .build()
    )
    phq9_decision_chain = (
        ChainBuilder()
        .with_model("gpt-4o")
        .with_prompt("phq9.decision")
        .build()
    )
    
    @staticmethod
    def get(phase, mode):
        if not hasattr(ChainStore, f"{phase}_{mode}_chain"):
            raise ValueError(f"Chain not found: {phase}_{mode}_chain")
        return getattr(ChainStore, f"{phase}_{mode}_chain")
