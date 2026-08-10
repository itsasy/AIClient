from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from core.context.base import BaseContextProvider
from core.execution_plan import ExecutionPlan

logger = logging.getLogger(__name__)


class SwarmForgeProvider(BaseContextProvider):

    key = "swarmforge"

    def __init__(self) -> None:
        self.swarmforge_dir = Path.home() / ".swarmforge" / "constitution"

        self._constitution: dict[str, str] = {}

        if self.swarmforge_dir.exists():
            self._load_constitution()

    def _load_constitution(self) -> None:
        for prompt_file in self.swarmforge_dir.glob("*.prompt"):
            try:
                content = prompt_file.read_text(
                    encoding="utf-8",
                    errors="ignore",
                )

                self._constitution[prompt_file.stem] = content

            except OSError:
                logger.warning(
                    "No se pudo cargar %s",
                    prompt_file,
                )

    def load(
        self,
        plan: ExecutionPlan,
        context: dict[str, Any],
    ) -> dict[str, Any]:

        if not self._constitution:
            return {}

        sections = [f"## {name}\n{content}" for name, content in self._constitution.items()]

        return {
            "constitution": "\n\n".join(sections),
            "articles": dict(self._constitution),
        }
