import os
import re
from pathlib import Path

from core.config import Config


class ObsidianSearch:
    def __init__(self):
        self.vault_path = Path(Config.OBSIDIAN_VAULT_PATH).expanduser()

    def search(self, query: str, max_results: int = 5):
        if not self.vault_path.exists():
            return []

        results = []
        query_lower = query.lower()

        for root, _, files in os.walk(self.vault_path):
            for file in files:
                if not file.endswith(".md"):
                    continue
                filepath = Path(root) / file
                try:
                    content = filepath.read_text(encoding="utf-8", errors="ignore")
                    rel_path = str(filepath.relative_to(self.vault_path))

                    score = 0
                    if query_lower in content.lower():
                        score += 50
                    score += len(re.findall(r"\b" + re.escape(query_lower) + r"\b", content.lower())) * 10

                    if score > 0:
                        results.append({"path": rel_path, "score": score, "content": content[:1200]})
                except Exception:
                    continue

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:max_results]

    def build_context(self, query: str) -> str:
        results = self.search(query)
        if not results:
            return ""

        context = ""
        for r in results:
            context += f"📄 {r['path']}\n{r['content']}\n{'-' * 60}\n\n"
        return context
