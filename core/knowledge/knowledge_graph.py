from core.config import Config
import json
from pathlib import Path
from collections import defaultdict


class KnowledgeGraph:
    def __init__(self):
        self.file = Config.PROJECT_ROOT / ".knowledge.json"
        self.graph = self._load()

    def _load(self):
        if self.file.exists():
            try:
                return json.loads(self.file.read_text(encoding="utf-8"))
            except:
                return defaultdict(dict)
        return defaultdict(dict)

    def add_knowledge(self, key: str, value: str, relation: str = "related"):
        self.graph[key][relation] = value
        self._save()

    def _save(self):
        self.file.write_text(
            json.dumps(self.graph, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def get(self, key: str):
        return self.graph.get(key, {})
