import os
import logging
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class GentlemanSkills:
    """
    Carga skills de Gentleman-Programming desde el sistema de archivos.
    Busca en ~/.engram/skills/, ~/.claude/skills/, etc.
    """

    def __init__(self):
        self.skills_dir = self._find_skills_dir()
        self.skills: Dict[str, str] = {}
        if self.skills_dir:
            logger.info(f"📂 Skills dir encontrado: {self.skills_dir}")
            self._load_all()
            logger.info(f"✅ Skills cargadas: {list(self.skills.keys())}")
        else:
            logger.warning("❌ No se encontraron skills de Gentleman en ninguna ruta.")

    def _find_skills_dir(self) -> Optional[Path]:
        """Busca el directorio de skills en las rutas típicas."""
        candidates = [
            Path.home() / ".engram" / "skills",
            Path.home() / ".claude" / "skills",
            Path.home() / ".codex" / "skills",
            Path.home() / ".gentleman" / "skills",
        ]
        for path in candidates:
            if path.exists():
                logger.info(f"✅ Skills encontradas en: {path}")
                return path
        return None

    def _load_all(self):
        """Recorre recursivamente todas las carpetas buscando SKILL.md."""
        for md_file in self.skills_dir.rglob("SKILL.md"):
            skill_name = md_file.parent.name
            try:
                content = md_file.read_text(encoding="utf-8", errors="ignore")
                self.skills[skill_name] = content
                logger.info(f"📄 Skill cargada: {skill_name}")
            except Exception as e:
                logger.warning(f"Error cargando {md_file}: {e}")

    def get_skill(self, name: str) -> Optional[str]:
        """Devuelve el contenido de una skill por su nombre."""
        return self.skills.get(name)

    def find_relevant(self, query: str) -> List[str]:
        """Devuelve nombres de skills que podrían ser relevantes para la consulta."""
        query_lower = query.lower()
        relevant = []
        for name in self.skills.keys():
            # Dividir el nombre en palabras (ej. "react-19" → ["react", "19"])
            keywords = name.replace("-", " ").split()
            if any(k in query_lower for k in keywords):
                relevant.append(name)
        # Ordenar por relevancia (las que coinciden con más palabras primero)
        relevant.sort(
            key=lambda n: sum(1 for k in n.replace("-", " ").split() if k in query_lower),
            reverse=True,
        )
        return relevant[:3]  # máximo 3 skills para no saturar el contexto
