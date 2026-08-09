from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class CommandResult:
    """
    Resultado del análisis de un comando slash.
    """

    command: str  # "spec", "plan", "build", ...
    arguments: str  # el resto de la entrada
    is_command: bool = True  # siempre True para comandos slash
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "command": self.command,
            "arguments": self.arguments,
            "is_command": self.is_command,
            "metadata": dict(self.metadata),
        }
