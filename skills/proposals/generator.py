from skills.base import Skill
from llm.router import LLMRouter


class ProposalGeneratorSkill(Skill):
    name = "generate_proposal"
    description = "Genera propuestas para freelance o LinkedIn"

    def execute(self, job_description: str, mode: str = "freelance", **kwargs):
        prompt = f"""Genera una propuesta profesional para:

Plataforma: {mode}
Descripción del trabajo:
{job_description}

Instrucciones:
- Entiende el dolor del cliente
- Propón solución clara
- Incluye precio estimado (si freelance)
- Destaca experiencia relevante
- Llamado a acción

Sé profesional y convincente."""
        return LLMRouter.generate(prompt)
