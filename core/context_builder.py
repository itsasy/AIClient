import os
from pathlib import Path

from core.config import Config
from obsidian.search import ObsidianSearch


class ContextBuilder:
    def __init__(self):
        self.obsidian = ObsidianSearch()

    def build(self, query: str) -> str:
        project_context = self.build_project_snapshot()
        obsidian_context = self.obsidian.build_context(query)

        sections = [
            "=== CONTEXTO DEL PROYECTO ===",
            project_context.strip(),
        ]

        if obsidian_context.strip():
            sections.extend(["=== CONOCIMIENTO LOCAL (OBSIDIAN) ===", obsidian_context.strip()])

        sections.append(f"=== CONSULTA ACTUAL ===\n{query}\n")
        return "\n\n".join(sections)

    def build_project_snapshot(self) -> str:
        root = Config.PROJECT_ROOT
        if not root.exists():
            return "No se pudo localizar la raíz del proyecto."

        relevant_files = [
            "README.md",
            "pyproject.toml",
            "agents",
            "core",
            "llm",
            "skills",
            "obsidian",
            "cli",
        ]

        lines = [f"Proyecto: {root.name}", f"Ruta: {root}"]
        for name in relevant_files:
            path = root / name
            if path.exists():
                if path.is_dir():
                    entries = sorted([child.name for child in path.iterdir()][:12])
                    lines.append(f"- {name}/: {', '.join(entries)}")
                else:
                    try:
                        content = path.read_text(encoding="utf-8", errors="ignore")[:1200]
                    except OSError:
                        content = ""
                    lines.append(f"- {name}:\n{content}")

        return "\n".join(lines)
