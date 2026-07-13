import logging
import re

from llm.prompt_builder import PromptBuilder
from llm.provider_manager import ProviderManager
from skills.manager import SkillManager

logger = logging.getLogger(__name__)


class LLMRouter:
    skill_manager = SkillManager()
    provider_manager = ProviderManager()

    @staticmethod
    def detect_skill(query: str):
        if not query:
            return None, None

        q = query.lower().strip()

        # README
        if re.search(
            r"\b(crea|crear|genera|generar|haz)\b.*"
            r"\b(readme|documentación|documentacion)\b",
            q,
        ):
            return "readme", {
                "request": query,
            }

        # Análisis explícito de código
        if re.search(
            r"\b(analiza|analizar|revisa|revisar)\b.*"
            r"\b("
            r"código|codigo|función|funcion|"
            r"clase|archivo|módulo|modulo"
            r")\b",
            q,
        ):
            explicit_code_markers = (
                "def ",
                "class ",
                "import ",
                "return ",
                "```",
            )

            if any(
                marker in q
                for marker in explicit_code_markers
            ):
                return "analyze", {
                    "code_snippet": query,
                }

        # Análisis del proyecto actual
        project_intent = re.search(
            r"\b("
            r"analiza|analizar|revisa|revisar|"
            r"evalúa|evaluar|inspecciona|inspeccionar|"
            r"problemas|errores|deuda"
            r")\b",
            q,
        )

        project_reference = re.search(
            r"\b("
            r"proyecto|repo|repositorio|"
            r"arquitectura|estructura|"
            r"código actual|codigo actual|"
            r"mi código|mi codigo|"
            r"actualmente|sistema actual"
            r")\b",
            q,
        )

        if project_intent and project_reference:
            return "analyze_project", {}

        # Generación de código o proyectos
        if re.search(
            r"\b("
            r"crea|crear|genera|generar|"
            r"implementa|implementar|escribe"
            r")\b.*"
            r"\b("
            r"función|funcion|clase|script|"
            r"endpoint|código|codigo|proyecto"
            r")\b",
            q,
        ):
            return "code", {
                "task": query,
            }

        return None, None

    @classmethod
    def generate(
        cls,
        task: str,
        context=None,
        skill_name=None,
        skill_params=None,
        provider_name: str | None = None,
        **kwargs,
    ) -> str:
        skill_result = cls._execute_skill(
            skill_name,
            skill_params,
        )

        prompt = PromptBuilder.build(
            task=task,
            context=context or {},
            skill_name=skill_name,
            skill_result=skill_result,
        )

        logger.debug(
            "Prompt generado para la tarea."
        )

        return cls.provider_manager.generate(
            prompt=prompt,
            provider_name=provider_name,
            **kwargs,
        )

    @classmethod
    def _execute_skill(
        cls,
        skill_name,
        skill_params=None,
    ):
        if not skill_name:
            return None

        logger.info(
            "Ejecutando skill: %s",
            skill_name,
        )

        return cls.skill_manager.execute(
            skill_name,
            **(skill_params or {}),
        )