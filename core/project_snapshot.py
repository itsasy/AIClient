from __future__ import annotations

from dataclasses import dataclass, field
from core.project_file import ProjectFile


@dataclass(slots=True)
class ProjectSnapshot:
    root: str
    files: list[ProjectFile] = field(default_factory=list)

    def add_file(self, path: str, content: str) -> None:
        self.files.append(ProjectFile(path=path, content=content))

    @property
    def file_count(self) -> int:
        return len(self.files)

    def find_by_extension(self, extension: str) -> list[ProjectFile]:
        extension = extension.lower()
        return [f for f in self.files if f.extension == extension]

    def find_by_name(self, name: str) -> list[ProjectFile]:
        name = name.lower()
        return [f for f in self.files if name in f.filename.lower()]

    def find_by_directory(self, directory: str) -> list[ProjectFile]:
        directory = directory.lower()
        return [f for f in self.files if directory in f.directory.lower()]

    def summary(self) -> dict:
        extensions: dict[str, int] = {}
        for f in self.files:
            extensions[f.extension] = extensions.get(f.extension, 0) + 1
        return {"root": self.root, "files": self.file_count, "extensions": extensions}

    def to_prompt(self) -> str:
        lines = [
            f"Proyecto: {self.root}",
            "",
            f"Archivos inspeccionados: {self.file_count}",
            "",
        ]
        for f in self.files:
            lines.append(f"# {f.path}")
            lines.append(f.content)
            lines.append("")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "root": self.root,
            "files": [f.to_dict() for f in self.files],
        }

    @classmethod
    def from_dict(cls, data: dict) -> ProjectSnapshot:
        snapshot = cls(root=data["root"])
        for f_data in data.get("files", []):
            snapshot.files.append(ProjectFile.from_dict(f_data))
        return snapshot
