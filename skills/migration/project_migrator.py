from skills.base import Skill
from core.project_inspector import ProjectInspector
from llm.router import LLMRouter


class ProjectMigratorSkill(Skill):
    name = "migrate_project"
    description = "Migra proyecto antiguo a estándares modernos"

    def execute(self, old_project_path: str = ".", new_standards: str = "", **kwargs):
        inspector = ProjectInspector()
        snapshot = inspector.inspect()

        prompt = f"""Migra este proyecto antiguo a estándares modernos:

Snapshot del proyecto antiguo:
{snapshot}

Estándares nuevos:
{new_standards or "Laravel 11, Docker, Sanctum, buenas prácticas modernas, arquitectura limpia"}

Proporciona:
1. Estructura recomendada
2. Cambios clave
3. Código migrado de archivos principales
4. Comandos de migración"""
        return LLMRouter.generate(prompt)
