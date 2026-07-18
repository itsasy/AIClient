from pathlib import Path

from core.config import Config
from core.project_snapshot import ProjectSnapshot


class ProjectInspector:
    MAX_FILE_CHARS = 3000
    MAX_SOURCE_FILES = 20

    EXCLUDED_DIRS = {
        ".git",
        ".venv",
        "__pycache__",
        ".pytest_cache",
    }

    INCLUDED_EXTENSIONS = {
        ".py",
        ".toml",
        ".md",
    }

    PRIORITY_FILES = (
        "README.md",
        "pyproject.toml",
    )

    SOURCE_DIRS = (
        "core",
        "llm",
        "skills",
        "agents",
        "obsidian",
        "cli",
        "tests",
    )

    def inspect(self) -> str:
        """
        Compatibilidad con el resto del proyecto.

        Continúa devolviendo un string mientras el resto
        del sistema migra a ProjectSnapshot.
        """

        snapshot = self.inspect_snapshot()

        return snapshot.to_prompt()

    def inspect_snapshot(self) -> ProjectSnapshot:
        """
        Nuevo método.

        Devuelve un modelo estructurado del proyecto.
        """

        root = Config.TARGET_PROJECT_ROOT

        snapshot = ProjectSnapshot(
            root=root.name,
        )

        if not root.exists():
            return snapshot

        all_files = self._collect_all_files(root)

        for path in all_files[: self.MAX_SOURCE_FILES]:

            try:
                full_content = path.read_text(
                    encoding="utf-8",
                    errors="ignore",
                )
            except OSError:
                continue

            snapshot.add_file(
                path=str(path.relative_to(root)),
                content=full_content[: self.MAX_FILE_CHARS],
            )

        return snapshot

    def _collect_all_files(
        self,
        root: Path,
    ) -> list[Path]:
        files: list[Path] = []

        for filename in self.PRIORITY_FILES:
            path = root / filename

            if path.exists() and path.is_file():
                files.append(path)

        for directory_name in self.SOURCE_DIRS:

            directory = root / directory_name

            if not directory.exists():
                continue

            if not directory.is_dir():
                continue

            for path in sorted(directory.rglob("*")):

                if not path.is_file():
                    continue

                relative_parts = path.relative_to(root).parts

                if any(part in self.EXCLUDED_DIRS for part in relative_parts):
                    continue

                if path.suffix.lower() not in self.INCLUDED_EXTENSIONS:
                    continue

                if path not in files:
                    files.append(path)

        return files
