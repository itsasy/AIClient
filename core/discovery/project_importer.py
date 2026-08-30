import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

class ProjectImporter:
    """
    Lee y resume el contenido de un template o repositorio semilla
    para inyectarlo en el contexto.
    """
    
    def __init__(self, ignore_patterns: list[str] | None = None) -> None:
        self.ignore_patterns = ignore_patterns or [
            ".git", "node_modules", "__pycache__", "venv", ".env", ".pytest_cache"
        ]

    def _should_ignore(self, path: Path) -> bool:
        for p in path.parts:
            if p in self.ignore_patterns:
                return True
        if path.name.startswith(".") and path.name != ".gitignore":
            return True
        return False

    def import_template(self, template_path: Path) -> dict[str, Any]:
        """
        Escanea el directorio y devuelve una representación estructurada.
        """
        structure = []
        files = {}

        if not template_path.exists() or not template_path.is_dir():
            return {"error": "Template path no encontrado."}

        for path in template_path.rglob("*"):
            if self._should_ignore(path):
                continue
            
            rel_path = path.relative_to(template_path).as_posix()
            
            if path.is_dir():
                structure.append(f"{rel_path}/")
            else:
                structure.append(rel_path)
                try:
                    # Leemos solo archivos pequeños de texto
                    if path.stat().st_size < 50000:
                        content = path.read_text(encoding="utf-8")
                        files[rel_path] = content
                except Exception:
                    pass

        return {
            "name": template_path.name,
            "structure": sorted(structure),
            "files": files
        }
