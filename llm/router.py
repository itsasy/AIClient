import logging
import re

from llm.prompt_builder import PromptBuilder
from skills.manager import SkillManager

logger = logging.getLogger(__name__)


class LLMRouter:

    skill_manager = SkillManager()

    @staticmethod
    def detect_skill(query: str):

        if not query:
            return None, None

        q = query.lower()

        if re.search(r"\b(crea|genera|haz)\b.*\b(readme|documentación|documentacion)\b", q):
            return "readme", {
                "project_name": query
            }

        if re.search(
            r"\b(analiza|revisa|evalúa|inspecciona)\b.*\b(proyecto|repo|arquitectura|estructura)\b",
            q
        ):
            return "analyze_project", {}

        if re.search(
            r"\b(analiza|revisa)\b.*\b(código|codigo|función|funcion|clase|archivo)\b",
            q
        ):
            return "analyze", {
                "code_snippet": query
            }

        if re.search(
            r"\b(crea|genera|implementa|escribe)\b.*\b(función|funcion|clase|script|endpoint|proyecto)\b",
            q
        ):
            return "code", {
                "task": query
            }

        return None, None

    @staticmethod
    def _provider():

        from llm.gemini import GeminiProvider

        return GeminiProvider()

    @staticmethod
    def generate(task,
                 context,
                 skill_name=None,
                 skill_params=None):

        provider = LLMRouter._provider()

        skill_result = None

        if skill_name:

            logger.info("Ejecutando skill %s", skill_name)

            skill_result = LLMRouter.skill_manager.execute(
                skill_name,
                **(skill_params or {})
            )

        prompt = PromptBuilder.build(
            task=task,
            context=context,
            skill_name=skill_name,
            skill_result=skill_result
        )

        logger.debug(prompt)

        return provider.generate(prompt)