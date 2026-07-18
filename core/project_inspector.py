import hashlib
import json
import os
from pathlib import Path

from core.config import Config
from core.project_snapshot import ProjectSnapshot


class ProjectInspector:
    MAX_FILE_CHARS = 3000
    MAX_SOURCE_FILES = 20
    CACHE_FILE = Config.PROJECT_ROOT / ".project_cache.json"

    EXCLUDED_DIRS = {".git", ".venv", "__pycache__", ".pytest_cache"}
    INCLUDED_EXTENSIONS = {
        ".py",
        ".toml",
        ".md",
        ".php",
        ".json",
        ".js",
        ".css",
        ".html",
        ".yml",
        ".yaml",
        ".xml",
        ".sh",
        ".env",
        ".lock",
        ".ini",
        ".vue",
        ".ts",
        ".jsx",
        ".tsx",
    }
    PRIORITY_FILES = ("README.md", "pyproject.toml")
    SOURCE_DIRS = ("core", "llm", "skills", "agents", "obsidian", "cli", "tests")

    def inspect(self) -> str:
        return self.inspect_snapshot().to_prompt()

    def inspect_snapshot(self) -> ProjectSnapshot:
        root = Config.TARGET_PROJECT_ROOT
        current_hash = self._compute_project_hash(root)

        cached = self._load_cache()
        if cached and cached.get("hash") == current_hash:
            return ProjectSnapshot.from_dict(cached["snapshot"])

        snapshot = self._build_snapshot(root)
        self._save_cache(current_hash, snapshot)
        return snapshot

    def _build_snapshot(self, root: Path) -> ProjectSnapshot:
        snapshot = ProjectSnapshot(root=root.name)
        if not root.exists():
            return snapshot

        all_files = self._collect_all_files(root)
        for path in all_files[: self.MAX_SOURCE_FILES]:
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")[
                    : self.MAX_FILE_CHARS
                ]
                snapshot.add_file(path=str(path.relative_to(root)), content=content)
            except OSError:
                continue
        return snapshot

    def _collect_all_files(self, root: Path) -> list[Path]:
        files: list[Path] = []

        for filename in self.PRIORITY_FILES:
            path = root / filename
            if path.exists() and path.is_file():
                files.append(path)

        for dir_name in self.SOURCE_DIRS:
            directory = root / dir_name
            if not directory.exists() or not directory.is_dir():
                continue
            for path in sorted(directory.rglob("*")):
                if not path.is_file():
                    continue
                relative_parts = path.relative_to(root).parts
                if any(part in self.EXCLUDED_DIRS for part in relative_parts):
                    continue
                if path.suffix.lower() not in self.INCLUDED_EXTENSIONS:
                    continue
                if path not in files:
                    files.append(path)
        return files

    def _compute_project_hash(self, root: Path) -> str:
        hasher = hashlib.md5()
        for path in sorted(root.rglob("*")):
            if path.is_file():
                try:
                    stat = path.stat()
                    hasher.update(f"{path}{stat.st_size}{stat.st_mtime}".encode())
                except OSError:
                    continue
        return hasher.hexdigest()

    def _load_cache(self) -> dict | None:
        if not self.CACHE_FILE.exists():
            return None
        try:
            data = json.loads(self.CACHE_FILE.read_text(encoding="utf-8"))
            if data.get("root") == str(Config.TARGET_PROJECT_ROOT):
                return data
        except (json.JSONDecodeError, OSError):
            pass
        return None

    def _save_cache(self, hash_value: str, snapshot: ProjectSnapshot) -> None:
        data = {
            "root": str(Config.TARGET_PROJECT_ROOT),
            "hash": hash_value,
            "snapshot": snapshot.to_dict(),
        }
        try:
            self.CACHE_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except OSError:
            pass
