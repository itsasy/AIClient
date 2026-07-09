from pathlib import Path

from core.config import Config


class ProjectInspector:
    def inspect(self) -> str:
        root = Config.PROJECT_ROOT

        if not root.exists():
            return "No se pudo localizar la raíz del proyecto."

        relevant = [
            "README.md",
            "pyproject.toml",
            "core",
            "llm",
            "skills",
            "agents",
            "obsidian",
            "cli",
        ]

        lines = [
            f"Proyecto: {root.name}",
            f"Ruta: {root}",
            ""
        ]

        for item in relevant:
            path = root / item

            if not path.exists():
                continue

            if path.is_dir():

                files = sorted(
                    child.name
                    for child in path.iterdir()
                    if not child.name.startswith("__pycache__")
                )

                lines.append(f"{item}/")

                for f in files[:20]:
                    lines.append(f"  - {f}")

            else:

                try:
                    content = path.read_text(
                        encoding="utf-8",
                        errors="ignore"
                    )[:1200]

                except Exception:
                    content = ""

                lines.append(f"\n===== {item} =====")
                lines.append(content)

        return "\n".join(lines)