from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(slots=True)
class Interaction:
    """Una interacción registrada del usuario con el sistema."""

    timestamp: datetime
    user_query: str
    assistant_response: str
    success: bool
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "user_query": self.user_query,
            "assistant_response": self.assistant_response,
            "success": self.success,
            "metadata": self.metadata,
        }


@dataclass(slots=True)
class ConsolidationProposal:
    """Propuesta de cambio a la memoria."""

    type: str  # "standard", "spec", "engram"
    key: str | None = None
    old_value: str | None = None
    new_value: str | None = None
    reason: str = ""
    source: str = ""  # qué interacción lo generó

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "key": self.key,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "reason": self.reason,
            "source": self.source,
        }


@dataclass(slots=True)
class ConsolidationReport:
    """Informe de consolidación diaria."""

    date: str
    interactions: list[Interaction]
    patterns: list[str]
    proposals: list[ConsolidationProposal]
    summary: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "date": self.date,
            "interactions": [i.to_dict() for i in self.interactions],
            "patterns": self.patterns,
            "proposals": [p.to_dict() for p in self.proposals],
            "summary": self.summary,
        }
