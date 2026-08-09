from __future__ import annotations

import logging
from pathlib import Path
from datetime import datetime

from typing import Optional

logger = logging.getLogger(__name__)


class GentlemanSkills:
    """
    Gestor de conocimiento operativo reutilizable.

    Descubre SKILL.md externos y los expone
    como conocimiento consultable.

    No ejecuta herramientas.
    No decide planificación.
    No construye prompts.
    """

    # Orden de prioridad:
    # más arriba gana
    SEARCH_PATHS = (
        (
            "engram",
            Path.home() / ".engram" / "skills",
        ),
        (
            "claude",
            Path.home() / ".claude" / "skills",
        ),
        (
            "claude_subagents",
            Path.home() / ".claude" / "subagents",
        ),
        (
            "codex",
            Path.home() / ".codex" / "skills",
        ),
        (
            "gentleman",
            Path.home() / ".gentleman" / "skills",
        ),
    )

    def __init__(self):

        self.skills: dict[str, str] = {}

        self.metadata: dict[str, dict] = {}

        self._search_cache: dict[str, list[str]] = {}

        self.skills_dirs = self._discover_skill_dirs()

        self._load_all()

    # ======================================================
    # Discovery
    # ======================================================

    def _discover_skill_dirs(self) -> list[dict]:

        result = []

        for priority, path in self.SEARCH_PATHS:

            if path.exists() and path.is_dir():

                result.append(
                    {
                        "name": priority,
                        "path": path,
                    }
                )

        return result

    # ======================================================
    # Loading
    # ======================================================

    def _load_all(self):

        self.skills.clear()

        self.metadata.clear()

        for source in self.skills_dirs:

            base = source["path"]

            for file in base.rglob("SKILL.md"):

                self._load_skill(
                    file,
                    source["name"],
                )

    def _load_skill(
        self,
        file: Path,
        source: str,
    ):

        try:

            content = file.read_text(
                encoding="utf-8",
                errors="ignore",
            )

            if not content.strip():

                return

            name = self._normalize_name(file.parent.name)

            # Si ya existe una skill con
            # mayor prioridad no reemplazar

            if name in self.skills:

                return

            stat = file.stat()

            self.skills[name] = content

            self.metadata[name] = {
                "name": name,
                "source": source,
                "path": str(file),
                "size": len(content),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            }

        except Exception:

            logger.exception(
                "Error cargando skill %s",
                file,
            )

    # ======================================================
    # Public API
    # ======================================================

    def list_skills(self) -> list[str]:

        return sorted(self.skills.keys())

    def get_skill(
        self,
        name: str,
    ) -> Optional[str]:

        return self.skills.get(self._normalize_name(name))

    def get_metadata(
        self,
        name: str,
    ) -> Optional[dict]:

        return self.metadata.get(self._normalize_name(name))

    def get_all_metadata(self) -> dict:

        return dict(self.metadata)

    def find_relevant(
        self,
        query: str,
        limit: int = 3,
    ) -> list[str]:

        if not query:

            return []

        cache_key = f"{query}:{limit}"

        if cache_key in self._search_cache:

            return self._search_cache[cache_key]

        tokens = {token for token in query.lower().split() if len(token) > 2}

        scored = []

        for name, content in self.skills.items():

            score = 0

            normalized_name = name.replace("_", " ").replace("-", " ")

            for token in tokens:

                if token in normalized_name:

                    score += 5

                if token in content.lower():

                    score += 1

            if score:

                scored.append(
                    (
                        score,
                        name,
                    )
                )

        scored.sort(reverse=True)

        result = [name for _, name in scored[:limit]]

        self._search_cache[cache_key] = result

        return result

    def find_skills(
        self,
        query: str,
        limit: int = 3,
    ) -> list[str]:

        return self.find_relevant(
            query,
            limit,
        )

    # ======================================================
    # Reload
    # ======================================================

    def reload(
        self,
        force: bool = True,
    ):

        self._search_cache.clear()

        self.skills_dirs = self._discover_skill_dirs()

        if force:

            self._load_all()

    # ======================================================
    # Helpers
    # ======================================================

    @staticmethod
    def _normalize_name(
        name: str,
    ) -> str:

        return (
            name.strip()
            .lower()
            .replace(
                "_",
                "-",
            )
            .replace(
                " ",
                "-",
            )
        )
