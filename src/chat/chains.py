from typing import Union
from langchain_community.chat_models.ollama import ChatOllama
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder, PromptTemplate
from langchain_openai.chat_models import ChatOpenAI

from .prompts.old import PromptStore
from . import prompts


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
        if model_name not in model_map:
            raise ValueError(f"Model '{model_name}' is not recognized. Available models: {list(model_map.keys())}")

        return model_map[model_name]()


class BasePrompt:

    def __init__(
        self,
        template=None,
        system_init_message=None,
        human_message="{input}",
        system_post_message=None,
        include_history=True,
        include_human_input=True,
        **kwargs
    ):
        self.template = template
        self.system_init_message = system_init_message
        self.human_message = human_message
        self.system_post_message = system_post_message
        self.include_history = include_history
        self.include_human_input = include_human_input
        self.kwargs = kwargs

    def create_prompt(self, **kwargs) -> Union[ChatPromptTemplate, PromptTemplate]:
        self.kwargs.update(kwargs)
        if self.template:
            return PromptTemplate.from_template(self.template, **self.kwargs)

        messages = []

        if self.system_init_message:
            messages.append(("system", self.system_init_message))
        if self.include_history:
            messages.append(MessagesPlaceholder(variable_name="history", optional=True))
        if self.include_human_input:
            messages.append(("human", self.human_message))
        if self.system_post_message:
            messages.append(("system", self.system_post_message))

        return ChatPromptTemplate.from_messages(messages, **self.kwargs)


class Prompts:

    @staticmethod
    def get(prompt_type, **kwargs) -> ChatPromptTemplate:
        prompts_map = {
            "test": lambda: BasePrompt(
                system_init_message="You are a helpful virtual assistant."
            ),
            "phq9.eval": lambda: BasePrompt(
                system_init_message=PromptStore.PHQ9_INIT,
                system_post_message=PromptStore.EVAL
            ),
            "phq9.decision": lambda: BasePrompt(
                system_init_message=PromptStore.PHQ9_INIT,
                system_post_message=PromptStore.DECISION
            ),
            "phq9.score": lambda: BasePrompt(
                system_init_message=PromptStore.PHQ9_INIT,
                system_post_message=PromptStore.SCORE,
                include_human_input=False
            ),
            "gad7.eval": lambda: BasePrompt(
                system_init_message=PromptStore.GAD7_INIT,
                system_post_message=PromptStore.EVAL
            ),
            "gad7.decision": lambda: BasePrompt(
                system_init_message=PromptStore.GAD7_INIT,
                system_post_message=PromptStore.DECISION
            ),
            "gad7.score": lambda: BasePrompt(
                system_init_message=PromptStore.GAD7_INIT,
                system_post_message=PromptStore.SCORE,
                include_human_input=False
            ),
            "monitoring.eval": lambda: BasePrompt(
                system_init_message=PromptStore.MONITORING_INIT,
                system_post_message=PromptStore.EVAL
            ),
            "monitoring.decision": lambda: BasePrompt(
                system_init_message=PromptStore.MONITORING_INIT,
                system_post_message=PromptStore.DECISION
            ),
            "monitoring.score": lambda: BasePrompt(
                system_init_message=PromptStore.MONITORING_INIT,
                system_post_message=PromptStore.SCORE,
                include_human_input=False
            ),
            "conclude": lambda: BasePrompt(                 # phase agnostic chain
                system_post_message=PromptStore.CONCLUDE
            ),
            

            # New prompts
            "dec.init": lambda: BasePrompt(
                template=prompts.dec.init
            ),
            "dec.normal": lambda: BasePrompt(
                template=prompts.dec.normal
            ),
            "dec.ambiguous": lambda: BasePrompt(
                template=prompts.dec.ambiguous
            ),
            "dec.drift": lambda: BasePrompt(
                template=prompts.dec.drift
            ),
            "dec.clarify": lambda: BasePrompt(
                template=prompts.dec.clarify
            ),
            "dec.skipped": lambda: BasePrompt(
                template=prompts.dec.skipped
            ),
            "dec.conclude": lambda: BasePrompt(
                template=prompts.dec.conclude
            ),
            "eval": lambda: BasePrompt(
                template=prompts.eval
            ),
            "score": lambda: BasePrompt(
                template=prompts.score
            ),
        }
        return prompts_map.get(prompt_type, lambda: None)().create_prompt(**kwargs)


