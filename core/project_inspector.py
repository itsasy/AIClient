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
    Inspector responsable de construir snapshots estructurados del proyecto.

    Responsabilidades:
    - Inspeccionar el proyecto objetivo.
    - Mantener un cache incremental.
    - Excluir directorios pesados o irrelevantes.
    - Limitar la cantidad de archivos inspeccionados.
    - Generar ProjectSnapshot compatible con el modelo actual.

    No:
    - Ejecuta código.
    - Decide qué contexto necesita una tarea.
    - Construye prompts.
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
        # AIClient / libs
        "core",
        "llm",
        "skills",
        "agents",
        "obsidian",
        "cli",
        "tests",
        # Proyectos generados (POS y otros)
        "src",
        "app",
        "lib",
        "modules",
        "adapters",
        "backend",
        "frontend",
        "api",
    )

    # ==========================================================
    # Public API
    # ==========================================================

    def inspect(self) -> str:
        """
        Compatibilidad con componentes que todavía esperan
        una representación textual.
        """
        return self.inspect_snapshot().to_prompt()

    def inspect_snapshot(self) -> ProjectSnapshot:
        """
        Construye o recupera el snapshot del proyecto objetivo.
        """

        root = Config.TARGET_PROJECT_ROOT

        if not root.exists():
            logger.warning(
                "Target project root no existe: %s",
                root,
            )

        current_hash = self._compute_project_hash(root)

        cached = self._load_cache()

        if cached and cached.get("hash") == current_hash and cached.get("snapshot"):
            logger.info("Usando snapshot cacheado")

            try:
                return ProjectSnapshot.from_dict(cached["snapshot"])
            except Exception:
                logger.exception("No se pudo cargar snapshot desde cache. " "Se reconstruirá.")

        logger.info("Construyendo nuevo snapshot")

        snapshot = self._build_snapshot(root)

        self._save_cache(
            current_hash,
            snapshot,
        )

        return snapshot

    # ==========================================================
    # Snapshot
    # ==========================================================

    def _build_snapshot(
        self,
        root: Path,
    ) -> ProjectSnapshot:
        """
        Construye un ProjectSnapshot usando la API actual.

        ProjectSnapshot actualmente recibe:
            project_name
            root_path
        """

        snapshot = ProjectSnapshot(
            project_name=root.name,
            root_path=str(root),
        )

        if not root.exists():
            return snapshot

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

    # ==========================================================
    # File collection
    # ==========================================================

    def _collect_all_files(
        self,
        root: Path,
    ) -> list[Path]:
        """
        Obtiene archivos relevantes del proyecto.
        """

        result: list[Path] = []
        seen: set[Path] = set()

        # ------------------------------------------------------
        # Archivos prioritarios
        # ------------------------------------------------------

        for filename in self.PRIORITY_FILES:
            path = root / filename

            if path.exists() and path.is_file():
                result.append(path)
                seen.add(path)

        # ------------------------------------------------------
        # Directorios fuente
        # ------------------------------------------------------

        for directory_name in self.SOURCE_DIRS:
            directory = root / directory_name

            if not directory.exists() or not directory.is_dir():
                continue

            for path in self._walk_controlled(
                directory,
                root,
            ):
                if path in seen:
                    continue

                if path.suffix.lower() not in self.INCLUDED_EXTENSIONS:
                    continue

                result.append(path)
                seen.add(path)

        if not result:
            for path in self._walk_controlled(root, root):
                if path in seen:
                    continue
                if path.suffix.lower() not in self.INCLUDED_EXTENSIONS:
                    continue
                result.append(path)
                seen.add(path)

        return result

    def _walk_controlled(
        self,
        directory: Path,
        root: Path,
    ) -> list[Path]:
        """
        Recorre un directorio evitando carpetas excluidas.
        """

        files: list[Path] = []

        for current, dirs, filenames in os.walk(directory):

            dirs[:] = [
                directory_name
                for directory_name in dirs
                if directory_name not in self.EXCLUDED_DIRS
            ]

            for filename in filenames:

                path = Path(current) / filename

                try:
                    relative = path.relative_to(root)
                except ValueError:
                    continue

                if any(part in self.EXCLUDED_DIRS for part in relative.parts):
                    continue

                if path.suffix.lower() not in self.INCLUDED_EXTENSIONS:
                    continue

                files.append(path)

        return files

    # ==========================================================
    # Hash / Cache
    # ==========================================================

    def _compute_project_hash(
        self,
        root: Path,
    ) -> str:
        """
        Calcula un hash ligero basado en rutas,
        tamaño y fecha de modificación.
        """

        hasher = hashlib.sha256()

        if not root.exists():
            return hasher.hexdigest()

        for path in self._collect_all_files(root):

            try:
                stat = path.stat()

                hasher.update(str(path.relative_to(root)).encode("utf-8"))

                hasher.update(str(stat.st_size).encode("utf-8"))

                hasher.update(str(stat.st_mtime_ns).encode("utf-8"))

            except OSError:
                continue

        return hasher.hexdigest()

    def _load_cache(self):
        if not self.CACHE_FILE.exists():
            return None

        try:
            return json.loads(self.CACHE_FILE.read_text(encoding="utf-8"))

        except Exception:
            logger.warning("Cache de proyecto corrupta. " "Se reconstruirá.")
            return None

    def _save_cache(
        self,
        hash_value: str,
        snapshot: ProjectSnapshot,
    ) -> None:

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
            logger.exception("No se pudo guardar cache del proyecto")
