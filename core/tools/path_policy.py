from __future__ import annotations

from pathlib import Path
from typing import Optional

from core.config import Config


class PathPolicy:
    """Valida rutas para prevenir path traversal."""

    @staticmethod
    def project_root() -> Path:
        return Config.TARGET_PROJECT_ROOT.resolve()

    @staticmethod
    def normalize(path: str | Path) -> Path:
        return Path(path).expanduser().resolve()

    @staticmethod
    def is_within_project(path: str | Path) -> bool:
        root = PathPolicy.project_root()
        target = PathPolicy.normalize(path)
        try:
            target.relative_to(root)
            return True
        except ValueError:
            return False

    @staticmethod
    def validate(path: str | Path) -> tuple[bool, Optional[str]]:
        if path is None or (isinstance(path, str) and not str(path).strip()):
            return False, "La ruta está vacía."

        raw = str(path).strip()

        try:
            normalized = PathPolicy.normalize(raw)
        except Exception as exc:
            return False, f"Ruta inválida: {exc}"

        if not PathPolicy.is_within_project(normalized):
            return (
                False,
                f"La ruta '{raw}' resuelve fuera del proyecto "
                f"({normalized}). Path traversal bloqueado.",
            )

        if normalized == PathPolicy.project_root():
            return False, "No se puede usar el directorio raíz del proyecto como archivo."

        return True, None

    @staticmethod
    def safe_join(*parts: str) -> Path:
        root = PathPolicy.project_root()
        candidate = root.joinpath(*parts)
        ok, err = PathPolicy.validate(candidate)
        if not ok:
            raise ValueError(err or "Ruta insegura")
        return PathPolicy.normalize(candidate)
