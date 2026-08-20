from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar


@dataclass(slots=True)
class RetryDecision:
    """
    Decisión tomada por RetryPolicy.
    Solo decide, no ejecuta.
    """

    retry: bool
    reason: str
    delay_seconds: float = 0.0
    needs_human: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.reason = str(self.reason).strip() or "sin razón especificada"
        if self.delay_seconds < 0:
            raise ValueError("delay_seconds no puede ser negativo.")
        self.metadata = dict(self.metadata or {})

    @classmethod
    def yes(
        cls,
        reason: str,
        delay_seconds: float = 0.5,
        metadata: dict[str, Any] | None = None,
    ) -> RetryDecision:
        return cls(
            retry=True,
            reason=reason,
            delay_seconds=delay_seconds,
            metadata=dict(metadata or {}),
        )

    @classmethod
    def no(
        cls,
        reason: str,
        metadata: dict[str, Any] | None = None,
    ) -> RetryDecision:
        return cls(
            retry=False,
            reason=reason,
            delay_seconds=0.0,
            metadata=dict(metadata or {}),
        )

    @classmethod
    def pause(
        cls,
        reason: str,
        metadata: dict[str, Any] | None = None,
    ) -> RetryDecision:
        return cls(
            retry=False,
            reason=reason,
            delay_seconds=0.0,
            needs_human=True,
            metadata=dict(metadata or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "retry": self.retry,
            "reason": self.reason,
            "delay_seconds": self.delay_seconds,
            "needs_human": self.needs_human,
            "metadata": dict(self.metadata),
        }
