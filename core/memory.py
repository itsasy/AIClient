import json
from datetime import datetime

from core.config import Config


class ConversationMemory:
    def __init__(self, project_id: str | None = None):
        project_id = project_id or Config.TARGET_PROJECT_ROOT.name
        memory_dir = Config.PROJECT_ROOT / ".memory"
        memory_dir.mkdir(exist_ok=True)
        self.file = memory_dir / f"{project_id}_history.json"
        self.history = self._load()

    def _load(self) -> list:
        if not self.file.exists():
            return []

        try:
            return json.loads(
                self.file.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError):
            return []

    def add(self, user: str, ai: str) -> None:
        self.history.append(
            {
                "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "user": user,
                "ai": ai[:800],
            }
        )

        self._save()

    def _save(self) -> None:
        self.file.write_text(
            json.dumps(
                self.history[-20:],
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    def get_context(self, max_tokens: int = 2000) -> str:
        if not self.history:
            return ""

        # Aproximación simple: 1 token = ~4 caracteres
        max_chars = max_tokens * 4
        current_chars = 0
        lines = []

        # Recorremos la historia desde el final (más reciente)
        for item in reversed(self.history):
            msg_str = (
                f"{item['time']}\n"
                f"Usuario: {item['user']}\n"
                f"AI: {item['ai']}"
            )
            
            if current_chars + len(msg_str) > max_chars:
                break
                
            lines.insert(0, msg_str)
            current_chars += len(msg_str)

        return "\n\n".join(lines)