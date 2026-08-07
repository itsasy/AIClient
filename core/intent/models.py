from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class IntentResult:
    """
    Contrato de interpretación de la petición del usuario.

    Representa QUÉ quiere hacer el usuario.

    NO representa:
    - cómo debe ejecutarse;
    - qué agente debe utilizarse;
    - qué skill debe ejecutarse;
    - qué provider LLM debe utilizarse;
    - qué pasos deben ejecutarse.

    Flujo oficial:

        User
          ↓
        IntentAnalyzer
          ↓
        IntentResult
          ↓
        PlanBuilder
          ↓
        ExecutionPlan
    """

    intent: str
    domain: str
    category: str = "general"
    complexity: str = "normal"
    confidence: float = 0.0
    entities: dict[str, Any] = field(default_factory=dict)
    signals: list[str] = field(default_factory=list)
    original_query: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.intent = self.intent.strip().lower()
        self.domain = self.domain.strip().lower()

        if not self.intent:
            raise ValueError("IntentResult requiere un intent válido.")

        if not self.domain:
            raise ValueError("IntentResult requiere un domain válido.")

        if self.confidence is not None:
            if not 0.0 <= self.confidence <= 1.0:
                raise ValueError("IntentResult.confidence debe estar entre 0.0 y 1.0.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent,
            "domain": self.domain,
            "category": self.category,
            "complexity": self.complexity,
            "confidence": self.confidence,
            "entities": dict(self.entities),
            "signals": list(self.signals),
            "original_query": self.original_query,
            "metadata": dict(self.metadata),
        }
