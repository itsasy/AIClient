from __future__ import annotations

from dataclasses import dataclass, field

from typing import Any


@dataclass(slots=True)
class IntentResult:
    """
    Resultado semántico del análisis de intención.

    Representa únicamente comprensión de intención.

    No:

    - Construye ExecutionPlans.
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

    # ======================================================
    # Lifecycle
    # ======================================================

    def __post_init__(
        self,
    ) -> None:

        self.intent = self.normalize(
            self.intent,
        )

        self.domain = self.normalize(
            self.domain,
        )

        self.category = self.normalize(
            self.category,
        )

        self.complexity = self.normalize(
            self.complexity,
        )

        self.confidence = max(
            0.0,
            min(
                1.0,
                float(self.confidence),
            ),
        )

    # ======================================================
    # Normalization
    # ======================================================

    @staticmethod
    def normalize(
        value: str | None,
    ) -> str:

        if not value:

            return ""

        return (
            value.lower()
            .strip()
            .replace(
                "-",
                "_",
            )
            .replace(
                " ",
                "_",
            )
        )

    # ======================================================
    # Serialization
    # ======================================================

    def to_dict(
        self,
    ) -> dict[str, Any]:

        return {
            "intent": self.intent,
            "domain": self.domain,
            "category": self.category,
            "complexity": self.complexity,
            "confidence": self.confidence,
            "entities": dict(
                self.entities,
            ),
            "signals": list(
                self.signals,
            ),
            "metadata": dict(
                self.metadata,
            ),
        }

    # ======================================================
    # Helpers
    # ======================================================

    def has_entity(
        self,
        key: str,
    ) -> bool:

        return key in self.entities

    def get_entity(
        self,
        key: str,
        default: Any = None,
    ) -> Any:

        return self.entities.get(
            key,
            default,
        )
