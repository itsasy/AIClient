from __future__ import annotations

import logging

from skills.registry import SkillRegistry
from skills.loader import SkillLoader
from skills.base import Skill

logger = logging.getLogger(__name__)


class SkillManager:
    """
    Resolver central de Skills.

    Responsabilidades:

    - Mantener catálogo.
    - Resolver skills.
    - Gestionar carga.

    No:

    - Ejecuta skills.
    - Maneja retries.
    - Normaliza resultados.

    La ejecución pertenece a SkillRuntime.
    """

    name = "skill_manager"

    def __init__(
        self,
        registry: SkillRegistry | None = None,
        loader: SkillLoader | None = None,
        auto_load: bool = True,
    ):

        self.registry = registry or SkillRegistry()

        self.loader = loader or SkillLoader(
            self.registry,
        )

        self.loaded_defaults = False

        if auto_load:
            self.load_defaults()

    # ==================================================
    # Loading
    # ==================================================

    def load_defaults(
        self,
    ) -> None:

        if self.loaded_defaults:
            return

        try:

            self.loader.load_defaults()

            self.loaded_defaults = True

            logger.info(
                "Skills por defecto cargadas",
            )

        except Exception:

            logger.exception(
                "Error cargando skills por defecto",
            )

    def load_module(
        self,
        module_path: str,
    ) -> None:

        if not module_path:
            return

        try:

            self.loader.load_module(
                module_path,
            )

            logger.info(
                "Skill module cargado=%s",
                module_path,
            )

        except Exception:

            logger.exception(
                "Error cargando skill module=%s",
                module_path,
            )

    def reload(
        self,
    ) -> None:

        self.clear()

        self.loaded_defaults = False

        self.load_defaults()

    # ==================================================
    # Resolution
    # ==================================================

    def get(
        self,
        name: str | None,
    ) -> Skill | None:

        if not name:
            return None

        try:

            return self.registry.get(
                name.strip(),
            )

        except Exception:

            logger.exception(
                "Error resolviendo skill=%s",
                name,
            )

            return None

    def has(
        self,
        name: str | None,
    ) -> bool:

        if not name:
            return False

        try:

            return self.registry.has(
                name.strip(),
            )

        except Exception:

            logger.exception(
                "Error comprobando skill=%s",
                name,
            )

            return False

    # ==================================================
    # Information
    # ==================================================

    def list(
        self,
    ) -> list[str]:

        return self.registry.list()

    def loaded(
        self,
    ) -> list[str]:

        return self.registry.loaded()

    def aliases(
        self,
    ) -> dict[str, str]:

        return self.registry.aliases()

    def metadata(
        self,
    ) -> list[dict]:

        return self.registry.metadata()

    def capabilities(
        self,
    ) -> dict[str, tuple[str, ...]]:

        result: dict[str, tuple[str, ...]] = {}

        for name in self.list():

            skill = self.get(
                name,
            )

            if skill:

                result[name] = skill.capabilities

        return result

    # ==================================================
    # Management
    # ==================================================

    def unregister(
        self,
        name: str,
    ) -> None:

        if not name:
            return

        try:

            self.registry.unregister(
                name.strip(),
            )

        except Exception:

            logger.exception(
                "Error eliminando skill=%s",
                name,
            )

    def clear(
        self,
    ) -> None:

        self.registry.clear()
