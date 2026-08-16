from __future__ import annotations

from typing import Any

__all__ = [
    "ExecutionEngine",
    "UnitDispatcher",
    "AgentRegistry",
    "SkillRegistry",
]


def __getattr__(name: str) -> Any:
    if name == "ExecutionEngine":
        from .execution_engine import ExecutionEngine

        return ExecutionEngine

    if name == "UnitDispatcher":
        from .dispatcher import UnitDispatcher

        return UnitDispatcher

    if name == "AgentRegistry":
        from .registry.agent_registry import AgentRegistry

        return AgentRegistry

    if name == "SkillRegistry":
        from .registry.skill_registry import SkillRegistry

        return SkillRegistry

    raise AttributeError(
        f"module {__name__!r} has no attribute {name!r}",
    )
