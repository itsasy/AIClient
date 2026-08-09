from __future__ import annotations

import logging

from runtime.registry.skill_registry import SkillRegistry
from skills.base import Skill
from skills.loader import SkillLoader

logger = logging.getLogger(__name__)


class SkillManager:
    """
    Fachada central para la gestión de Skills.

    Responsabilidades:
        - Coordinar SkillLoader y SkillRegistry.
        - Cargar Skills.
        - Resolver Skills.
        - Consultar capacidades y metadata.
        - Exponer operaciones administrativas del sistema.

    No:
        - Ejecuta Skills.
        - Decide qué Skill debe ejecutarse.
        - Gestiona el lifecycle de ExecutionPlan.
        - Ejecuta Tools.
    """

    name = "skill_manager"

    def __init__(
        self,
        registry: SkillRegistry | None = None,
        loader: SkillLoader | None = None,
        auto_load: bool = True,
    ) -> None:
        self.registry = registry or SkillRegistry()

        self.loader = loader or SkillLoader(
            self.registry,
        )

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

        return self.registry.get(
            name,
        )

    def has(
        self,
        name: str | None,
    ) -> bool:
        if not name:
            return False

        return self.registry.has(
            name,
        )

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

    # ==========================================================
    # Registry queries
    # ==========================================================

    def list(self) -> list[str]:
        return self.registry.list()

    def count(self) -> int:
        return self.registry.count()

    def aliases(self) -> dict[str, str]:
        return self.registry.aliases()

    def metadata(self) -> list[dict]:
        return self.registry.metadata()

    def capabilities(
        self,
    ) -> dict[str, tuple[str, ...]]:
        return self.registry.capabilities()

    # ==========================================================
    # Loader state
    # ==========================================================

    def loaded(self) -> list[str]:
        """
        Skills descubiertas y cargadas por SkillLoader.

        El estado de carga pertenece al Loader, no al Registry.
        """
        return self.loader.loaded()

    def loader_stats(self) -> dict[str, int]:
        return self.loader.stats()

    # ==========================================================
    # Administration
    # ==========================================================

    def unregister(
        self,
        name: str,
    ) -> None:
        if not name:
            return

        self.registry.unregister(
            name,
        )

    def clear(self) -> None:
        """
        Limpia únicamente las Skills registradas.

        El estado interno del Loader se mantiene separado y
        puede reiniciarse mediante clear_state().
        """
        self.registry.clear()
