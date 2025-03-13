class ChatStates:
    """
    Enum for chat states
    """

    BEGIN = 'BEGIN'
    INIT = 'INIT'
    AMBIGUOUS = 'AMBIGUOUS'
    DRIFT = 'DRIFT'
    CLARIFY = 'CLARIFY'
    NORMAL = 'NORMAL'
    SKIPPED = 'SKIPPED'
    CONCLUDE = 'CONCLUDE'
    COMPLETE = 'COMPLETE'


class Actions:
    """
    Enum for chat actions
    """

    CONCLUDE = 'end_session'
    closed = 'end_session'

    def get_action_flag(chat_state):
        """
        Get action flag based on chat state
        """
        return getattr(Actions, chat_state, None)
    
