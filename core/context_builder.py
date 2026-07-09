import logging

from core.config import Config
from obsidian.search import ObsidianSearch

logger = logging.getLogger(__name__)


class ContextBuilder:
    def __init__(self):
        self.obsidian = ObsidianSearch()

    def build(self, query: str) -> str:
        q = (query or "").lower()

        requires_project = any(
            word in q
            for word in (
                "proyecto",
                "arquitectura",
                "estructura",
                "repo",
                "readme",
                "docker",
                "laravel",
                "nestjs",
                "spring",
                "directorio",
                "carpeta",
            )
        )

        sections = []

        if requires_project:
            sections.append("=== CONTEXTO DEL PROYECTO ===")
            sections.append(self.build_project_snapshot())

        obsidian = self.obsidian.build_context(query)
        if obsidian:
            sections.append("=== SEGUNDO CEREBRO ===")
            sections.append(obsidian)

        sections.append(f"=== CONSULTA ===\n{query}")
        result = "\n\n".join(section for section in sections if section)
        if not result:
            logger.debug("No se generó contexto para: %s", query)
        return result

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
