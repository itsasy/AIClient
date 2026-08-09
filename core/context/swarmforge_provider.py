from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from core.context.base import BaseContextProvider
from core.execution_plan import ExecutionPlan

logger = logging.getLogger(__name__)


class SwarmForgeProvider(BaseContextProvider):
    """
    Proveedor de la "constitución" de SwarmForge.

    Carga reglas de ingeniería (Clean Code, SOLID, TDD, etc.)
    desde el repositorio de SwarmForge si está disponible.
    """

    key = "swarmforge"

    def __init__(self):
        self.swarmforge_dir = Path.home() / ".swarmforge" / "constitution"
        self._constitution: dict[str, str] = {}

        if self.swarmforge_dir.exists():
            self._load_constitution()

    def _load_constitution(self) -> None:
        """Carga los artículos de la constitución desde archivos .prompt."""
        for prompt_file in self.swarmforge_dir.glob("*.prompt"):
            try:
                content = prompt_file.read_text(encoding="utf-8", errors="ignore")
                name = prompt_file.stem
                self._constitution[name] = content
                logger.info("Cargado artículo de SwarmForge: %s", name)
            except Exception as e:
                logger.warning("Error cargando %s: %s", prompt_file, e)

    def load(
        self,
        plan: ExecutionPlan,
        context: dict[str, Any],
    ) -> None:
        if not self._constitution:
            return

        sections = []
        for name, content in self._constitution.items():
            sections.append(f"## {name}\n{content}")

        context[self.key] = "\n\n".join(sections)
        logger.info("SwarmForge constitución cargada (%d artículos)", len(self._constitution))
