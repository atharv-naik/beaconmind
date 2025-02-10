class ChatStates:
    """
    Enum for chat states
    """

    BEGIN = 'BEGIN'
    AMBIGUOUS = 'AMBIGUOUS'
    DRIFT = 'DRIFT'
    NORMAL = 'NORMAL'
    CONCLUDE = 'CONCLUDE'
    COMPLETE = 'COMPLETE'

    @staticmethod
    def is_BEGIN(object):
        metrics = object.get_assessment_progress()
        return len([v for v in metrics.values() if v != -1]) == 0

    @staticmethod
    def is_COMPLETE(object):
        metrics = object.get_assessment_progress()
        return len([v for v in metrics.values() if v != -1]) == object.curr_phase.N
