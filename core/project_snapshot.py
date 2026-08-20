from __future__ import annotations

import json

from dataclasses import dataclass, field
from typing import Any

from core.project_file import ProjectFile


@dataclass(slots=True)
class ProjectDirectory:
    path: str
    name: str
    files_count: int = 0
    directories_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "name": self.name,
            "files_count": self.files_count,
            "directories_count": self.directories_count,
            "metadata": dict(self.metadata),
        }


@dataclass(slots=True)
class ProjectSnapshot:
    """
    Snapshot estructural de un proyecto.

    Es una representación interna del proyecto.
    No equivale automáticamente al contexto enviado al LLM.
    """

    project_name: str
    root_path: str = ""

    files: list[ProjectFile] = field(default_factory=list)
    directories: list[ProjectDirectory] = field(default_factory=list)

    languages: dict[str, int] = field(default_factory=dict)
    extensions: dict[str, int] = field(default_factory=dict)

    metadata: dict[str, Any] = field(default_factory=dict)
    generated_at: str | None = None

    @property
    def file_count(self) -> int:
        return len(self.files)

    @property
    def directory_count(self) -> int:
        return len(self.directories)

    def add_file(
        self,
        path: str,
        content: str | None = None,
        **kwargs: Any,
    ) -> ProjectFile:

        file = ProjectFile(
            path=path,
            content=content,
            **kwargs,
        )

        self.files.append(file)

        extension = file.extension
        if extension:
            self.extensions[extension] = self.extensions.get(extension, 0) + 1

        if file.language:
            self.languages[file.language] = self.languages.get(file.language, 0) + 1

        return file

    def summary(self) -> str:
        language_summary = ", ".join(
            f"{name}: {count}"
            for name, count in sorted(
                self.languages.items(),
                key=lambda item: (-item[1], item[0]),
            )
        )

        extension_summary = ", ".join(
            f"{name}: {count}"
            for name, count in sorted(
                self.extensions.items(),
                key=lambda item: (-item[1], item[0]),
            )
        )

        lines = [
            f"Proyecto: {self.project_name}",
            f"Ruta: {self.root_path}",
            f"Archivos: {self.file_count}",
            f"Directorios: {self.directory_count}",
        ]

        if language_summary:
            lines.append(f"Lenguajes: {language_summary}")

        if extension_summary:
            lines.append(f"Extensiones: {extension_summary}")

        return "\n".join(lines)

    def to_dict(
        self,
        include_content: bool = True,
    ) -> dict[str, Any]:
        return {
            "project_name": self.project_name,
            "root_path": self.root_path,
            "files": [file.to_dict(include_content=include_content) for file in self.files],
            "directories": [directory.to_dict() for directory in self.directories],
            "languages": dict(self.languages),
            "extensions": dict(self.extensions),
            "metadata": dict(self.metadata),
            "generated_at": self.generated_at,
        }

    def to_architecture_context(
        self,
        max_files: int = 120,
        max_directories: int = 80,
        *,
        include_file_content: bool = False,
    ) -> dict[str, Any]:
        """
        Evidencia estructural para Agents.
        Por defecto NO incluye content de archivos (prompt lean).
        """
        file_entries: list[dict[str, Any]] = []
        for file in self.files[:max_files]:
            if include_file_content and hasattr(file, "to_architecture_dict"):
                file_entries.append(file.to_architecture_dict())
            else:
                entry: dict[str, Any] = {
                    "path": getattr(file, "path", ""),
                }
                ext = getattr(file, "extension", None)
                lang = getattr(file, "language", None)
                if ext:
                    entry["extension"] = ext
                if lang:
                    entry["language"] = lang
                file_entries.append(entry)

        return {
            "project": {
                "name": self.project_name,
                "root_path": self.root_path,
                "file_count": self.file_count,
                "directory_count": self.directory_count,
            },
            "languages": dict(self.languages),
            "extensions": dict(self.extensions),
            "directories": [
                directory.to_dict() for directory in self.directories[:max_directories]
            ],
            "files": file_entries,
            "metadata": dict(self.metadata),
            "summary": self.summary(),
        }

    def to_prompt(
        self,
        max_files: int = 120,
        max_directories: int = 80,
    ) -> str:

        return json.dumps(
            self.to_architecture_context(
                max_files=max_files,
                max_directories=max_directories,
            ),
            ensure_ascii=False,
            indent=2,
        )

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> ProjectSnapshot:

        files: list[ProjectFile] = []
        for item in data.get("files", []):
            if not isinstance(item, dict):
                continue
            try:
                files.append(ProjectFile.from_dict(item))
            except Exception:
                continue

        directories: list[ProjectDirectory] = []
        for item in data.get("directories", []):
            if not isinstance(item, dict):
                continue
            directories.append(
                ProjectDirectory(
                    path=str(item.get("path", "") or ""),
                    name=str(item.get("name", "") or ""),
                    files_count=int(item.get("files_count", 0) or 0),
                    directories_count=int(item.get("directories_count", 0) or 0),
                    metadata=dict(item.get("metadata") or {}),
                )
            )

        return cls(
            project_name=str(data.get("project_name") or "Unknown"),
            root_path=str(data.get("root_path") or ""),
            files=files,
            directories=directories,
            languages=dict(data.get("languages") or {}),
            extensions=dict(data.get("extensions") or {}),
            metadata=dict(data.get("metadata") or {}),
            generated_at=data.get("generated_at"),
        )
