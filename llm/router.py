import logging
import re

from skills.manager import SkillManager

logger = logging.getLogger(__name__)


class LLMRouter:
    skill_manager = SkillManager()

    @staticmethod
    def detect_skill(query: str):
        if not query:
            return None, None

        q = query.lower()

        if re.search(r"\b(crea|genera|haz)\b.*\b(readme|read me|documentación|documentacion)\b", q):
            logger.info("Skill detectada: readme")
            return "readme", {"project_name": query}

        if re.search(r"\b(analiza|revisa|problemas|bugs|code smells)\b.*\b(proyecto|repo|arquitectura|estructura|estándares|diseño)\b", q):
            logger.info("Skill detectada: analyze_project")
            return "analyze_project", {"project_path": "."}

        if re.search(r"\b(analiza|revisa|problemas)\b.*\b(código|codigo|función|funcion|clase|archivo)\b", q):
            logger.info("Skill detectada: analyze")
            return "analyze", {"code_snippet": query}

        if re.search(r"\b(crea|genera|implementa|escribe)\b.*\b(función|funcion|clase|script|código|codigo|endpoint)\b", q):
            logger.info("Skill detectada: code")
            return "code", {"task": query}

        logger.debug("No se detectó skill para: %s", query)
        return None, None

    @staticmethod
    def _provider():
        from .gemini import GeminiProvider

        return GeminiProvider()

    @staticmethod
    def generate(task: str, context: str = "", skill_name=None, skill_params=None):
        provider = LLMRouter._provider()

        if skill_name and skill_params is not None:
            try:
                skill_result = LLMRouter.skill_manager.execute(skill_name, **skill_params)
                prompt = f"""Skill activada: {skill_name}
Resultado de skill:
{skill_result}

Consulta original: {task}

Contexto adicional: {context[:800]}

Responde usando la skill como base principal."""
            except Exception as exc:
                logger.exception("Error ejecutando la skill %s", skill_name)
                prompt = f"Error en skill {skill_name}: {exc}\nConsulta: {task}"
        else:
            prompt = f"""Consulta: {task}

Contexto:
{context[:1500]}"""

        return provider.generate(prompt)

