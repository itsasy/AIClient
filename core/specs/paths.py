from __future__ import annotations

import re
import unicodedata
from pathlib import Path

from core.config import Config


def specs_dir() -> Path:
    root = Path(getattr(Config, "TARGET_PROJECT_ROOT", Path.cwd()))
    path = root / ".specs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def sanitize_spec_name(name: str, max_len: int = 60) -> str:
    normalized = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    cleaned = re.sub(r"[^a-zA-Z0-9_\-]+", "_", normalized[:max_len]).strip("_")
    return (cleaned or "spec").lower()


def spec_path_for(topic: str) -> str:
    return f".specs/{sanitize_spec_name(topic)}.md"
