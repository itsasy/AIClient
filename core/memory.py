import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict

class ConversationMemory:
    def __init__(self):
        self.file = Path("/home/alexis/Workspace/AIClient/.history.json")
        self.history = self._load()
    
    def _load(self):
        if self.file.exists():
            try:
                return json.loads(self.file.read_text())
            except:
                return []
        return []
    
    def add(self, user: str, ai: str):
        self.history.append({
            "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "user": user,
            "ai": ai[:800]
        })
        self._save()
    
    def _save(self):
        self.file.write_text(json.dumps(self.history[-20:], indent=2, ensure_ascii=False))
    
    def get_context(self) -> str:
        if not self.history:
            return ""
        ctx = "=== HISTORIAL RECIENTE ===\n"
        for h in self.history[-4:]:
            ctx += f"{h['time']} Tú: {h['user']}\nAI: {h['ai']}\n\n"
        return ctx
