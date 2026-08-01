import os
from typing import Dict


import logging

logger = logging.getLogger(__name__)


class GentlemanSkills:
    def __init__(self):
        self.skills_dir = self._find_skills_dir()
        self.skills: Dict[str, str] = {}
        if self.skills_dir:
            logger.info(f"📂 Skills dir encontrado: {self.skills_dir}")
            self._load_all()
            logger.info(f"✅ Skills cargadas: {list(self.skills.keys())}")
        else:
            logger.warning("❌ No se encontraron skills.")

    def _load_all(self):
        for md_file in self.skills_dir.rglob("SKILL.md"):
            skill_name = md_file.parent.name
            content = md_file.read_text(encoding="utf-8", errors="ignore")
            self.skills[skill_name] = content
            logger.info(f"📄 Skill cargada: {skill_name}")
