from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class ProjectFile:
    """
    Representa un archivo del proyecto.

    Este objeto será la unidad mínima utilizada por el
    ContextRetriever, ProjectIndex y futuras búsquedas
    semánticas.
    """

    path: str
    content: str

    @property
    def extension(self) -> str:
        return Path(self.path).suffix.lower()

    @property
    def filename(self) -> str:
        return Path(self.path).name

    @property
    def directory(self) -> str:
        return str(Path(self.path).parent)

    @property
    def size(self) -> int:
        return len(self.content)

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "filename": self.filename,
            "directory": self.directory,
            "extension": self.extension,
            "size": self.size,
        }