class ChainBuilder:
    """
    Builder class to create a chain of models, prompts, and output parsers

    Example usage:
    ```
    chain = (
        ChainBuilder()
        .with_model("gpt-4o")
        .with_prompt("default")
        .add_step(custom_step)
        .build()
    )
    chain.invoke(data)
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
    phq9_score_chain = (
        ChainBuilder()
        .with_model("gpt-4o")
        .with_prompt("phq9.score")
        .build()
    )
    gad7_eval_chain = (
        ChainBuilder()
        .with_model("gpt-4o")
        .with_prompt("gad7.eval")
        .build()
    )
    gad7_decision_chain = (
        ChainBuilder()
        .with_model("gpt-4o")
        .with_prompt("gad7.decision")
        .build()
    )
    gad7_score_chain = (
        ChainBuilder()
        .with_model("gpt-4o")
        .with_prompt("gad7.score")
        .build()
    )
    monitoring_eval_chain = (
        ChainBuilder()
        .with_model("gpt-4o")
        .with_prompt("monitoring.eval")
        .build()
    )
    monitoring_decision_chain = (
        ChainBuilder()
        .with_model("gpt-4o")
        .with_prompt("monitoring.decision")
        .build()
    )
    monitoring_score_chain = (
        ChainBuilder()
        .with_model("gpt-4o")
        .with_prompt("monitoring.score")
        .build()
    )
    conclude_chain = (
        ChainBuilder()
        .with_model("gpt-4o")
        .with_prompt("conclude")
        .build()
    )


    # New chains
    dec_init_chain = (
        ChainBuilder()
        .with_model("gpt-4o")
        .with_prompt("dec.init")
        .build()
    )
    dec_normal_chain = (
        ChainBuilder()
        .with_model("gpt-4o")
        .with_prompt("dec.normal")
        .build()
    )
    dec_ambiguous_chain = (
        ChainBuilder()
        .with_model("gpt-4o")
        .with_prompt("dec.ambiguous")
        .build()
    )
    dec_drift_chain = (
        ChainBuilder()
        .with_model("gpt-4o")
        .with_prompt("dec.drift")
        .build()
    )
    dec_clarify_chain = (
        ChainBuilder()
        .with_model("gpt-4o")
        .with_prompt("dec.clarify")
        .build()
    )
    dec_skipped_chain = (
        ChainBuilder()
        .with_model("gpt-4o")
        .with_prompt("dec.skipped")
        .build()
    )
    dec_conclude_chain = (
        ChainBuilder()
        .with_model("gpt-4o")
        .with_prompt("dec.conclude")
        .build()
    )
    eval_chain = (
        ChainBuilder()
        .with_model("gpt-4o")
        .with_prompt("eval")
        .build()
    )
    score_chain = (
        ChainBuilder()
        .with_model("gpt-4o")
        .with_prompt("score")
        .build()
    )
    
    @staticmethod
    def get(mode, phase=None):
        """
        Retrieve a predefined chain from ChainStore.

        Raises ValueError if chain is not found.
        """
        if phase:
            chain_name = f"{phase}_{mode}_chain"
        else:
            chain_name = f"{mode}_chain"

        if not hasattr(ChainStore, chain_name):
            valid_chains = [
                attr for attr in dir(ChainStore)
                if attr.endswith("_chain") and not attr.startswith("__")
            ]
            raise ValueError(
                f"Chain not found: {chain_name}. "
                f"Available chains are: {', '.join(valid_chains)}"
            )
        
        return getattr(ChainStore, chain_name)
