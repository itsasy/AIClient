from __future__ import annotations

import logging

from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class GentlemanSkills:
    """
    Gestor de Gentleman Skills.

    Descubre conocimiento operativo reutilizable.

    Fuentes:

    - ~/.engram/skills/
    - ~/.claude/skills/
    - ~/.codex/skills/
    - ~/.gentleman/skills/

    Responsabilidades:

    - Descubrir skills.
    - Cargar contenido.
    - Indexar metadata.
    - Buscar skills relevantes.

    No:

    - Construye prompts.
    - Ejecuta herramientas.
    - Decide prioridades.
    """

    SEARCH_PATHS = (
        Path.home() / ".engram" / "skills",
        Path.home() / ".claude" / "skills",
        Path.home() / ".codex" / "skills",
        Path.home() / ".gentleman" / "skills",
    )

    def __init__(self):

        self.skills: dict[str, str] = {}

        self.metadata: dict[str, dict] = {}

        self._search_cache: dict[str, list[str]] = {}

        self.skills_dirs = self._discover_skill_dirs()

        if not self.skills_dirs:

            logger.warning("No se encontraron Gentleman Skills.")

            return

        logger.info(
            "Directorios Gentleman encontrados: %s",
            self.skills_dirs,
        )

        self._load_all()

        logger.info(
            "Gentleman Skills cargadas: %s",
            list(self.skills.keys()),
        )

    # ==========================================================
    # Discovery
    # ==========================================================

    def _discover_skill_dirs(self) -> list[Path]:

        directories = []

        for path in self.SEARCH_PATHS:

            if path.exists() and path.is_dir():

                directories.append(path)

        return directories

    # ==========================================================
    # Loading
    # ==========================================================

    def _load_all(self) -> None:

        for directory in self.skills_dirs:

            for file in directory.rglob("SKILL.md"):

                self._load_skill(file)

    def _load_skill(
        self,
        file: Path,
    ) -> None:

        try:

            name = self._normalize_name(file.parent.name)

            content = file.read_text(
                encoding="utf-8",
                errors="ignore",
            )

            if not content.strip():

                return

            # Si existe una skill con mismo nombre,
            # gana la última encontrada.
            self.skills[name] = content

            self.metadata[name] = {
                "name": name,
                "path": str(file),
                "directory": str(file.parent),
                "size": len(content),
            }

        except Exception:

            logger.exception(
                "Error cargando skill: %s",
                file,
            )

    # ==========================================================
    # Public API
    # ==========================================================

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
    ) -> dict | None:

        return self.metadata.get(self._normalize_name(name))

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

        query_lower = query.lower()

        query_tokens = {token for token in query_lower.split() if len(token) > 2}

        scored: list[tuple[int, str]] = []

        for name, content in self.skills.items():

            score = 0

            normalized_name = name.replace("-", " ").replace("_", " ")

            # -----------------------------
            # Match nombre
            # -----------------------------

            for token in normalized_name.split():

                if token in query_lower:

                    score += 5

            # -----------------------------
            # Match contenido
            # -----------------------------

            preview = content.lower()

            for token in query_tokens:

                if token in preview:

                    score += 1

            # -----------------------------
            # Frontmatter / tags
            # -----------------------------

            if "tags:" in preview:

                for token in query_tokens:

                    if token in preview:

                        score += 2

            if score:

                scored.append(
                    (
                        score,
                        name,
                    )
                )

        scored.sort(
            key=lambda item: item[0],
            reverse=True,
        )

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

    # ==========================================================
    # Reload
    # ==========================================================

    def reload(self) -> None:

        self.skills.clear()

        self.metadata.clear()

        self._search_cache.clear()

        self.skills_dirs = self._discover_skill_dirs()

        self._load_all()

    # ==========================================================
    # Helpers
    # ==========================================================

    @staticmethod
    def _normalize_name(
        name: str,
    ) -> str:

        return (
            name.strip()
            .lower()
            .replace(
                " ",
                "-",
            )
            .replace(
                "_",
                "-",
            )
        )
