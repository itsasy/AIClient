from google import genai

from core.config import Config
from llm.base import LLMProvider


class GeminiProvider(LLMProvider):

    def __init__(self):

        self.client = genai.Client(
            api_key=Config.GEMINI_API_KEY
        )

    def generate(self, prompt: str, **kwargs):

        response = self.client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        return response.text