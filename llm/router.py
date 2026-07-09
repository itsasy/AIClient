import re

from core.config import Config
from core.context_builder import ContextBuilder
from skills.manager import SkillManager


class LLMRouter:
    skill_manager = SkillManager()

    @staticmethod
    def detect_skill(query: str):
        if not query:
            return None, None

        q = query.lower()
        patterns = [
            ("readme", [r"\b(readme|read me|documentación|documenta|documentar)\b"]),
            (
                "analyze_project",
                [
                    r"\b(analiza(?:r)?(?: este| el)? proyecto|revisa(?:r)?(?: este| el)? proyecto|estándares|estructura del proyecto|estructura de carpetas|arquitectura|diseño)\b",
                    r"\b(analiza(?:r)? este repo|revisa(?:r)? este repo|analiza(?:r)? la arquitectura)\b",
                ],
            ),
            ("analyze", [r"\b(analiza(?:r)?(?: este| el)? código|revisa(?:r)?(?: este| el)? código|analiza(?:r)? el módulo|revisa(?:r)? el módulo|analiza(?:r)? el archivo|revisa(?:r)? el archivo)\b"]),
            ("code", [r"\b(genera(?:r)?|crea(?:r)?|implementa(?:r)?|función python|clase|script|snippet)\b"]),
        ]

        for skill_name, regexes in patterns:
            if any(re.search(pattern, q) for pattern in regexes):
                if skill_name == "readme":
                    return skill_name, {"project_name": query}
                if skill_name == "analyze_project":
                    return skill_name, {"project_path": str(Config.PROJECT_ROOT)}
                if skill_name == "code":
                    return skill_name, {"task": query}
                if skill_name == "analyze":
                    return skill_name, {"code_snippet": query}

        return None, None

    @staticmethod
    def _get_provider():
        try:
            from .gemini import GeminiProvider

            return GeminiProvider()
        except Exception:
            class FallbackProvider:
                def generate(self, prompt: str, **kwargs) -> str:
                    return "No se pudo contactar al proveedor LLM. Revisa la configuración de GEMINI_API_KEY."

            return FallbackProvider()

    @staticmethod
    def generate(prompt: str):
        builder = ContextBuilder()
        context_prompt = builder.build(prompt or "")
        skill_name, params = LLMRouter.detect_skill(context_prompt)

        provider = LLMRouter._get_provider()
        if skill_name:
            try:
                skill_result = LLMRouter.skill_manager.execute(skill_name, **params)
            except Exception as exc:
                skill_result = f"Error ejecutando skill '{skill_name}': {exc}"

            enriched_prompt = (
                f"{context_prompt}\n\n"
                f"[Skill activada: {skill_name}]\n"
                f"{skill_result}"
            )
            return provider.generate(enriched_prompt)

        return provider.generate(context_prompt)

