from __future__ import annotations

import hashlib
import json
import logging
import os
from pathlib import Path

from core.config import Config
from core.project_snapshot import ProjectSnapshot

logger = logging.getLogger(__name__)


class ProjectInspector:
    """
    Inspector responsable de construir snapshots del proyecto.

    Características:
    - Escaneo controlado.
    - Cache incremental.
    - Exclusión de carpetas pesadas.
    - Snapshot preparado para LLM.
    """

    MAX_FILE_CHARS = 3000
    MAX_SOURCE_FILES = 50

    CACHE_FILE = Config.PROJECT_ROOT / ".project_cache.json"

    EXCLUDED_DIRS = {
        ".git",
        ".venv",
        "venv",
        "__pycache__",
        ".pytest_cache",
        "node_modules",
        "vendor",
        "dist",
        "build",
        ".next",
        "target",
        "storage",
        "bootstrap",
        ".idea",
        ".vscode",
    }

    INCLUDED_EXTENSIONS = {
        ".py",
        ".toml",
        ".md",
        ".php",
        ".json",
        ".js",
        ".ts",
        ".tsx",
        ".jsx",
        ".vue",
        ".css",
        ".html",
        ".yaml",
        ".yml",
        ".xml",
        ".sh",
        ".env",
        ".ini",
        ".lock",
    }

    PRIORITY_FILES = (
        "README.md",
        "pyproject.toml",
        "package.json",
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
        return self.inspect_snapshot().to_prompt()

    def inspect_snapshot(self) -> ProjectSnapshot:

        root = Config.TARGET_PROJECT_ROOT

        current_hash = self._compute_project_hash(root)

        cached = self._load_cache()

        if cached and cached.get("hash") == current_hash:
            logger.info("Usando snapshot cacheado")
            return ProjectSnapshot.from_dict(cached["snapshot"])

        logger.info("Construyendo nuevo snapshot")

        snapshot = self._build_snapshot(root)

        self._save_cache(
            current_hash,
            snapshot,
        )

        return snapshot

    def _build_snapshot(
        self,
        root: Path,
    ) -> ProjectSnapshot:

        snapshot = ProjectSnapshot(root=root.name)

        files = self._collect_all_files(root)

        for path in files[: self.MAX_SOURCE_FILES]:

            try:

                content = path.read_text(
                    encoding="utf-8",
                    errors="ignore",
                )[: self.MAX_FILE_CHARS]

                snapshot.add_file(
                    path=str(path.relative_to(root)),
                    content=content,
                )

            except OSError:
                logger.warning(
                    "No se pudo leer %s",
                    path,
                )

        return snapshot

    def _collect_all_files(
        self,
        root: Path,
    ) -> list[Path]:

        result = []

        seen = set()

        for filename in self.PRIORITY_FILES:

            path = root / filename

            if path.exists():

                result.append(path)
                seen.add(path)

        for directory_name in self.SOURCE_DIRS:

            directory = root / directory_name

            if not directory.exists():
                continue

            for path in self._walk_controlled(
                directory,
                root,
            ):

                if path not in seen and path.suffix.lower() in self.INCLUDED_EXTENSIONS:
                    result.append(path)
                    seen.add(path)

        return sorted(result)

    def _walk_controlled(
        self,
        directory: Path,
        root: Path,
    ) -> list[Path]:

        files = []

        for current, dirs, filenames in os.walk(directory):

            dirs[:] = [d for d in dirs if d not in self.EXCLUDED_DIRS]

            for filename in filenames:

                path = Path(current) / filename

                relative = path.relative_to(root)

                if any(part in self.EXCLUDED_DIRS for part in relative.parts):
                    continue

                files.append(path)

        return files

    def _compute_project_hash(
        self,
        root: Path,
    ) -> str:

        hasher = hashlib.sha256()

        for path in self._collect_all_files(root):

            try:

                stat = path.stat()

                hasher.update(str(path.relative_to(root)).encode())

                hasher.update(str(stat.st_size).encode())

                hasher.update(str(stat.st_mtime_ns).encode())

            except OSError:
                continue

        return hasher.hexdigest()

    def _load_cache(self):

        if not self.CACHE_FILE.exists():
            return None

        try:

            return json.loads(self.CACHE_FILE.read_text(encoding="utf-8"))

        except Exception:

            logger.warning("Cache corrupta")

            return None

    def _save_cache(
        self,
        hash_value: str,
        snapshot: ProjectSnapshot,
    ):

        data = {
            "root": str(Config.TARGET_PROJECT_ROOT),
            "hash": hash_value,
            "snapshot": snapshot.to_dict(),
        }

        try:

            self.CACHE_FILE.write_text(
                json.dumps(
                    data,
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

        except OSError:

            logger.exception("No se pudo guardar cache")
