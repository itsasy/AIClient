from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class IntentResult:
    """
    Resultado normalizado del análisis de intención.

    Representa QUÉ quiere hacer el usuario.

    No representa:

    - cómo ejecutar la tarea;
    - qué agente utilizar;
    - qué skill utilizar;
    - qué provider LLM utilizar;
    - qué permisos conceder;
    - qué pasos ejecutar.

    Flujo:

        User
          ↓
        IntentAnalyzer
          ↓
        IntentResult
          ↓
        PlanBuilder
          ↓
        ExecutionPlan
          ↓
        Runtime
    """

    VALID_COMPLEXITIES = frozenset(
        {
            "low",
            "normal",
            "high",
            "complex",
        }
    )

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
        self.intent = self._normalize_required(
            self.intent,
            "intent",
        )

        self.domain = self._normalize_required(
            self.domain,
            "domain",
        )

        self.category = self._normalize_optional_string(
            self.category,
            "category",
            default="general",
        )

        self.complexity = self._normalize_complexity(
            self.complexity,
        )

        self.confidence = self._normalize_confidence(
            self.confidence,
        )

        if not isinstance(self.entities, dict):
            raise ValueError("IntentResult.entities debe ser un diccionario.")

        if not isinstance(self.signals, list):
            raise ValueError("IntentResult.signals debe ser una lista.")

        self.signals = [str(signal).strip() for signal in self.signals if str(signal).strip()]

        if not isinstance(self.metadata, dict):
            raise ValueError("IntentResult.metadata debe ser un diccionario.")

        self.original_query = (
            self.original_query.strip() if isinstance(self.original_query, str) else ""
        )

    # =========================================================
    # Normalization
    # =========================================================

    @staticmethod
    def _normalize_required(
        value: str,
        field_name: str,
    ) -> str:
        if not isinstance(value, str):
            raise ValueError(f"IntentResult.{field_name} debe ser un string.")

        value = value.strip().lower()

        if not value:
            raise ValueError(f"IntentResult.{field_name} no puede estar vacío.")

        return value.replace("-", "_").replace(" ", "_")

    @staticmethod
    def _normalize_optional_string(
        value: str | None,
        field_name: str,
        default: str,
    ) -> str:
        if value is None:
            return default

        if not isinstance(value, str):
            raise ValueError(f"IntentResult.{field_name} debe ser un string.")

        value = value.strip().lower()

        return value.replace("-", "_").replace(" ", "_") if value else default

    @classmethod
    def _normalize_complexity(
        cls,
        value: str,
    ) -> str:
        if not isinstance(value, str):
            raise ValueError("IntentResult.complexity debe ser un string.")

        value = value.lower().strip().replace("-", "_").replace(" ", "_")

        if value not in cls.VALID_COMPLEXITIES:
            raise ValueError(
                f"Complejidad inválida: {value}. "
                f"Valores permitidos: "
                f"{sorted(cls.VALID_COMPLEXITIES)}"
            )

        return value

    @staticmethod
    def _normalize_confidence(
        value: float,
    ) -> float:
        if isinstance(value, bool):
            raise ValueError("IntentResult.confidence debe ser numérico.")

        try:
            value = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("IntentResult.confidence debe ser numérico.") from exc

        if not 0.0 <= value <= 1.0:
            raise ValueError("IntentResult.confidence debe estar entre 0.0 y 1.0.")

        return value

    # =========================================================
    # Semantic helpers
    # =========================================================

    @property
    def is_high_confidence(self) -> bool:
        return self.confidence >= 0.80

    @property
    def is_complex(self) -> bool:
        return self.complexity in {
            "high",
            "complex",
        }

    def has_entity(
        self,
        name: str,
    ) -> bool:
        return bool(name and name in self.entities and self.entities[name] is not None)

    def get_entity(
        self,
        name: str,
        default: Any = None,
    ) -> Any:
        return self.entities.get(
            name,
            default,
        )

    # =========================================================
    # Serialization
    # =========================================================

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

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> IntentResult:
        if not isinstance(data, dict):
            raise ValueError("IntentResult.from_dict requiere un diccionario.")

        return cls(
            intent=data.get("intent", "conversation"),
            domain=data.get("domain", "conversation"),
            category=data.get("category", "general"),
            complexity=data.get("complexity", "normal"),
            confidence=data.get("confidence", 0.0),
            entities=data.get("entities", {}),
            signals=data.get("signals", []),
            original_query=data.get("original_query", ""),
            metadata=data.get("metadata", {}),
        )

    def __repr__(self) -> str:
        return (
            f"<IntentResult("
            f"intent={self.intent}, "
            f"domain={self.domain}, "
            f"category={self.category}, "
            f"complexity={self.complexity}, "
            f"confidence={self.confidence:.2f})>"
        )
