from __future__ import annotations

import hashlib
import json
import logging
import os
from pathlib import Path

from core.config import Config
from core.project_snapshot import ProjectDirectory, ProjectSnapshot

logger = logging.getLogger(__name__)


class ProjectInspector:
    """
    Inspector de snapshots del proyecto.

    Root por defecto: PROJECT_ROOT (orquestador / cwd de trabajo).
    TARGET_PROJECT_ROOT solo si prefer_target=True (producto).
    path explícito (absoluto o relativo al base) tiene prioridad.
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
        "runtime",
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
        return self.inspect_snapshot().to_prompt()

    def inspect_snapshot(
        self,
        path: str | None = None,
        *,
        prefer_target: bool = False,
    ) -> ProjectSnapshot:
        root = self._resolve_root(path, prefer_target=prefer_target)

        if not root.exists():
            logger.warning("Project root no existe: %s", root)

        current_hash = self._compute_project_hash(root)
        cached = self._load_cache()

        if (
            cached
            and cached.get("root") == str(root)
            and cached.get("hash") == current_hash
            and cached.get("snapshot")
        ):
            logger.info("Usando snapshot cacheado | root=%s", root)
            try:
                return ProjectSnapshot.from_dict(cached["snapshot"])
            except Exception:
                logger.exception("No se pudo cargar snapshot desde cache. Se reconstruirá.")

        logger.info("Construyendo nuevo snapshot | root=%s", root)
        snapshot = self._build_snapshot(root)
        self._save_cache(current_hash, snapshot, root)
        return snapshot

    def _resolve_root(
        self,
        path: str | None = None,
        *,
        prefer_target: bool = False,
    ) -> Path:
        base = (
            Path(Config.TARGET_PROJECT_ROOT).expanduser().resolve()
            if prefer_target
            else Path(Config.PROJECT_ROOT).expanduser().resolve()
        )

        if path is None:
            return base

        raw = str(path).strip()
        if not raw or raw in (".", "./"):
            return base

        candidate = Path(raw).expanduser()
        if candidate.is_absolute():
            return candidate.resolve()

        return (base / candidate).resolve()

    # ==========================================================
    # Snapshot
    # ==========================================================

    def _build_snapshot(self, root: Path) -> ProjectSnapshot:
        snapshot = ProjectSnapshot(
            project_name=root.name,
            root_path=str(root),
        )

        if not root.exists():
            return snapshot

        for directory in self._collect_directories(root):
            snapshot.directories.append(directory)

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
                logger.warning("No se pudo leer %s", path)

        return snapshot

    # ==========================================================
    # File collection
    # ==========================================================

    def _collect_all_files(self, root: Path) -> list[Path]:
        result: list[Path] = []
        seen: set[Path] = set()
        root = Path(root).expanduser().resolve()

        for filename in self.PRIORITY_FILES:
            path = root / filename
            if path.exists() and path.is_file():
                result.append(path)
                seen.add(path)

        for directory_name in self.SOURCE_DIRS:
            directory = root / directory_name
            if not directory.exists() or not directory.is_dir():
                continue
            for path in self._walk_controlled(directory, root):
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

    def _collect_directories(self, root: Path) -> list[ProjectDirectory]:
        result: list[ProjectDirectory] = []
        root = Path(root).expanduser().resolve()
        if not root.is_dir():
            return result

        for current, dirs, filenames in os.walk(root):
            current_path = Path(current).resolve()
            dirs[:] = [d for d in dirs if d not in self.EXCLUDED_DIRS]
            if current_path == root:
                continue
            try:
                relative = current_path.relative_to(root)
            except ValueError:
                continue
            if any(part in self.EXCLUDED_DIRS for part in relative.parts):
                continue
            result.append(
                ProjectDirectory(
                    path=str(relative),
                    name=current_path.name,
                    files_count=len(filenames),
                    directories_count=len(dirs),
                )
            )
        return result

    def _walk_controlled(self, directory: Path, root: Path) -> list[Path]:
        files: list[Path] = []
        root = Path(root).resolve()
        directory = Path(directory).resolve()
        if not directory.is_dir():
            return files

        for current, dirs, filenames in os.walk(directory):
            dirs[:] = [d for d in dirs if d not in self.EXCLUDED_DIRS]
            for filename in filenames:
                path = (Path(current) / filename).resolve()
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

    def _compute_project_hash(self, root: Path) -> str:
        hasher = hashlib.sha256()
        hasher.update(str(root).encode("utf-8"))
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
            logger.warning("Cache de proyecto corrupta. Se reconstruirá.")
            return None

    def _save_cache(
        self,
        hash_value: str,
        snapshot: ProjectSnapshot,
        root: Path,
    ) -> None:
        data = {
            "root": str(root),
            "hash": hash_value,
            "snapshot": snapshot.to_dict(),
        }
        try:
            self.CACHE_FILE.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError:
            logger.exception("No se pudo guardar cache del proyecto")
