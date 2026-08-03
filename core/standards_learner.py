from typing import Dict

from core.config import Config
import json


class StandardsLearner:

    def __init__(self):

        self.file = Config.PROJECT_ROOT / ".standards.json"

        self.standards: Dict[str, str] = self._load()

    def _load(self):

        if not self.file.exists():
            return {}

        try:

            return json.loads(self.file.read_text(encoding="utf-8"))

        except Exception:

            return {}

    def learn(
        self,
        key: str,
        value: str,
    ) -> None:

        self.standards[key] = value

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

        return self.standards
