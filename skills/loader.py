from __future__ import annotations

import importlib
import inspect
import logging

from skills.base import Skill

from runtime.registry.skill_registry import SkillRegistry

logger = logging.getLogger(__name__)


class SkillLoader:
    """
    Descubridor dinámico de Skills.

    Responsabilidades:

    - Importar módulos.
    - Detectar clases Skill.
    - Registrar clases.

    No:

    - Ejecuta Skills.
    - Decide qué Skill usar.
    - Gestiona resultados.
    """

    DEFAULT_MODULES = (
        "skills.code.analyze",
        "skills.code.executor",
        "skills.code.generate",
        "skills.code.project_analyzer",
        "skills.code.sandbox",
        "skills.docs.readme",
        "skills.knowledge.ingest",
        "skills.migration.project_migrator",
        "skills.migration.refactor",
        "skills.projects.full_generator",
        "skills.projects.laravel",
        "skills.proposals.generator",
        "skills.scraping.integrations",
        "skills.scraping.job_scraper",
    )

    def __init__(
        self,
        registry: SkillRegistry,
    ) -> None:

        self.registry = registry

        self.loaded_modules: set[str] = set()

        self.failed_modules: set[str] = set()

        self.loaded_skills: set[str] = set()

    # ==================================================
    # Loading
    # ==================================================

    def load_module(
        self,
        module_path: str,
    ) -> bool:

        if not module_path:

            return False

        if module_path in self.loaded_modules:

            return True

        try:

            module = importlib.import_module(
                module_path,
            )

            self._discover_module(
                module,
            )

            self.loaded_modules.add(
                module_path,
            )

            return True

        except Exception:

            self.failed_modules.add(
                module_path,
            )

            logger.exception(
                "Error cargando módulo Skill=%s",
                module_path,
            )

            return False

    def load_modules(
        self,
        modules: list[str] | tuple[str, ...],
    ) -> dict[str, bool]:

        result = {}

        for module in modules:

            result[module] = self.load_module(
                module,
            )

        return result

    # ==================================================
    # Discovery
    # ==================================================

    def _discover_module(
        self,
        module,
    ) -> None:

        for _, obj in inspect.getmembers(
            module,
            inspect.isclass,
        ):

            if obj is Skill:

                continue

            if not issubclass(
                obj,
                Skill,
            ):

                continue

            if inspect.isabstract(
                obj,
            ):

                continue

            if obj.__module__ != module.__name__:

                continue

            self._register_skill(
                obj,
            )

    # ==================================================
    # Registration
    # ==================================================

    def _register_skill(
        self,
        skill_class: type[Skill],
    ) -> None:

        errors = skill_class.validate_definition()

        if errors:

            logger.warning(
                "Skill inválida %s: %s",
                skill_class,
                errors,
            )

            return

        try:

            self.registry.register(
                skill_class,
            )

            self.loaded_skills.add(
                skill_class.name,
            )

            logger.info(
                "Skill registrada=%s",
                skill_class.name,
            )

        except ValueError:

            logger.debug(
                "Skill ya registrada=%s",
                skill_class.name,
            )

        except Exception:

            logger.exception(
                "Error registrando Skill=%s",
                skill_class.name,
            )

    # ==================================================
    # Defaults
    # ==================================================

    def load_defaults(
        self,
    ) -> dict[str, bool]:

        return self.load_modules(
            self.DEFAULT_MODULES,
        )

    # ==================================================
    # Information
    # ==================================================

    @property
    def loaded_count(
        self,
    ) -> int:

        return len(
            self.loaded_modules,
        )

    def stats(
        self,
    ) -> dict:

        return {
            "modules": len(
                self.loaded_modules,
            ),
            "failed_modules": len(
                self.failed_modules,
            ),
            "skills": len(
                self.loaded_skills,
            ),
        }

    # ==================================================
    # Management
    # ==================================================

    def clear_state(
        self,
    ) -> None:

        self.loaded_modules.clear()

        self.failed_modules.clear()

        self.loaded_skills.clear()
