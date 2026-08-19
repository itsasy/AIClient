from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar


@dataclass(slots=True)
class EvaluationResult:
    """
    Resultado de la evaluación de SelfCritic.

    Separado de ExecutionResult:
        ExecutionResult  → qué ocurrió al ejecutar
        EvaluationResult → qué tan bueno fue el resultado
    """

    VALID_STATUSES: ClassVar[frozenset[str]] = frozenset(
        {
            "passed",
            "failed",
            "unavailable",  # SelfCritic no pudo evaluar
            "skipped",  # no se pidió evaluación
        }
    )

    status: str
    passed: bool | None = None
    score: int | None = None
    issues: list[str] = field(default_factory=list)
    corrections: list[str] = field(default_factory=list)
    reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.status = self.status.strip().lower()
        if self.status not in self.VALID_STATUSES:
            raise ValueError(
                f"EvaluationResult.status inválido: {self.status}. "
                f"Permitidos: {sorted(self.VALID_STATUSES)}"
            )

        if self.passed is not None and not isinstance(self.passed, bool):
            raise ValueError("EvaluationResult.passed debe ser bool o None.")

        if self.score is not None and (
            isinstance(self.score, bool) or not isinstance(self.score, int)
        ):
            raise ValueError("EvaluationResult.score debe ser int o None.")

        self.issues = [str(i) for i in (self.issues or [])]
        self.corrections = [str(c) for c in (self.corrections or [])]
        self.reason = str(self.reason).strip() if self.reason else None
        self.metadata = dict(self.metadata or {})

    # ---------------------------------------------------------
    # Factories
    # ---------------------------------------------------------

    @classmethod
    def passed(
        cls,
        score: int | None = None,
        reason: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> EvaluationResult:
        return cls(
            status="passed",
            passed=True,
            score=score,
            reason=reason or "Evaluación superada",
            metadata=dict(metadata or {}),
        )

    @classmethod
    def failed(
        cls,
        issues: list[str] | None = None,
        corrections: list[str] | None = None,
        score: int | None = None,
        reason: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> EvaluationResult:
        return cls(
            status="failed",
            passed=False,
            score=score,
            issues=list(issues or []),
            corrections=list(corrections or []),
            reason=reason or "Evaluación fallida",
            metadata=dict(metadata or {}),
        )

    @classmethod
    def unavailable(
        cls,
        reason: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> EvaluationResult:
        return cls(
            status="unavailable",
            passed=None,
            reason=reason or "SelfCritic no pudo evaluar el resultado",
            metadata=dict(metadata or {}),
        )

    @classmethod
    def skipped(
        cls,
        reason: str | None = None,
    ) -> EvaluationResult:
        return cls(
            status="skipped",
            passed=None,
            reason=reason or "Evaluación no requerida",
        )

    # ---------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------

    @property
    def is_passed(self) -> bool:
        return self.status == "passed"

    @property
    def is_failed(self) -> bool:
        return self.status == "failed"

    @property
    def is_unavailable(self) -> bool:
        return self.status == "unavailable"

    @property
    def is_skipped(self) -> bool:
        return self.status == "skipped"

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "passed": self.passed,
            "score": self.score,
            "issues": list(self.issues),
            "corrections": list(self.corrections),
            "reason": self.reason,
            "metadata": dict(self.metadata),
        }
