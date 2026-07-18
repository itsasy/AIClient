from pathlib import Path
from core.config import Config
from obsidian.index import ObsidianIndex


class ObsidianSearch:
    def __init__(self):
        self.vault_path = Path(Config.OBSIDIAN_VAULT_PATH).expanduser()
        self.index = ObsidianIndex()

    def search(self, query: str, max_results: int = 5):
        if not self.vault_path.exists():
            return []

        results = self.index.search(query, max_results=max_results)
        formatted = []
        for r in results:
            formatted.append(
                {
                    "path": r["path"],
                    "score": r["score"],
                    "content": r["content"][:1200] if r["content"] else "",
                }
            )
        return formatted

    def build_context(self, query: str) -> str:
        results = self.search(query)
        if not results:
            return ""

        context = ""
        for r in results:
            context += f"📄 {r['path']}\n{r['content']}\n{'-' * 60}\n\n"
        return context
