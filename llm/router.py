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
            return "readme", {"project_name": query}

        if re.search(r"\b(analiza|revisa|evalúa|inspecciona|problemas)\b", q) and re.search(r"\b(mi|este|actual|actualmente|proyecto|repo|arquitectura|estructura|código|codigo)\b", q):
            if re.search(r"\b(problemas|errores|deuda|arquitectura|estructura|proyecto|repo|actual|actualmente)\b", q) and not re.search(r"\b(función|funcion|clase|archivo|módulo|modulo|script|endpoint)\b", q):
                return "analyze_project", {}

        if re.search(r"\b(analiza|revisa)\b.*\b(código|codigo|función|funcion|clase|archivo|módulo|modulo)\b", q):
            if re.search(r"\b(este|mi|actual|actualmente|proyecto|repo)\b", q) and not re.search(r"\b(def |class |import |return |if |for |while |try:|except |snippet|archivo|función|funcion|clase|módulo|modulo)\b", q) and "analiza este código" in q:
                return None, None
            return "analyze", {"code_snippet": query}

        if re.search(r"\b(crea|genera|implementa|escribe)\b.*\b(función|funcion|clase|script|endpoint|proyecto)\b", q):
            return "code", {"task": query}

        return None, None

    @staticmethod
    def _provider():

        from llm.gemini import GeminiProvider

        return GeminiProvider()

    @staticmethod
    def generate(task,
                 context="",
                 skill_name=None,
                 skill_params=None):
        provider = LLMRouter._provider()
        skill_result = LLMRouter._execute_skill(skill_name, skill_params)

        prompt = PromptBuilder.build(
            task=task,
            context=context,
            skill_name=skill_name,
            skill_result=skill_result
        )

        logger.debug(prompt)
        return provider.generate(prompt)

    @staticmethod
    def _execute_skill(skill_name, skill_params=None):
        if not skill_name:
            return None

        logger.info("Ejecutando skill %s", skill_name)
        return LLMRouter.skill_manager.execute(skill_name, **(skill_params or {}))