from skills.base import Skill
import requests
from bs4 import BeautifulSoup


class FreelanceScraperSkill(Skill):
    name = "scrape_job"
    description = "Analiza trabajos en LinkedIn y Workana"

    def execute(self, url: str, platform: str = "linkedin", **kwargs):
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, "html.parser")

            title = soup.find("title").text if soup.find("title") else "Sin título"
            description = soup.get_text()[:1500]

            pain_points = self._analyze_pain(description)

            return {
                "type": "job_analysis",
                "payload": {
                    "ok": True,
                    "platform": platform,
                    "title": title,
                    "description": description,
                    "pain_points": pain_points,
                    "url": url,
                },
            }
        except Exception as e:
            return {"type": "job_analysis", "payload": {"ok": False, "error": str(e)}}

    def _analyze_pain(self, text: str):
        pain_keywords = [
            "problema",
            "error",
            "necesito",
            "busco",
            "ayuda",
            "solucionar",
            "urgente",
        ]
        return [word for word in pain_keywords if word in text.lower()]
