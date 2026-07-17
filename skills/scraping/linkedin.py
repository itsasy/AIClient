from skills.base import Skill
import requests
from bs4 import BeautifulSoup


class LinkedInScraperSkill(Skill):
    name = "linkedin_scrape"
    description = "Extrae información de LinkedIn de forma básica"

    def execute(self, url: str, **kwargs):
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, "html.parser")

            title = soup.find("title").text if soup.find("title") else "Sin título"
            summary = soup.find("meta", attrs={"name": "description"})
            summary = summary["content"] if summary else "Sin descripción"

            return {
                "type": "linkedin_result",
                "payload": {
                    "ok": True,
                    "title": title,
                    "summary": summary[:500],
                    "url": url,
                },
            }
        except Exception as e:
            return {
                "type": "linkedin_result",
                "payload": {"ok": False, "error": str(e)},
            }
