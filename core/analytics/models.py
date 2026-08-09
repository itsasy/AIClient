from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(slots=True)
class ExecutionMetric:
    """Métrica de una ejecución individual."""

    execution_id: str
    plan_id: str
    intent: str
    provider: str
    model: str
    started_at: datetime
    duration: float
    status: str  # "success", "partial", "failed", "cancelled"
    retry_count: int
    tokens: int | None = None
    estimated_cost: float | None = None
    error: str | None = None
    step_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "plan_id": self.plan_id,
            "intent": self.intent,
            "provider": self.provider,
            "model": self.model,
            "started_at": self.started_at.isoformat(),
            "duration": self.duration,
            "status": self.status,
            "retry_count": self.retry_count,
            "tokens": self.tokens,
            "estimated_cost": self.estimated_cost,
            "error": self.error,
            "step_count": self.step_count,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExecutionMetric:
        return cls(
            execution_id=data["execution_id"],
            plan_id=data["plan_id"],
            intent=data["intent"],
            provider=data["provider"],
            model=data["model"],
            started_at=datetime.fromisoformat(data["started_at"]),
            duration=data["duration"],
            status=data["status"],
            retry_count=data["retry_count"],
            tokens=data.get("tokens"),
            estimated_cost=data.get("estimated_cost"),
            error=data.get("error"),
            step_count=data.get("step_count", 0),
            metadata=data.get("metadata", {}),
        )
