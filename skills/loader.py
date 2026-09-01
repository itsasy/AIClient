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

    Carga módulos, descubre clases Skill y las registra
    automáticamente en SkillRegistry.
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
        "skills.projects.new_project",
        "skills.projects.laravel",
        "skills.proposals.generator",
        "skills.scraping.integrations",
        "skills.scraping.job_scraper",
        "skills.files.write_file",
        "skills.projects.create_project",
        "skills.projects.scaffold_module",
        "skills.projects.scaffold_ui_shell",
        "skills.audit.security_audit",
        "skills.audit.performance_audit",
        "skills.audit.quality_audit",
        "skills.audit.architecture_audit",
        "skills.system.shell",
    )

    def __init__(
        self,
        registry: SkillRegistry,
    ) -> None:

        self.registry = registry

        self.loaded_modules: set[str] = set()
        self.failed_modules: set[str] = set()
        self.loaded_skills: set[str] = set()

    # ======================================================
    # Module loading
    # ======================================================

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

            logger.info(
                "Skill module cargado=%s",
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

        result: dict[str, bool] = {}

        for module in modules:

            result[module] = self.load_module(
                module,
            )

        return result

    # ======================================================
    # Discovery
    # ======================================================

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

    # ======================================================
    # Registration
    # ======================================================

    def _register_skill(
        self,
        skill_class: type[Skill],
    ) -> None:

        errors = skill_class.validate_definition()

        if errors:

            logger.warning(
                "Skill inválida=%s errores=%s",
                skill_class.__name__,
                errors,
            )

            return

        name = SkillRegistry.normalize(
            skill_class.name,
        )

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

            self.loaded_skills.add(
                name,
            )

            logger.info(
                "Skill registrada=%s",
                name,
            )

        except ValueError as exc:

            logger.debug(
                "Skill ya registrada=%s (%s)",
                name,
                exc,
            )

        except Exception:

            logger.exception(
                "Error registrando Skill=%s",
                name,
            )

    # ======================================================
    # Default loading
    # ======================================================

    def load_defaults(
        self,
    ) -> dict[str, bool]:

        return self.load_modules(
            self.DEFAULT_MODULES,
        )

    # ======================================================
    # Inspection
    # ======================================================

    def stats(
        self,
    ) -> dict[str, int]:

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

    def loaded(
        self,
    ) -> list[str]:

        return sorted(
            self.loaded_skills,
        )

    # ======================================================
    # Reset
    # ======================================================

    def clear_state(
        self,
    ) -> None:

        self.loaded_modules.clear()
        self.failed_modules.clear()
        self.loaded_skills.clear()
