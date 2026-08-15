"""Priority Engine — implementa config/priority-scoring.yaml. Mesmo padrão do SAL Intelligence OS."""

from dataclasses import dataclass
from pathlib import Path

import yaml

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[3] / "config" / "priority-scoring.yaml"


@dataclass
class PriorityResult:
    score: float
    label: str
    human_approval_required: bool
    triggered_gates: list[str]


class PriorityEngine:
    def __init__(self, config_path: Path = DEFAULT_CONFIG_PATH) -> None:
        with open(config_path, encoding="utf-8") as f:
            self.config = yaml.safe_load(f)
        self.dimensions: dict[str, dict] = self.config["dimensions"]
        self.gates: dict = self.config["gates"]
        self.labels: dict[str, str] = self.config["labels"]

    def score(self, dimension_values: dict[str, float]) -> float:
        missing = set(self.dimensions) - set(dimension_values)
        if missing:
            raise ValueError(f"dimensões faltando para o cálculo de score: {missing}")
        total = sum(dimension_values[name] * spec["weight"] for name, spec in self.dimensions.items())
        return round(total, 2)

    def label_for(self, score: float) -> str:
        for score_range, label in self.labels.items():
            low, high = (int(x) for x in score_range.split("-"))
            if low <= score <= high:
                return label
        return "SEM CLASSIFICAÇÃO"

    def requires_human_approval(self, triggered_flags: list[str]) -> tuple[bool, list[str]]:
        required = self.gates.get("human_approval_required_if", [])
        triggered = [flag for flag in triggered_flags if flag in required]
        return bool(triggered), triggered

    def evaluate(self, dimension_values: dict[str, float], triggered_flags: list[str] | None = None) -> PriorityResult:
        score = self.score(dimension_values)
        needs_approval, triggered_gates = self.requires_human_approval(triggered_flags or [])
        return PriorityResult(
            score=score,
            label=self.label_for(score),
            human_approval_required=needs_approval,
            triggered_gates=triggered_gates,
        )
