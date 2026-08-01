import os
from pathlib import Path
from typing import Dict, List, Optional


class GentlemanSkills:
    def __init__(self):
        self.skills_dir = self._find_skills_dir()
        self.skills: Dict[str, str] = {}
        if self.skills_dir:
            self._load_all()

    def _find_skills_dir(self) -> Optional[Path]:
        candidates = [
            Path.home() / ".engram" / "skills",
            Path.home() / ".claude" / "skills",
            Path.home() / ".codex" / "skills",
            Path.home() / ".gentleman" / "skills",
        ]
        for path in candidates:
            if path.exists():
                return path
        return None

    def _load_all(self):
        for md_file in self.skills_dir.rglob("SKILL.md"):
            skill_name = md_file.parent.name
            content = md_file.read_text(encoding="utf-8", errors="ignore")
            self.skills[skill_name] = content

    def get_skill(self, name: str) -> Optional[str]:
        return self.skills.get(name)

    def find_relevant(self, query: str) -> List[str]:
        query_lower = query.lower()
        relevant = []
        for name in self.skills.keys():
            keywords = name.replace("-", " ").split()
            if any(k in query_lower for k in keywords):
                relevant.append(name)
        # Ordenar por relevancia (las que coinciden con más palabras primero)
        relevant.sort(
            key=lambda n: sum(1 for k in n.replace("-", " ").split() if k in query_lower),
            reverse=True,
        )
        return relevant[:3]  # máximo 3 skills para no saturar el contexto
