import json
from datetime import datetime
from pathlib import Path

from core.config import Config


class ConversationMemory:
    def __init__(self):
        self.file = Config.PROJECT_ROOT / ".history.json"
        self.history = self._load()

    def _load(self):
        if self.file.exists():
            try:
                return json.loads(self.file.read_text(encoding="utf-8"))
            except Exception:
                return []
        return []

    def add(self, user: str, ai: str):
        self.history.append(
            {
                "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "user": user,
                "ai": ai[:800],
            }
        )
        self._save()

    def _save(self):
        self.file.write_text(json.dumps(self.history[-20:], indent=2, ensure_ascii=False), encoding="utf-8")

    def get_context(self) -> str:
        if not self.history:
            return ""
        ctx = "=== HISTORIAL RECIENTE ===\n"
        for h in self.history[-4:]:
            ctx += f"{h['time']} Tú: {h['user']}\nAI: {h['ai']}\n\n"
        return ctx
