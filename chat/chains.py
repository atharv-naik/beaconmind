from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_community.chat_models.ollama import ChatOllama
from langchain_openai.chat_models import ChatOpenAI


class Models:

    # local models
    orca_mini = ChatOllama(model="orca-mini")
    llama2 = ChatOllama(model="llama2")
    llama3 = ChatOllama(model="llama3")

    # openai models
    # TODO: Add OpenAI models here

class Prompts:

    default_system_message = (
        """You're a psychiatrist. Diagnose the patient's mental health from each of their responses. Respond in a way a psychiatrist would. When writing large blocks of text, use bullet points to break up the text. Try to keep your responses short concise and to the point for the most part unless you feel it's necessary to write more."""

        """Try to keep your responses short concise and to the point for the most part unless you feel it's necessary to write more."""

        """Help the patient understand their mental health and provide them with the best advice you can. Remember, you're a professional psychiatrist, so act like one."""
    )

    @staticmethod
    def create_prompt(system_message: str = default_system_message):
        return ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    system_message,
                ),
                MessagesPlaceholder(variable_name="history"),
                ("human", "{input}"),
            ]
        )

    default_prompt = create_prompt()

class Chains:
    """
    This class provides pre-defined chains for the chatbot.
    """
    default_chain = Prompts.default_prompt | Models.orca_mini

    def create_custom_chain(self, model_name: str):
        # TODO: Implement this method
        pass


default_chain = Chains.default_chain
