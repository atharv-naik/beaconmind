"""
Definitions for assessment phases and their details.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Iterable, List, Tuple, Union


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
    @abstractmethod
    def questions(self) -> List[Dict[str, Any]]:
        """List of questions in the assessment."""
        pass

    @property
    @abstractmethod
    def N(self) -> int:
        """Number of questions in the assessment."""
        pass

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

    def get(self, id: int) -> str:
        """Get the question text for a given question ID."""
        if 1 <= id <= self.N:
            return self.questions[id - 1]["text"]
        raise ValueError(f"Invalid question ID: {id}")
    
    @abstractmethod
    def severity(self, data: Dict[str, Dict[str, int]]) -> str:
        """Get severity based on assessment scores."""
        pass

    @abstractmethod
    def total_score(self, data: Dict[str, Dict[str, int]]) -> int:
        """Get the total score of the assessment."""
        pass

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
    def N(self) -> int:
        return 9
    
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
    def questions(self) -> List[Dict[str, Union[int, str]]]:
        return [
            {"id": 1, "text": "Little interest or pleasure in doing things"},
            {"id": 2, "text": "Feeling down, depressed, or hopeless"},
            {"id": 3, "text": "Trouble falling or staying asleep, or sleeping too much"},
            {"id": 4, "text": "Feeling tired or having little energy"},
            {"id": 5, "text": "Poor appetite or overeating"},
            {"id": 6, "text": "Feeling bad about yourself - or that you are a failure or have let yourself or your family down"},
            {"id": 7, "text": "Trouble concentrating on things, such as reading the newspaper or watching television"},
            {"id": 8, "text": "Moving or speaking so slowly that other people could have noticed. Or the opposite - being so fidgety or restless that you have been moving around a lot more than usual"},
            {"id": 9, "text": "Thoughts that you would be better off dead, or of hurting yourself"},
        ]

    def severity(self, data: Union[Dict[str, Dict[str, int]], int]) -> str:
        """Get the severity of depression based on the PHQ-9 score."""
        if isinstance(data, int):
            score = data
        else:
            score = sum([data[str(q_id)]["score"] for q_id in range(1, self.N + 1)])
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
        return sum([data[str(q_id)]["score"] for q_id in range(1, self.N + 1)])


class GAD7Phase(BaseAssessmentPhase):
    
    @property
    def name(self) -> str:
        return "assessment.gad7"
    
    @property
    def verbose_name(self) -> str:
        return "GAD7"
    
    @property
    def N(self) -> int:
        return 7
    
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
    def questions(self) -> List[Dict[str, Union[int, str]]]:
        return [
            {"id": 1, "text": "Feeling nervous, anxious or on edge?"},
            {"id": 2, "text": "Not being able to stop or control worrying?"},
            {"id": 3, "text": "Worrying too much about different things?"},
            {"id": 4, "text": "Trouble relaxing?"},
            {"id": 5, "text": "Being so restless that it is hard to sit still?"},
            {"id": 6, "text": "Becoming easily annoyed or irritable?"},
            {"id": 7, "text": "Feeling afraid as if something awful might happen?"},
        ]
    
    def severity(self, data: Union[Dict[int, Dict[str, int]], int]) -> str:
        """Get the severity of anxiety based on the GAD-7 score."""
        if isinstance(data, int):
            score = data
        else:
            score = sum([data[str(q_id)]["score"] for q_id in range(1, self.N + 1)])
        match score:
            case n if n <= 4:
                return "Minimal anxiety"
            case n if n <= 9:
                return "Mild anxiety"
            case n if n <= 14:
                return "Moderate anxiety"
            case _:
                return "Severe anxiety"
    
    def total_score(self, data: Dict[int, Dict[str, int]]) -> int:
        """Get the total score of the GAD-7 assessment."""
        return sum([data[str(q_id)]["score"] for q_id in range(1, self.N + 1)])


class MonitoringPhase(BaseAssessmentPhase):

    @property
    def name(self) -> str:
        return "monitoring"
    
    @property
    def verbose_name(self) -> str:
        return "Monitoring"
    
    @property
    def N(self) -> int:
        return len(self.questions)
    
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
    def questions(self) -> List[Dict[str, Union[int, str]]]:
        return [
            {"id": 1, "text": "How have you been feeling emotionally over the past week?"},
            {"id": 2, "text": "Have you experienced any changes in your mood or energy levels?"},
            {"id": 3, "text": "Have you noticed any improvement or worsening in your [specific symptoms, e.g., anxiety, depression, psychosis]?"},
            {"id": 4, "text": "Have you experienced any new symptoms since your last visit?"},
            {"id": 5, "text": "Have you been taking your prescribed medications as directed?"},
            {"id": 6, "text": "Have you missed any doses? If yes, how often?"},
            {"id": 7, "text": "Have you experienced any side effects from the medication?"},
            {"id": 8, "text": "Have you been able to work on the goals or coping strategies discussed in your last session?"},
            {"id": 9, "text": "Do you feel that any particular challenges are hindering your progress?"},
            {"id": 10, "text": "Are you able to perform daily tasks as usual (e.g., work, household responsibilities)?"},
            {"id": 11, "text": "Have you engaged in social activities or connected with friends/family recently?"},
            {"id": 12, "text": "Have you experienced any aggressive or harmful impulses towards others?"},
            {"id": 13, "text": "Have you used any substances (e.g., alcohol, drugs) since your last visit?"},
            {"id": 14, "text": "Are there any concerns or challenges you'd like to discuss with your care team?"},
        ]
    
    def severity(self, data: Union[Dict[int, Dict[str, int]], int]) -> str:
        return "Not applicable"
    
    def total_score(self, data: Dict[int, Dict[str, int]]) -> int:
        return 0


class PhaseMap:
    """Manager class for assessment phase mapping and sequence."""

    _seq = [
        PHQ9Phase().name,
        GAD7Phase().name,
        MonitoringPhase().name,
    ]

    _mapper = {
        PHQ9Phase().name: PHQ9Phase(),
        GAD7Phase().name: GAD7Phase(),
        MonitoringPhase().name: MonitoringPhase(),
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
        return [cls._mapper[name] for name in cls._seq]

    @classmethod
    def next(cls, current: str, wrap=False) -> str:
        """Get the next phase in the sequence."""
        assert current in cls._seq, f"Invalid phase: {current}"
        if wrap:
            return cls._seq[(cls._seq.index(current) + 1) % len(cls._seq)]
        assert current != cls._seq[-1], f"No next phase available after {current}"
        return cls._seq[cls._seq.index(current) + 1]


if __name__ == "__main__":
    from icecream import ic

    phase = PHQ9Phase()
    ic(phase == PhaseMap.get(PhaseMap.first()))
    phase = ic(PhaseMap.get(PhaseMap.next("assessment.phq9")))
    ic(phase)
    ic(phase.name)
    ic(phase.short_name)
    ic(phase.verbose_name)
    ic(phase.questions)
    ic(phase.N)
    ic(phase.low)
    ic(phase.high)
    ic(phase.span)
    ic(phase.labels)
    ic(phase.cap)
    ic(phase.get(1))
    scores = {
        "1": {
            "score": 0,
            "remark": "The patient enjoys activities and finds pleasure in them.",
            "snippet": "I enjoy stuff mostly.",
            "keywords": ["enjoy activities", "positive mood"]
        },
        "2": {
            "score": 2,
            "remark": "The patient feels down and like a 'loser' due to job placement pressures.",
            "snippet": "I feel a loser... yet to land a job while my friends have grabbed like 50lpa+ jobs.",
            "keywords": ["job pressure", "feeling down"]
        },
        "3": {
            "score": 0,
            "remark": "The patient reports no changes in sleep patterns.",
            "snippet": "Nothing particular here.",
            "keywords": ["consistent sleep"]
        },
        "4": {
            "score": 1,
            "remark": "The patient feels tired frequently but attributes it to being naturally less energetic.",
            "snippet": "I guess I am always tired... I've always been a lazy person.",
            "keywords": ["low energy", "natural pace"]
        },
        "5": {
            "score": 0,
            "remark": "The patient has a consistent appetite and enjoys eating.",
            "snippet": "I'm a foodie so naturally I eat a lot.",
            "keywords": ["consistent appetite", "enjoys food"]
        },
        "6": {
            "score": 2,
            "remark": "The patient feels like a failure due to comparison with peers during placement season.",
            "snippet": "I feel a loser... my friends have grabbed like 50lpa+ jobs.",
            "keywords": ["feeling failure", "peer comparison"]
        },
        "7": {
            "score": 0,
            "remark": "The patient enjoys reading and distracts themselves intentionally with anime.",
            "snippet": "I love reading... intentionally distract myself by watching excessive anime.",
            "keywords": ["enjoys reading", "distraction"]
        },
        "8": {
            "score": 0,
            "remark": "The patient has not noticed restlessness or slow movements.",
            "snippet": "No no nah.",
            "keywords": []
        },
        "9": {
            "score": 0,
            "remark": "The patient does not report thoughts of self-harm or being better off not around.",
            "snippet": "Not that sort of stuff.",
            "keywords": []
        }
    }
    ic(phase.severity(scores))
    ic(phase.total_score(scores))
    ic(PhaseMap.first())
    ic(PhaseMap.get("assessment.phq9"))
