from skills.base import Skill
import requests
from bs4 import BeautifulSoup


class FreelanceScraperSkill(Skill):
    name = "scrape_freelance"
    description = "Extrae y analiza trabajos de LinkedIn, Workana, etc."

    def execute(self, url: str, platform: str = "linkedin", **kwargs):
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, "html.parser")

            title = soup.find("title").text if soup.find("title") else "Sin título"
            description = soup.find("meta", attrs={"name": "description"})
            description = (
                description["content"] if description else soup.get_text()[:800]
            )

            # Análisis de dolor del cliente
            pain_points = self._analyze_pain(description)

            return {
                "type": "freelance_analysis",
                "payload": {
                    "ok": True,
                    "platform": platform,
                    "title": title,
                    "description": description[:1000],
                    "pain_points": pain_points,
                    "url": url,
                },
            }
        except Exception as e:
            return {
                "type": "freelance_analysis",
                "payload": {"ok": False, "error": str(e)},
            }

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
        pains = [word for word in pain_keywords if word in text.lower()]
        return pains or ["No se identificaron dolores claros"]
