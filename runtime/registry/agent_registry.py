from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Type

if TYPE_CHECKING:
    from agents.base import Agent

logger = logging.getLogger(__name__)


class AgentRegistry:
    """
    Registro central de Agents.
    """

    def __init__(self) -> None:
        self._agents: dict[str, Type[Agent]] = {}
        self._aliases: dict[str, str] = {}

    @staticmethod
    def normalize(value: str | None) -> str:
        if not value:
            return ""
        return value.lower().strip().replace("-", "_").replace(" ", "_")

    def register(
        self,
        name: str,
        factory: Type[Agent],
        aliases: tuple[str, ...] | list[str] | None = None,
        overwrite: bool = False,
    ) -> None:
        key = self.normalize(name)
        if not key:
            raise ValueError("Agent requiere name")
        if not factory:
            raise ValueError("Factory Agent inválida")
        if key in self._agents and not overwrite:
            raise ValueError(f"Agent ya registrado: {key}")

        self._agents[key] = factory
        if aliases:
            for alias in aliases:
                alias_key = self.normalize(alias)
                if alias_key:
                    self._aliases[alias_key] = key
        logger.info("Agent registrado=%s", key)

    def resolve_name(self, name: str) -> str:
        key = self.normalize(name)
        return self._aliases.get(key, key)

    def get(self, name: str) -> Agent | None:
        key = self.resolve_name(name)
        factory = self._agents.get(key)
        if not factory:
            return None
        return factory()

    def has(self, name: str) -> bool:
        return self.resolve_name(name) in self._agents

    def list(self) -> list[str]:
        return sorted(self._agents.keys())

    def count(self) -> int:
        return len(self._agents)

    def aliases(self) -> dict[str, str]:
        return dict(self._aliases)

    def unregister(self, name: str) -> None:
        key = self.resolve_name(name)
        self._agents.pop(key, None)
        self._aliases = {alias: target for alias, target in self._aliases.items() if target != key}

    def clear(self) -> None:
        self._agents.clear()
        self._aliases.clear()
