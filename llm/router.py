from .gemini import GeminiProvider
from skills.manager import SkillManager

class LLMRouter:
    skill_manager = SkillManager()
    
    @staticmethod
    def detect_skill(query: str):
        q = query.lower()
        if any(k in q for k in ["readme", "read me", "documentación"]):
            return "readme", {"project_name": query}
        if any(k in q for k in ["analiza este proyecto", "estándares", "estructura del proyecto", "arquitectura"]):
            return "analyze_project", {"project_path": "."}
        if any(k in q for k in ["genera", "crea código", "función python", "clase"]):
            return "code", {"task": query}
        if "analiza este código" in q or "revisa este código" in q:
            return "analyze", {"code_snippet": query}
        return None, None
    
    @staticmethod
    def generate(prompt: str):
        skill_name, params = LLMRouter.detect_skill(prompt)
        if skill_name:
            result = LLMRouter.skill_manager.execute(skill_name, **params)
            return f"[Skill: {skill_name}]\n{result}"
        
        # LLM normal
        provider = GeminiProvider()
        return provider.generate(prompt)
