from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class ProjectFile:
    """
    Representación normalizada de un archivo de proyecto.

    Es la única representación de archivo utilizada por
    ProjectSnapshot y ProjectIndex.
    """

    path: str
    content: str | None = None

    filename: str = ""
    extension: str = ""
    size: int = 0
    lines: int = 0
    language: str | None = None

    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.path = str(self.path)

        path = Path(self.path)

        if not self.filename:
            self.filename = path.name

        if not self.extension:
            self.extension = path.suffix.lower()

        if self.content is not None:
            self.size = len(self.content)
            self.lines = self.content.count("\n") + (1 if self.content else 0)

    @property
    def directory(self) -> str:
        return str(Path(self.path).parent)

    def to_dict(
        self,
        include_content: bool = True,
    ) -> dict[str, Any]:
        data = {
            "path": self.path,
            "filename": self.filename,
            "extension": self.extension,
            "size": self.size,
            "lines": self.lines,
            "language": self.language,
            "metadata": dict(self.metadata),
        }

        if include_content:
            data["content"] = self.content

        return data

    def to_architecture_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "filename": self.filename,
            "extension": self.extension,
            "language": self.language,
            "size": self.size,
            "lines": self.lines,
            "content": self.content,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> ProjectFile:
        return cls(
            path=data["path"],
            content=data.get("content"),
            filename=data.get("filename", ""),
            extension=data.get("extension", ""),
            size=data.get("size", 0),
            lines=data.get("lines", 0),
            language=data.get("language"),
            metadata=data.get("metadata", {}),
        )
