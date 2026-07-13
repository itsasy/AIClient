from pathlib import Path

from core.config import Config


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

    def inspect(self) -> str:
        root = Config.PROJECT_ROOT

        if not root.exists():
            return "No se pudo localizar la raíz del proyecto."

        lines = [
            f"Proyecto: {root.name}",
            f"Ruta: {root}",
            "",
            "=== ESTRUCTURA OBSERVADA ===",
        ]

        source_files = self._collect_files(root)

        for path in source_files:
            relative_path = path.relative_to(root)
            lines.append(f"- {relative_path}")

        lines.append("")
        lines.append("=== CONTENIDO INSPECCIONADO ===")

        for path in source_files:
            relative_path = path.relative_to(root)

            try:
                content = path.read_text(
                    encoding="utf-8",
                    errors="ignore",
                )[:self.MAX_FILE_CHARS]
            except OSError as exc:
                lines.append(
                    f"\n===== {relative_path} =====\n"
                    f"No se pudo leer: {exc}"
                )
                continue

            lines.append(
                f"\n===== {relative_path} =====\n{content}"
            )

        return "\n".join(lines)

    def _collect_files(self, root: Path) -> list[Path]:
        files = []

        priority_files = [
            root / "README.md",
            root / "pyproject.toml",
        ]

        for path in priority_files:
            if path.exists() and path.is_file():
                files.append(path)

        source_dirs = [
            "core",
            "llm",
            "skills",
            "agents",
            "obsidian",
            "cli",
        ]

        for directory_name in source_dirs:
            directory = root / directory_name

            if not directory.exists():
                continue

            for path in sorted(directory.rglob("*")):
                if len(files) >= self.MAX_SOURCE_FILES:
                    break

                if not path.is_file():
                    continue

                if any(
                    part in self.EXCLUDED_DIRS
                    for part in path.parts
                ):
                    continue

                if path.suffix not in self.INCLUDED_EXTENSIONS:
                    continue

                if path not in files:
                    files.append(path)

        return files[:self.MAX_SOURCE_FILES]