from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class ProjectFile:
    """
    Representación de un archivo inspeccionado.

    El contenido completo puede existir en memoria para operaciones
    internas, pero NO debe enviarse automáticamente al LLM.
    """

    path: str
    filename: str
    extension: str = ""
    size: int = 0
    lines: int = 0
    language: str | None = None
    content: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

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
        """
        Representación mínima de un archivo para análisis arquitectónico.
        """

        return {
            "path": self.path,
            "filename": self.filename,
            "extension": self.extension,
            "language": self.language,
            "lines": self.lines,
            "size": self.size,
            "metadata": dict(self.metadata),
        }


@dataclass(slots=True)
class ProjectDirectory:
    """
    Representación de un directorio del proyecto.
    """

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

    El snapshot es una representación interna del proyecto.
    No debe confundirse con el contexto que se envía al LLM.

    Representaciones:

        to_dict()
            Snapshot completo.

        to_architecture_context()
            Vista compacta para análisis arquitectónico.

        to_prompt()
            Alias seguro de la representación compacta.
    """

    project_name: str

    root_path: str = ""

    files: list[Any] = field(default_factory=list)
    directories: list[Any] = field(default_factory=list)

    languages: dict[str, int] = field(default_factory=dict)
    extensions: dict[str, int] = field(default_factory=dict)

    metadata: dict[str, Any] = field(default_factory=dict)

    generated_at: str | None = None

    # ==========================================================
    # Properties
    # ==========================================================

    @property
    def file_count(self) -> int:
        return len(self.files)

    @property
    def directory_count(self) -> int:
        return len(self.directories)

    # ==========================================================
    # Summary
    # ==========================================================

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
            lines.append(
                f"Lenguajes: {language_summary}",
            )

        if extension_summary:
            lines.append(
                f"Extensiones: {extension_summary}",
            )

        return "\n".join(lines)

    # ==========================================================
    # Serialization
    # ==========================================================

    def _serialize_item(
        self,
        item: Any,
        include_content: bool = True,
    ) -> Any:
        if hasattr(item, "to_dict"):
            try:
                return item.to_dict(
                    include_content=include_content,
                )
            except TypeError:
                return item.to_dict()

        if hasattr(item, "__dict__"):
            data = dict(item.__dict__)

            if not include_content:
                data.pop("content", None)

            return data

        if isinstance(item, dict):
            data = dict(item)

            if not include_content:
                data.pop("content", None)

            return data

        return str(item)

    def to_dict(
        self,
        include_content: bool = True,
    ) -> dict[str, Any]:
        """
        Serialización completa del snapshot.

        Úsese para persistencia, debugging o herramientas internas.
        No usar directamente como contexto LLM.
        """

        return {
            "project_name": self.project_name,
            "root_path": self.root_path,
            "files": [
                self._serialize_item(
                    item,
                    include_content=include_content,
                )
                for item in self.files
            ],
            "directories": [
                self._serialize_item(
                    item,
                    include_content=include_content,
                )
                for item in self.directories
            ],
            "languages": dict(self.languages),
            "extensions": dict(self.extensions),
            "metadata": dict(self.metadata),
            "generated_at": self.generated_at,
        }

    # ==========================================================
    # Architecture context
    # ==========================================================

    def to_architecture_context(
        self,
        max_files: int = 120,
        max_directories: int = 80,
    ) -> dict[str, Any]:
        """
        Construye la representación específica para un ArchitectAgent.

        No incluye contenido fuente.

        El objetivo es que el LLM pueda entender:

            - tamaño del proyecto
            - estructura
            - módulos
            - archivos relevantes
            - lenguajes
            - extensiones

        sin recibir cientos de KB de código fuente.
        """

        files = []

        for item in self.files[:max_files]:
            files.append(
                self._serialize_item(
                    item,
                    include_content=False,
                )
            )

        directories = []

        for item in self.directories[:max_directories]:
            directories.append(
                self._serialize_item(
                    item,
                    include_content=False,
                )
            )

        return {
            "project": {
                "name": self.project_name,
                "root_path": self.root_path,
                "file_count": self.file_count,
                "directory_count": self.directory_count,
            },
            "languages": dict(self.languages),
            "extensions": dict(self.extensions),
            "directories": directories,
            "files": files,
            "metadata": dict(self.metadata),
        }

    def to_prompt(
        self,
        max_files: int = 120,
        max_directories: int = 80,
    ) -> str:
        """
        Compatibilidad con código existente.

        IMPORTANTE:
        to_prompt() ya NO devuelve el contenido completo del proyecto.
        Devuelve únicamente el contexto arquitectónico compacto.
        """

        import json

        return json.dumps(
            self.to_architecture_context(
                max_files=max_files,
                max_directories=max_directories,
            ),
            ensure_ascii=False,
            indent=2,
        )

    # ==========================================================
    # Factory helpers
    # ==========================================================

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> ProjectSnapshot:
        return cls(
            project_name=data.get(
                "project_name",
                "Unknown",
            ),
            root_path=data.get(
                "root_path",
                "",
            ),
            files=data.get(
                "files",
                [],
            ),
            directories=data.get(
                "directories",
                [],
            ),
            languages=data.get(
                "languages",
                {},
            ),
            extensions=data.get(
                "extensions",
                {},
            ),
            metadata=data.get(
                "metadata",
                {},
            ),
            generated_at=data.get(
                "generated_at",
            ),
        )
