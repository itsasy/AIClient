from __future__ import annotations

from dataclasses import dataclass, field

from core.project_file import ProjectFile


@dataclass(slots=True)
class ProjectSnapshot:
    """
    Snapshot estructurado del proyecto.

    Sustituye progresivamente al antiguo snapshot basado
    únicamente en texto.
    """

    root: str
    files: list[ProjectFile] = field(default_factory=list)

    def add_file(
        self,
        path: str,
        content: str,
    ) -> None:
        self.files.append(
            ProjectFile(
                path=path,
                content=content,
            )
        )

    @property
    def file_count(self) -> int:
        return len(self.files)

    def find_by_extension(
        self,
        extension: str,
    ) -> list[ProjectFile]:
        extension = extension.lower()

        return [
            file
            for file in self.files
            if file.extension == extension
        ]

    def find_by_name(
        self,
        name: str,
    ) -> list[ProjectFile]:
        name = name.lower()

        return [
            file
            for file in self.files
            if name in file.filename.lower()
        ]

    def find_by_directory(
        self,
        directory: str,
    ) -> list[ProjectFile]:
        directory = directory.lower()

        return [
            file
            for file in self.files
            if directory in file.directory.lower()
        ]

    def summary(self) -> dict:
        extensions: dict[str, int] = {}

        for file in self.files:
            extensions[file.extension] = (
                extensions.get(file.extension, 0) + 1
            )

        return {
            "root": self.root,
            "files": self.file_count,
            "extensions": extensions,
        }

    def to_prompt(self) -> str:
        """
        Compatibilidad temporal con PromptBuilder.

        Mientras el resto del sistema migra al nuevo
        modelo estructurado, este método genera una
        representación textual.
        """

        lines = [
            f"Proyecto: {self.root}",
            "",
            f"Archivos inspeccionados: {self.file_count}",
            "",
        ]

        for file in self.files:
            lines.append(f"# {file.path}")
            lines.append(file.content)
            lines.append("")

        return "\n".join(lines)