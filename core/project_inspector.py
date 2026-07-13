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
        root = Config.PROJECT_ROOT

        if not root.exists():
            return "No se pudo localizar la raíz del proyecto."

        all_files = self._collect_all_files(root)
        inspected_files = all_files[:self.MAX_SOURCE_FILES]
        omitted_files = all_files[self.MAX_SOURCE_FILES:]

        lines = [
            f"Proyecto: {root.name}",
            f"Ruta: {root}",
            "",
            "=== ALCANCE DE LA INSPECCIÓN ===",
            (
                f"Se inspeccionaron {len(inspected_files)} de "
                f"{len(all_files)} archivos elegibles."
            ),
            (
                "IMPORTANTE: este snapshot es parcial. "
                "Un archivo no incluido o no inspeccionado no debe "
                "considerarse inexistente."
            ),
            "",
            "=== ARCHIVOS INSPECCIONADOS ===",
        ]

        if inspected_files:
            for path in inspected_files:
                lines.append(f"- {path.relative_to(root)}")
        else:
            lines.append("- Ninguno")

        lines.extend(
            [
                "",
                "=== ARCHIVOS NO INSPECCIONADOS POR LÍMITE ===",
            ]
        )

        if omitted_files:
            for path in omitted_files:
                lines.append(f"- {path.relative_to(root)}")
        else:
            lines.append("- Ninguno")

        lines.extend(
            [
                "",
                "=== CONTENIDO INSPECCIONADO ===",
            ]
        )

        for path in inspected_files:
            relative_path = path.relative_to(root)

            try:
                full_content = path.read_text(
                    encoding="utf-8",
                    errors="ignore",
                )
            except OSError as exc:
                lines.append(
                    f"\n===== {relative_path} =====\n"
                    f"No se pudo leer el archivo: {exc}"
                )
                continue

            content = full_content[:self.MAX_FILE_CHARS]

            lines.append(f"\n===== {relative_path} =====")
            lines.append(content)

            if len(full_content) > self.MAX_FILE_CHARS:
                lines.append(
                    "\n[CONTENIDO TRUNCADO: "
                    f"se muestran los primeros {self.MAX_FILE_CHARS} caracteres]"
                )

        return "\n".join(lines)

    def _collect_all_files(self, root: Path) -> list[Path]:
        files: list[Path] = []

        for filename in self.PRIORITY_FILES:
            path = root / filename

            if path.exists() and path.is_file():
                files.append(path)

        for directory_name in self.SOURCE_DIRS:
            directory = root / directory_name

            if not directory.exists() or not directory.is_dir():
                continue

            for path in sorted(directory.rglob("*")):
                if not path.is_file():
                    continue

                relative_parts = path.relative_to(root).parts

                if any(
                    part in self.EXCLUDED_DIRS
                    for part in relative_parts
                ):
                    continue

                if path.suffix.lower() not in self.INCLUDED_EXTENSIONS:
                    continue

                if path not in files:
                    files.append(path)

        return files