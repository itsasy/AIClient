import logging
import re

from llm.gemini import GeminiProvider
from llm.prompt_builder import PromptBuilder
from skills.manager import SkillManager


logger = logging.getLogger(__name__)


class LLMRouter:
    skill_manager = SkillManager()

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
                "project_name": query,
            }

        # Análisis de código explícito
        if re.search(
            r"\b(analiza|analizar|revisa|revisar)\b.*"
            r"\b(código|codigo|función|funcion|clase|archivo|módulo|modulo)\b",
            q,
        ):
            explicit_code_markers = (
                "def ",
                "class ",
                "import ",
                "return ",
                "```",
            )

            if any(marker in q for marker in explicit_code_markers):
                return "analyze", {
                    "code_snippet": query,
                }

        # Análisis del proyecto actual
        project_intent = re.search(
            r"\b(analiza|analizar|revisa|revisar|evalúa|evaluar|"
            r"inspecciona|inspeccionar|problemas|errores|deuda)\b",
            q,
        )

        project_reference = re.search(
            r"\b(proyecto|repo|repositorio|arquitectura|estructura|"
            r"código actual|codigo actual|mi código|mi codigo|"
            r"actualmente|sistema actual)\b",
            q,
        )

        if project_intent and project_reference:
            return "analyze_project", {}

        # Generación de código o proyectos
        if re.search(
            r"\b(crea|crear|genera|generar|implementa|implementar|escribe)\b.*"
            r"\b(función|funcion|clase|script|endpoint|código|codigo|proyecto)\b",
            q,
        ):
            return "code", {
                "task": query,
            }

        return None, None

    @staticmethod
    def generate(
        task: str,
        context=None,
        skill_name=None,
        skill_params=None,
    ) -> str:
        skill_result = LLMRouter._execute_skill(
            skill_name,
            skill_params,
        )

        prompt = PromptBuilder.build(
            task=task,
            context=context or {},
            skill_name=skill_name,
            skill_result=skill_result,
        )

        logger.debug("Prompt generado:\n%s", prompt)

        provider = GeminiProvider()
        return provider.generate(prompt)

    @staticmethod
    def _execute_skill(skill_name, skill_params=None):
        if not skill_name:
            return None

        logger.info("Ejecutando skill: %s", skill_name)

        return LLMRouter.skill_manager.execute(
            skill_name,
            **(skill_params or {}),
        )