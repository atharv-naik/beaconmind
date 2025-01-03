from abc import ABC, abstractmethod
from typing import Dict, List


class BaseAssessmentPhase(ABC):
    """Abstract base class for assessment details."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the assessment."""
        pass

    @property
    @abstractmethod
    def verbose_name(self) -> str:
        """Verbose name of the assessment."""
        pass

    @property
    @abstractmethod
    def questions(self) -> List[Dict[str, str]]:
        """List of questions in the assessment."""
        pass

    @property
    @abstractmethod
    def N(self) -> int:
        """Number of questions in the assessment."""
        pass

    def get(self, id: int) -> str:
        """Get the question text for a given question ID."""
        if 1 <= id <= self.N:
            return self.questions[id - 1]["text"]
        raise ValueError(f"Invalid question ID: {id}")
    
    @abstractmethod
    def severity(self, data: dict) -> str:
        """Calculate the severity of the assessment based on the scores."""
        pass

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name


class PHQ9Phase(BaseAssessmentPhase):

    @property
    def name(self) -> str:
        return "phq9"

    @property
    def verbose_name(self) -> str:
        return f"assessment.{self.name}"

    @property
    def N(self) -> int:
        return 9

    @property
    def questions(self) -> List[Dict[str, str]]:
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

    def severity(self, data: dict) -> str:
        """Calculate the severity of depression based on the PHQ-9 score."""
        score = sum([data[q_id]["score"] for q_id in range(1, self.N + 1)])
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


class GAD7Phase(BaseAssessmentPhase):
    # TODO: Add GAD7
    pass


class PhaseMap:

    _seq = [
        PHQ9Phase().verbose_name,
        # ...,
        # "monitoring",
    ]

    _mapper = {
        PHQ9Phase().verbose_name: PHQ9Phase(),
        # ...,
        # "monitoring": None,
    }

    @classmethod
    def first(cls) -> str:
        """Get the first (init) phase in the sequence."""
        return cls._seq[0]

    @classmethod
    def get(cls, verbose_name: str) -> BaseAssessmentPhase:
        return cls._mapper.get(verbose_name)

    @classmethod
    def next(cls, current: str) -> str:
        """Get the next phase in the sequence."""
        assert current in cls._seq, f"Invalid phase: {current}"
        assert current != cls._seq[-1], "No next phase available"
        return cls._seq[cls._seq.index(current) + 1]
