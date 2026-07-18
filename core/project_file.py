from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class ProjectFile:
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
        return {"path": self.path, "content": self.content}

    @classmethod
    def from_dict(cls, data: dict) -> ProjectFile:
        return cls(path=data["path"], content=data["content"])
