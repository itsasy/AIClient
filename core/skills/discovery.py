from pathlib import Path
from typing import List
import os
import re
from core.skills.models import Skill

class SkillDiscovery:
    def __init__(self, search_paths: List[str]):
        self.search_paths = search_paths
        
    def discover(self) -> List[Skill]:
        skills = []
        for path_str in self.search_paths:
            base_path = Path(path_str).expanduser()
            if not base_path.exists() or not base_path.is_dir():
                continue
                
            for child in base_path.iterdir():
                if child.is_dir():
                    skill_md = child / "SKILL.md"
                    if skill_md.exists():
                        skills.append(self._parse_skill_md(child, skill_md))
        return skills
        
    def _parse_skill_md(self, skill_dir: Path, md_path: Path) -> Skill:
        # A rudimentary parser. Real implementation would parse YAML frontmatter.
        content = md_path.read_text(encoding="utf-8", errors="ignore")
        name = skill_dir.name
        capabilities = []
        
        # Heuristics for capabilities if not formally defined
        if "move_files" in content or "relocate" in content:
            capabilities.append("move_files")
        if "inspect" in content or "boundary" in content:
            capabilities.append("inspect_boundary")
        if "rewrite" in content or "import" in content:
            capabilities.append("rewrite_imports")
        if "tests" in content or "pytest" in content:
            capabilities.append("run_tests")
            
        mutating = "move_files" in capabilities or "rewrite_imports" in capabilities
        
        return Skill(
            name=name,
            location=str(skill_dir),
            description=f"Skill discovered at {skill_dir}",
            capabilities=capabilities,
            mutating=mutating,
            available=True # Assuming available if present
        )
