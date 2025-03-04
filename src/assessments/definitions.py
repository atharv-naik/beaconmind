"""
Definitions for assessment phases and their details.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Iterable, List, Tuple, Union


END = "END"


class QuestionNode:
    def __init__(self, node_id: str, qid: Union[int, str], text: str, y: Union[int, str], n: Union[int, str], o: Union[int, str], r: int = 2):
        self.node_id = node_id
        self.qid = qid
        self.text = text
        self._y = y  # Yes response transition
        self._n = n  # No response transition
        self._o = o  # Other response transition (retry dependent)
        self._c = self.node_id  # Clarify response (loop back to self)
        self.r = r  # Retry threshold

    def y(self): return self._y
    def n(self): return self._n
    def o(self, retry_count: int): return self.node_id if retry_count <= self.r else self._o
    def c(self): return self._c

    def __str__(self):
        return self.text

    def __repr__(self):
        return f"<QuestionNode(node_id={self.node_id}, qid={self.qid}, text={self.text[:20]}...)>"


class BaseAssessmentPhase(ABC):
    """Abstract base class for assessment phase details."""

    @property
    @abstractmethod
    def name(self) -> str:
        """
        System name of the phase

        For system reference (e.g. in the database). The `Patient.phase` field points to this value. 
        Starts with `assessment.` prefix. ex. `assessment.phq9`
        """
        pass

    @property
    def short_name(self) -> str:
        """Short system name of the phase."""
        return self.name.split(".")[-1]

    @property
    @abstractmethod
    def verbose_name(self) -> str:
        """
        Verbose/display name of the phase

        For user reference (e.g. in the dashboard)
        """
        pass

    @property
    def description(self) -> str:
        """Short description of the assessment phase."""
        return ""

    @property
    @abstractmethod
    def questions(self) -> Dict[str, QuestionNode]:
        """QuestionsNode graph for the assessment phase."""
        pass

    @property
    @abstractmethod
    def N(self) -> int:
        """Number of questions in the assessment."""
        pass

    @property
    def supports_scoring(self) -> bool:
        """Indicates whether the assessment supports scoring."""
        return True

    @property
    @abstractmethod
    def low(self) -> int:
        """Minimum score for any assessment question."""
        pass

    @property
    @abstractmethod
    def high(self) -> int:
        """Maximum score for any assessment question."""
        pass

    @property
    def span(self) -> Tuple[int, int]:
        """Score range (low, high) for assessment questions."""
        return self.low, self.high

    @property
    def range(self) -> Iterable[int]:
        """Score range iterable for assessment questions."""
        return range(self.low, self.high + 1)

    @property
    @abstractmethod
    def labels(self) -> List[str]:
        """Labels for the assessment scores."""
        pass

    @property
    def cap(self) -> int:
        """Cap score `(N*high)` for the assessment."""
        return self.N * self.high

    @abstractmethod
    def severity(self, data: Dict[str, Dict[str, int]]) -> str:
        """Get severity based on assessment scores."""
        pass

    @abstractmethod
    def total_score(self, data: Dict[str, Dict[str, int]]) -> int:
        """Get the total score of the assessment."""
        pass

    def get(self, node_id: str) -> QuestionNode:
        """Get the question node for a given question ID."""
        try:
            return self.questions[str(node_id)]
        except KeyError:
            raise ValueError(
                f"QuestionNode(node_id={node_id}) not found in {self.name}")
    
    @property
    def base_node_id(self) -> str:
        """Get the base question node ID."""
        return "1"

    def next_q(self, node_id: str, tr: str, r: int = 1) -> Union[QuestionNode, str]:
        node = self.get(node_id)
        nxt = {
            'y': node.y(),
            'n': node.n(),
            'o': node.o(r),
            'c': node.c()
        }[tr]
        if nxt == END:
            return END
        return self.get(nxt)
    
    def get_questions_dict(self) -> Dict[str, Dict[str, Any]]:
        """Get the questions as a JSON serializable dictionary."""
        return {
            str(q.qid): {
                "qid": q.qid,
                "text": q.text,
                "labels": self.labels,
                "score_range": self.span,
            }
            for q in self.questions.values()
        }

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name

    def __eq__(self, other):
        """Checks equality based on the system name."""
        if isinstance(other, BaseAssessmentPhase):
            return self.name == other.name
        return False

class PHQ9Phase(BaseAssessmentPhase):

    @property
    def name(self) -> str:
        return "assessment.phq9"

    @property
    def verbose_name(self) -> str:
        return "PHQ9"

    @property
    def description(self) -> str:
        return "The PHQ-9 is a multipurpose instrument for screening, diagnosing, monitoring, and measuring the severity of depression."

    @property
    def N(self) -> int:
        return len(set(node.qid for node in self.questions.values()))

    @property
    def low(self) -> int:
        return 0

    @property
    def high(self) -> int:
        return 3

    @property
    def labels(self) -> List[str]:
        return ["Not at all", "Several days", "More than half the days", "Nearly every day"]

    @property
    def questions(self) -> Dict[str, QuestionNode]:
        return {
            "1": QuestionNode(
                node_id="1",
                qid=1,
                text="Little interest or pleasure in doing things",
                y=2, n=2, o=2
            ),
            "2": QuestionNode(
                node_id="2",
                qid=2,
                text="Feeling down, depressed, or hopeless",
                y=3, n=3, o=3
            ),
            "3": QuestionNode(
                node_id="3",
                qid=3,
                text="Trouble falling or staying asleep, or sleeping too much",
                y=4, n=4, o=4
            ),
            "4": QuestionNode(
                node_id="4",
                qid=4,
                text="Feeling tired or having little energy",
                y=5, n=5, o=5
            ),
            "5": QuestionNode(
                node_id="5",
                qid=5,
                text="Poor appetite or overeating",
                y=6, n=6, o=6
            ),
            "6": QuestionNode(
                node_id="6",
                qid=6,
                text="Feeling bad about yourself - or that you are a failure or have let yourself or your family down",
                y=7, n=7, o=7
            ),
            "7": QuestionNode(
                node_id="7",
                qid=7,
                text="Trouble concentrating on things, such as reading the newspaper or watching television",
                y=8, n=8, o=8
            ),
            "8": QuestionNode(
                node_id="8",
                qid=8,
                text="Moving or speaking so slowly that other people could have noticed. Or the opposite - being so fidgety or restless that you have been moving around a lot more than usual",
                y=9, n=9, o=9
            ),
            "9": QuestionNode(
                node_id="9",
                qid=9,
                text="Thoughts that you would be better off dead, or of hurting yourself",
                y=END, n=END, o=END
            ),
        }

    def severity(self, data: Union[Dict[str, Dict[str, int]], int]) -> str:
        """Get the severity of depression based on the PHQ-9 score."""
        if isinstance(data, int):
            score = data
        else:
            score = sum([data[str(qid)]["score"] for qid in data.keys()])
        match score:
            case n if n <= 4:
                return "Minimal depression"
            case n if n <= 9:
                return "Mild depression"
            case n if n <= 14:
                return "Moderate depression"
            case n if n <= 19:
                return "Moderately severe depression"
            case _:
                return "Severe depression"

    def total_score(self, data: Dict[str, Dict[str, int]]) -> int:
        """Get the total score of the PHQ-9 assessment."""
        return sum([data[str(qid)]["score"] for qid in data.keys()])


class GAD7Phase(BaseAssessmentPhase):

    @property
    def name(self) -> str:
        return "assessment.gad7"

    @property
    def verbose_name(self) -> str:
        return "GAD7"

    @property
    def description(self) -> str:
        return "The GAD-7 is a self-reported questionnaire for screening and severity measuring of generalized anxiety disorder."

    @property
    def N(self) -> int:
        return len(set(node.qid for node in self.questions.values()))

    @property
    def low(self) -> int:
        return 0

    @property
    def high(self) -> int:
        return 3

    @property
    def labels(self) -> List[str]:
        return ["Not at all", "Several days", "More than half the days", "Nearly every day"]

    @property
    def questions(self) -> Dict[str, QuestionNode]:
        return {
            "1": QuestionNode(
                node_id="1",
                qid=1,
                text="Feeling nervous, anxious or on edge?",
                y=2, n=END, o=END, r=2
            ),
            "2": QuestionNode(
                node_id="2",
                qid=2,
                text="Not being able to stop or control worrying?",
                y=3, n=3, o=3
            ),
            "3": QuestionNode(
                node_id="3",
                qid=3,
                text="Worrying too much about different things?",
                y=4, n=4, o=4
            ),
            "4": QuestionNode(
                node_id="4",
                qid=4,
                text="Trouble relaxing?",
                y=5, n=5, o=5
            ),
            "5": QuestionNode(
                node_id="5",
                qid=5,
                text="Being so restless that it is hard to sit still?",
                y=6, n=6, o=6
            ),
            "6": QuestionNode(
                node_id="6",
                qid=6,
                text="Becoming easily annoyed or irritable?",
                y=7, n=7, o=7
            ),
            "7": QuestionNode(
                node_id="7",
                qid=7,
                text="Feeling afraid as if something awful might happen?",
                y=END, n=END, o=END
            ),
        }

    def severity(self, data: Union[Dict[str, Dict[str, int]], int]) -> str:
        """Get the severity of anxiety based on the GAD-7 score."""
        if isinstance(data, int):
            score = data
        else:
            score = sum([data[str(qid)]["score"] for qid in data.keys()])
        match score:
            case n if n <= 4:
                return "Minimal anxiety"
            case n if n <= 9:
                return "Mild anxiety"
            case n if n <= 14:
                return "Moderate anxiety"
            case _:
                return "Severe anxiety"

    def total_score(self, data: Dict[str, Dict[str, int]]) -> int:
        """Get the total score of the GAD-7 assessment."""
        return sum([data[str(qid)]["score"] for qid in data.keys()])


class MonitoringPhase(BaseAssessmentPhase):

    @property
    def name(self) -> str:
        return "monitoring"

    @property
    def verbose_name(self) -> str:
        return "Monitoring"

    @property
    def N(self) -> int:
        return len(set(node.qid for node in self.questions.values()))
    
    @property
    def supports_scoring(self) -> bool:
        return True

    @property
    def low(self) -> int:
        return 0  # responses are not scored

    @property
    def high(self) -> int:
        return 0  # responses are not scored

    @property
    def labels(self) -> List[str]:
        return []

    @property
    def questions(self) -> Dict[str, QuestionNode]:
        return {
            "1": QuestionNode(
                node_id="1",
                qid=1,
                text="Have you noticed any improvement or worsening in your [specific symptoms, e.g., anxiety, depression, psychosis]?",
                y="2a", n="2a", o="2a"
            ),
            "2a": QuestionNode(
                node_id="2a",
                qid="2a",
                text="Have you experienced any new symptoms since your last visit?",
                y="2b", n=3, o=3
            ),
            "2b": QuestionNode(
                node_id="2b",
                qid="2b",
                text="What are the new symptoms?",
                y=3, n=3, o=3
            ),
            "3": QuestionNode(
                node_id="3",
                qid=3,
                text="Have you been taking your prescribed medications as directed?",
                y=4, n=4, o=4
            ),
            "4": QuestionNode(
                node_id="4",
                qid=4,
                text="Have you missed any doses? If yes, how often?",
                y="5a", n="5a", o="5a"
            ),
            "5a": QuestionNode(
                node_id="5a",
                qid="5a",
                text="Have you experienced any side effects from the medication?",
                y="5b", n=6, o=6
            ),
            "5b": QuestionNode(
                node_id="5b",
                qid="5b",
                text="What side effects have you experienced?",
                y=6, n=6, o=6,
                # type="descriptive"
            ),
            "6": QuestionNode(
                node_id="6",
                qid=6,
                text="Have you used any substances (e.g., alcohol, drugs) since your last visit?",
                y=END, n=END, o=END
            ),
        }

    def severity(self, data: Union[Dict[str, Dict[str, int]], int]) -> str:
        return "Not applicable"

    def total_score(self, data: Dict[str, Dict[str, int]]) -> int:
        return 0


class ASQPhase(BaseAssessmentPhase):
    """
    Implementation of the Ask Suicide-Screening Questions (ASQ) tool with branching logic
    that ensures all four initial questions (Q1-Q4) are asked before determining whether
    the final question (Q5) should be administered.

    ------------------------------------------------------------
    State Transition Diagram & Explanation:
    ------------------------------------------------------------
    The ASQ assessment comprises 5 questions (Q1-Q5):

    Q1: "In the past few weeks, have you wished you were dead?"
      - If answered YES, we set a positive flag and route to Q2's YES branch (node "2y").
      - If answered NO, we set a negative flag and route to Q2's NO branch (node "2n").
      - 'Other' responses trigger a retry (r=1), and if exceeded, the assessment ends.

    Q2: "In the past few weeks, have you felt that you or your family would be better off if you were dead?"
      - For a YES branch from Q1 (node "2y"):
          * Regardless of response (YES or NO), we continue with a positive flag to Q3's YES branch ("3y").
      - For a NO branch from Q1 (node "2n"):
          * A YES response here sets the positive flag and routes to Q3's YES branch ("3y").
          * A NO response maintains the negative flag and routes to Q3's NO branch ("3n").

    Q3: "In the past week, have you been having thoughts about killing yourself?"
      - From the YES branch (node "3y"):
          * Both YES and NO responses maintain the positive flag and route to Q4's YES branch ("4y").
      - From the NO branch (node "3n"):
          * A YES response switches to the positive branch ("4y").
          * A NO response remains negative and routes to Q4's NO branch ("4n").

    Q4: "Have you ever tried to kill yourself? If yes, when?"
      - In the YES branch (node "4y"), the existence of a positive flag means that Q5 will be asked; 
        both YES and NO responses route to Q5 (node "5").
      - In the NO branch (node "4n"), if the response is NO (and no positive flag has been raised),
        the assessment ends immediately (END). However, if a YES is encountered here, it overrides
        the negative flag and routes to Q5 (node "5").

    Q5: "Are you having thoughts of killing yourself right now?"
      - This final question is only administered if at least one of Q1-Q4 generated a positive (YES) flag.
      - Regardless of the response to Q5, the assessment terminates (END).

    Note on Node IDs & qid:
      - Using different node IDs that share the same qid (for example, "2y" and "2n") allows the
        system to remember the branch (i.e., positive flag vs. negative flag) taken by the user. This
        approach enables the assessment to later decide whether to administer Q5 based on any positive
        indications across Q1-Q4.
    """

    @property
    def name(self) -> str:
        return "assessment.asq"

    @property
    def verbose_name(self) -> str:
        return "ASQ"

    @property
    def N(self) -> int:
        return len(set(node.qid for node in self.questions.values()))

    @property
    def low(self) -> int:
        return 0

    @property
    def high(self) -> int:
        return 1

    @property
    def labels(self) -> List[str]:
        return ["No", "Yes"]

    @property
    def questions(self) -> Dict[str, QuestionNode]:
        return {
            # Q1: Ask about wishing to be dead.
            "1": QuestionNode(
                node_id="1",
                qid=1,
                text="In the past few weeks, have you wished you were dead?",
                y="2y",  # YES: set positive flag; proceed to Q2 YES branch.
                n="2n",  # NO: remain negative; proceed to Q2 NO branch.
                o=END,
                r=1
            ),
            # Q2: Ask about feeling that self/family would be better off dead.
            "2y": QuestionNode(
                node_id="2y",
                qid=2,
                text="In the past few weeks, have you felt that you or your family would be better off if you were dead?",
                y="3y",  # YES: maintain positive flag.
                n="3y",  # NO: positive flag remains from Q1.
                o=END,
                r=1
            ),
            "2n": QuestionNode(
                node_id="2n",
                qid=2,
                text="In the past few weeks, have you felt that you or your family would be better off if you were dead?",
                y="3y",  # YES: positive flag now set.
                n="3n",  # NO: continue with negative flag.
                o=END,
                r=1
            ),
            # Q3: Ask about having thoughts of killing oneself.
            "3y": QuestionNode(
                node_id="3y",
                qid=3,
                text="In the past week, have you been having thoughts about killing yourself?",
                y="4ya",  # YES: maintain positive flag.
                n="4ya",  # NO: still positive flag.
                o=END,
                r=1
            ),
            "3n": QuestionNode(
                node_id="3n",
                qid=3,
                text="In the past week, have you been having thoughts about killing yourself?",
                y="4ya",  # YES: switch to positive branch.
                n="4na",  # NO: remain negative.
                o=END,
                r=1
            ),
            # Q4: Ask about previous suicide attempts.
            "4ya": QuestionNode(
                node_id="4ya",
                qid="4a",
                text="Have you ever tried to kill yourself?",
                y="4yb",  # YES: maintain positive flag
                n="5y",   # NO: as positive flag was raised earlier, jump to Q5
                o="5y",
                r=1
            ),
            "4na": QuestionNode(
                node_id="4na",
                qid="4a",
                text="Have you ever tried to kill yourself?",
                y="4yb",  # YES: override negative flag and go to Q4b
                n=END,    # NO: as no positive flag was raised earlier, end assessment.
                o=END,
                r=1
            ),
            "4yb": QuestionNode(
                node_id="4yb",
                qid="4b",
                text="How?",
                y="4yc",  # YES/NO: has no significance for this question; no switching
                n="4yc",
                o="5y",
                r=1
            ),
            "4nb": QuestionNode(
                node_id="4nb",
                qid="4b",
                text="How?",
                y="4nc",  # YES/NO: has no significance for this question; no switching
                n="4nc",
                o="5y",
                r=1
            ),
            "4yc": QuestionNode(
                node_id="4yc",
                qid="4c",
                text="When?",
                y="5y",   # YES/NO: has no significance for this question; no switching
                n="5y",
                o="5y",
                r=1
            ),
            "4nc": QuestionNode(
                node_id="4nc",
                qid="4c",
                text="When?",
                y=END,    # YES/NO: has no significance for this question; no switching
                n=END,
                o=END,
                r=1
            ),
            # Q5: Final question about current suicidal thoughts.
            "5y": QuestionNode(
                node_id="5y",
                qid=5,
                text="Are you having thoughts of killing yourself right now?",
                y=END,  # Terminal node: assessment ends.
                n=END,
                o=END,
                r=1
            ),
        }

    @property
    def base_node_id(self) -> str:
        return "1"

    def severity(self, data: Dict[str, Dict[str, int]]) -> str:
        """
        Determines the screening result.
        A 'Positive' screen is flagged if any of the responses to Q1-Q4 is 'Yes' (score = 1).
        Otherwise, the screen is considered 'Negative'.
        """

        if all(data[str(qid)]["score"] == 0 for qid in data.keys()):
            return "Negative"
        if data["5"]["score"] == 1:
            return "Acute positive screen"
        return "Non-acute positive screen"

    def total_score(self, data: Dict[str, Dict[str, int]]) -> int:
        """
        Returns the sum of binary scores (0 for 'No', 1 for 'Yes') for consistency with the
        base class, even though the primary use of the ASQ is as a screening tool rather than
        a graded assessment.
        """
        return sum(data[str(qid)]["score"] for qid in data.keys())


class PhaseMap:
    """Manager class for assessment phase mapping and sequence."""

    _seq = [
        PHQ9Phase().name,
        GAD7Phase().name,
        # ASQPhase().name,
        MonitoringPhase().name,
    ]

    _mapper = {
        PHQ9Phase().name: PHQ9Phase(),
        GAD7Phase().name: GAD7Phase(),
        MonitoringPhase().name: MonitoringPhase(),
        ASQPhase().name: ASQPhase(),
    }

    @classmethod
    def first(cls) -> str:
        """Get the first (init) phase name in the sequence."""
        return cls._seq[0]

    @classmethod
    def last(cls) -> str:
        """Get the last phase name in the sequence."""
        return cls._seq[-1]

    @classmethod
    def get(cls, name: str) -> BaseAssessmentPhase:
        return cls._mapper.get(name)

    @classmethod
    def get_first(cls) -> BaseAssessmentPhase:
        return cls._mapper[cls.first()]

    @classmethod
    def get_last(cls) -> BaseAssessmentPhase:
        return cls._mapper[cls.last()]

    @classmethod
    def all(cls) -> List[BaseAssessmentPhase]:
        return [cls._mapper[name] for name in cls._mapper]

    @classmethod
    def next(cls, current: str, wrap=False) -> str:
        """Get the next phase in the sequence."""
        assert current in cls._seq, f"Invalid phase: {current}"
        if wrap:
            return cls._seq[(cls._seq.index(current) + 1) % len(cls._seq)]
        if cls._seq.index(current) + 1 == len(cls._seq):
            return END
        return cls._seq[cls._seq.index(current) + 1]


if __name__ == "__main__":
    from icecream import ic
    import random, json

    phase = PHQ9Phase()
    phase = ic(PhaseMap.get(PhaseMap.next("assessment.phq9")))
    ic(phase.verbose_name)
    ic(phase.N)

    phase = ASQPhase()
    ic(json.dumps(phase.get_questions_dict()))
    q_node = phase.get(phase.base_node_id)
    r = 0
    while q_node != END:

        tr = random.choice(["y", "n", "o", "c"])
        ic(q_node, tr)
        q_node = phase.next_q(q_node.node_id, tr, r=r)
        if tr == "o":
            r += 1
        else: r = 0
        
    ic(q_node)

    phase = PHQ9Phase()
    node = phase.next_q("2", "o", r=1)
    ic(node)
