"""Data Quality Gate — docs/ARCHITECTURE.md item 3. Mesmo padrão do SAL Intelligence OS
(componente genérico, reaproveitado sem redesenho)."""

from dataclasses import dataclass, field


@dataclass
class QualityCheckResult:
    passed: bool
    score: int
    reasons: list[str] = field(default_factory=list)


class DataQualityGate:
    def __init__(self, minimum_score: int = 60) -> None:
        self.minimum_score = minimum_score

    def check_completeness(self, record: dict, required_fields: list[str]) -> tuple[bool, str]:
        missing = [f for f in required_fields if record.get(f) in (None, "", [])]
        if missing:
            return False, f"campos obrigatórios ausentes: {', '.join(missing)}"
        return True, "completo"

    def check_materiality(self, absolute_delta: float, materiality_threshold: float) -> tuple[bool, str]:
        if abs(absolute_delta) < materiality_threshold:
            return False, f"desvio abaixo do limite de materialidade ({materiality_threshold})"
        return True, "material"

    def evaluate(self, checks: list[tuple[bool, str]]) -> QualityCheckResult:
        if not checks:
            return QualityCheckResult(passed=False, score=0, reasons=["nenhum check executado"])
        passed_count = sum(1 for ok, _ in checks if ok)
        score = round(100 * passed_count / len(checks))
        reasons = [reason for ok, reason in checks if not ok]
        return QualityCheckResult(passed=score >= self.minimum_score and not reasons, score=score, reasons=reasons)
