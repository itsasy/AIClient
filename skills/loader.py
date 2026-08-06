from __future__ import annotations

import importlib
import inspect
import logging

from skills.base import Skill
from skills.registry import SkillRegistry

logger = logging.getLogger(__name__)


class SkillLoader:
    """
    Descubrimiento y registro dinámico de Skills.

    Responsabilidades:

    - Importar módulos.
    - Detectar Skills.
    - Registrar factories.
    - Mantener catálogo cargado.

    No:

    - Ejecuta Skills.
    - Instancia Skills.
    - Gestiona resultados.
    """

    def __init__(
        self,
        registry: SkillRegistry,
    ):

        self.registry = registry

        self.loaded_modules: set[str] = set()

    # ======================================================
    # Module loading
    # ======================================================

    def load_module(
        self,
        module_path: str,
    ) -> None:

        if module_path in self.loaded_modules:

            logger.debug(
                "Módulo Skill ya cargado=%s",
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

        except Exception:

            logger.exception(
                "Error cargando módulo Skill=%s",
                module_path,
            )

    # ======================================================
    # Discovery
    # ======================================================

    def _register_from_module(
        self,
        module,
    ) -> None:

        for obj_name in dir(module):

            try:

                obj = getattr(
                    module,
                    obj_name,
                )

            except Exception:

                continue

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

            self._register_skill(
                obj,
            )

    # ======================================================
    # Registration
    # ======================================================

    def _register_skill(
        self,
        skill_class: type[Skill],
    ) -> None:

        name = getattr(
            skill_class,
            "name",
            None,
        )

        if not name:

            logger.warning(
                "Skill sin nombre ignorada=%s",
                skill_class,
            )

            return

        aliases = getattr(
            skill_class,
            "aliases",
            None,
        )

        try:

            self.registry.register(
                name=name,
                factory=skill_class,
                aliases=aliases,
            )

            logger.info(
                "Skill cargada=%s aliases=%s capabilities=%s",
                name,
                aliases,
                getattr(
                    skill_class,
                    "capabilities",
                    (),
                ),
            )

        except ValueError:

            logger.debug(
                "Skill ya registrada=%s",
                name,
            )

        except Exception:

            logger.exception(
                "Error registrando Skill=%s",
                name,
            )

    # ======================================================
    # Defaults
    # ======================================================

    def load_defaults(
        self,
    ) -> None:

        modules = [
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

        for module in modules:

            self.load_module(
                module,
            )
