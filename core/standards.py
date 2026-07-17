from core.config import Config
import json
from pathlib import Path


class StandardsLearner:
    def __init__(self):
        self.file = Config.PROJECT_ROOT / ".standards.json"
        self.standards = self._load()

    def _load(self):
        if self.file.exists():
            try:
                return json.loads(self.file.read_text())
            except:
                return {}
        return {}

    def learn(self, key: str, value: str):
        self.standards[key] = value
        self._save()

    def _save(self):
        self.file.write_text(json.dumps(self.standards, indent=2))

    def get(self, key: str):
        return self.standards.get(key, "")
