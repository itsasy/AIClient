from __future__ import annotations

import json
import tempfile
from pathlib import Path

from core.config import Config


class StandardsLearner:
    """
    Guarda preferencias aprendidas del usuario.
    """

    def __init__(self):

        self.file = Config.PROJECT_ROOT / ".standards.json"

        self.standards: dict[str, str] = self._load()

    def _load(self) -> dict[str, str]:

        if not self.file.exists():
            return {}

        try:

            data = json.loads(self.file.read_text(encoding="utf-8"))

            if isinstance(data, dict):
                return data

        except Exception:

            pass

        return {}

    def learn(
        self,
        key: str,
        value: str,
    ) -> None:

        key = key.strip().lower()

        if not key:
            raise ValueError("La clave no puede estar vacía")

        self.standards[key] = value.strip()

        self._save()

    def forget(
        self,
        key: str,
    ) -> None:

        self.standards.pop(
            key,
            None,
        )

        self._save()

    def _save(self):

        self.file.write_text(
            json.dumps(
                self.standards,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    def get(
        self,
        key: str,
    ) -> str:

        return self.standards.get(
            key,
            "No definido aún",
        )

    def list_standards(self) -> dict[str, str]:

        return dict(self.standards)
