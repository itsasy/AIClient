from __future__ import annotations

import logging

from runtime.registry.skill_registry import SkillRegistry
from skills.base import Skill
from skills.loader import SkillLoader

logger = logging.getLogger(__name__)


class SkillManager:
    """
    Fachada central de gestión de Skills.

    El Manager coordina Registry + Loader.

    No ejecuta Skills.
    """

    name = "skill_manager"

    def __init__(
        self,
        registry: SkillRegistry | None = None,
        loader: SkillLoader | None = None,
        auto_load: bool = True,
    ) -> None:

        self.registry = registry or SkillRegistry()

        self.loader = loader or SkillLoader(self.registry)

        self.loaded_defaults = False

        if auto_load:
            self.load_defaults()

    # ==========================================================
    # Loading
    # ==========================================================

    def load_defaults(self) -> None:

        if self.loaded_defaults:
            return

        result = self.loader.load_defaults()

        self.loaded_defaults = True

        failed = [module for module, success in result.items() if not success]

        if failed:
            logger.warning(
                "Módulos Skill fallidos=%s",
                failed,
            )

    def load_module(
        self,
        module_path: str,
    ) -> bool:

        if not module_path:
            return False

        return self.loader.load_module(
            module_path,
        )

    def reload(self) -> None:

        self.clear()

        self.loader.clear_state()

        self.loaded_defaults = False

        self.load_defaults()

    # ==========================================================
    # Resolution
    # ==========================================================

    def get(
        self,
        name: str | None,
    ) -> Skill | None:

        if not name:
            return None

        return self.registry.get(name)

    def has(
        self,
        name: str | None,
    ) -> bool:

        if not name:
            return False

        return self.registry.has(name)

    # ==========================================================
    # Capabilities
    # ==========================================================

    def find_by_capability(
        self,
        capability: str,
    ) -> list[Skill]:

        return self.registry.find_by_capability(
            capability,
        )

    def contains_capability(
        self,
        capability: str,
    ) -> bool:

        return self.registry.contains_capability(
            capability,
        )

    def capabilities(
        self,
    ) -> dict[str, tuple[str, ...]]:

        return self.registry.capabilities()

    # ==========================================================
    # Queries
    # ==========================================================

    def list(self) -> list[str]:

        return self.registry.list()

    def count(self) -> int:

        return self.registry.count()

    def loaded(self) -> list[str]:

        return self.loader.loaded()

    def aliases(self) -> dict[str, str]:

        return self.registry.aliases()

    def metadata(self) -> list[dict]:

        return self.registry.metadata()

    # ==========================================================
    # Lifecycle
    # ==========================================================

    def unregister(
        self,
        name: str,
    ) -> None:

        if not name:
            return

        self.registry.unregister(name)

    def clear(self) -> None:

        self.registry.clear()
