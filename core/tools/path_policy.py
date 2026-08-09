from __future__ import annotations

from pathlib import Path
from typing import Optional

from core.config import Config


class PathPolicy:
    """
    Valida rutas de archivos para prevenir accesos no permitidos.

    Responsabilidades:
        - Verificar que la ruta esté dentro del proyecto.
        - Prevenir el uso de `..` para salir del proyecto.
        - Normalizar rutas relativas.
    """

    @staticmethod
    def normalize(path: str | Path) -> Path:
        """Convierte a Path y resuelve rutas relativas."""
        return Path(path).expanduser().resolve()

    @staticmethod
    def is_within_project(path: str | Path) -> bool:
        """Verifica que la ruta esté dentro del directorio del proyecto."""
        root = Config.TARGET_PROJECT_ROOT.resolve()
        target = PathPolicy.normalize(path)

        try:
            target.relative_to(root)
            return True
        except ValueError:
            return False

    @staticmethod
    def validate(path: str | Path) -> tuple[bool, Optional[str]]:
        """
        Valida la ruta y devuelve (ok, error_message).
        """
        if not path:
            return False, "La ruta está vacía."

        normalized = PathPolicy.normalize(path)

        if not PathPolicy.is_within_project(normalized):
            return False, f"La ruta '{normalized}' está fuera del proyecto."

        if ".." in str(normalized):
            return False, "La ruta contiene '..' que podría salir del proyecto."

        return True, None
