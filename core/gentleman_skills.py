import os
from pathlib import Path


class GentlemanSkills:
    def __init__(self):
        # Buscar skills en los directorios típicos
        self.skills_dir = Path.home() / ".engram" / "skills"
        if not self.skills_dir.exists():
            # Fallback a .claude/skills
            self.skills_dir = Path.home() / ".claude" / "skills"
        self.skills = self._load_all()

    def _load_all(self):
        skills = {}
        for md_file in self.skills_dir.rglob("SKILL.md"):
            content = md_file.read_text(encoding="utf-8")
            # Extraer nombre de la carpeta (ej. react-19)
            skill_name = md_file.parent.name
            skills[skill_name] = content
        return skills

    def get_skill(self, name: str) -> str | None:
        return self.skills.get(name)

    def find_relevant(self, query: str) -> list[str]:
        """Devuelve nombres de skills que podrían ser relevantes para la consulta."""
        query_lower = query.lower()
        relevant = []
        for name in self.skills.keys():
            # Detectar coincidencias simples (React, Tailwind, etc.)
            keywords = name.replace("-", " ").split()
            if any(k in query_lower for k in keywords):
                relevant.append(name)
        return relevant
