from __future__ import annotations

from dataclasses import dataclass, field

from typing import Any


@dataclass(slots=True)
class IntentResult:
    """
    Resultado semántico del análisis de intención.

    Representa únicamente comprensión de intención.

    No:

    - Crea ExecutionPlans.
    - Selecciona Agents.
    - Selecciona Skills.
    - Ejecuta acciones.
    """

    intent: str

    domain: str

    category: str = "general"

    complexity: str = "normal"

    confidence: float = 0.0

    entities: dict[str, Any] = field(
        default_factory=dict,
    )

    signals: list[str] = field(
        default_factory=list,
    )

    metadata: dict[str, Any] = field(
        default_factory=dict,
    )

    def __post_init__(
        self,
    ) -> None:

        self.intent = self._normalize(
            self.intent,
        )

        self.domain = self._normalize(
            self.domain,
        )

        self.category = self._normalize(
            self.category,
        )

        self.complexity = self._normalize(
            self.complexity,
        )

        self.confidence = max(
            0.0,
            min(
                1.0,
                float(self.confidence),
            ),
        )

    @staticmethod
    def _normalize(
        value: str,
    ) -> str:

        if not value:
            return ""

        return value.lower().strip().replace("-", "_").replace(" ", "_")

    def to_dict(
        self,
    ) -> dict[str, Any]:

        return {
            "intent": self.intent,
            "domain": self.domain,
            "category": self.category,
            "complexity": self.complexity,
            "confidence": self.confidence,
            "entities": dict(self.entities),
            "signals": list(self.signals),
            "metadata": dict(self.metadata),
        }
