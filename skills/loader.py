from __future__ import annotations

import importlib
import inspect
import logging

from skills.base import Skill
from skills.registry import SkillRegistry

logger = logging.getLogger(__name__)


class SkillLoader:
    """
    Descubrimiento y registro de Skills.

    Responsabilidades:

    - Importar módulos.
    - Detectar clases Skill.
    - Validar implementaciones.
    - Registrarlas en SkillRegistry.
    - Mantener estado de carga.

    No:

    - Ejecuta Skills.
    - Instancia Skills.
    - Gestiona resultados.
    - Decide qué Skill utilizar.
    """

    DEFAULT_MODULES = [
        # Code
        "skills.code.analyze",
        "skills.code.executor",
        "skills.code.generate",
        "skills.code.project_analyzer",
        "skills.code.sandbox",
        # Documentation
        "skills.docs.readme",
        # Knowledge
        "skills.knowledge.ingest",
        # Migration
        "skills.migration.project_migrator",
        "skills.migration.refactor",
        # Projects
        "skills.projects.full_generator",
        "skills.projects.laravel",
        # Proposals
        "skills.proposals.generator",
        # Scraping
        "skills.scraping.integrations",
        "skills.scraping.job_scraper",
    ]

    def __init__(
        self,
        registry: SkillRegistry,
        modules: list[str] | None = None,
    ):

        self.registry = registry

        self.modules = modules or self.DEFAULT_MODULES.copy()

        self.loaded_modules: set[str] = set()

        self.errors: list[dict[str, str]] = []

    # ======================================================
    # Module loading
    # ======================================================

    def load_module(
        self,
        module_path: str,
    ) -> None:

        if module_path in self.loaded_modules:

            logger.debug(
                "Skill module ya cargado=%s",
                module_path,
            )

            return

        try:

            module = importlib.import_module(
                module_path,
            )

            self._register_from_module(
                module,
            )

            self.loaded_modules.add(
                module_path,
            )

        except Exception as exc:

            self.errors.append(
                {
                    "module": module_path,
                    "error": str(exc),
                }
            )

            logger.exception(
                "Error cargando Skill module=%s",
                module_path,
            )

    def _register_from_module(
        self,
        module,
    ) -> None:

        for attribute_name in dir(module):

            obj = getattr(
                module,
                attribute_name,
            )

            if not inspect.isclass(obj):

                continue

            if obj is Skill:

                continue

            if not issubclass(
                obj,
                Skill,
            ):

                continue

            if inspect.isabstract(obj):

                continue

            if obj.__module__ != module.__name__:

                continue

            skill_name = getattr(
                obj,
                "name",
                None,
            )

            if not skill_name:

                logger.warning(
                    "Skill sin nombre ignorada=%s",
                    obj,
                )

                continue

            if not hasattr(
                obj,
                "execute",
            ):

                logger.warning(
                    "Skill inválida sin execute=%s",
                    skill_name,
                )

                continue

            if self.registry.has(
                skill_name,
            ):

                logger.warning(
                    "Skill duplicada ignorada=%s",
                    skill_name,
                )

                continue

            self.registry.register(
                skill_name,
                obj,
            )

            logger.info(
                "Skill registrada=%s capabilities=%s",
                skill_name,
                getattr(
                    obj,
                    "capabilities",
                    (),
                ),
            )

    # ======================================================
    # Defaults
    # ======================================================

    def load_defaults(
        self,
    ) -> None:

        self.load_modules(
            self.modules,
        )

    def load_modules(
        self,
        modules: list[str],
    ) -> None:

        for module in modules:

            self.load_module(
                module,
            )

    # ======================================================
    # Information
    # ======================================================

    def get_errors(
        self,
    ) -> list[dict[str, str]]:

        return self.errors.copy()

    def get_loaded_modules(
        self,
    ) -> list[str]:

        return sorted(
            self.loaded_modules,
        )
