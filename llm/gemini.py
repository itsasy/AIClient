from google import genai
from google.genai.types import Part
from .base import LLMProvider
from core.config import Config

class GeminiProvider(LLMProvider):
    def __init__(self):
        self.client = genai.Client(api_key=Config.GEMINI_API_KEY)
    
    def generate(self, prompt: str, **kwargs) -> str:
        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",   # o gemini-1.5-flash
                contents=[prompt]
            )
            return response.text
        except Exception as e:
            return f"Error Gemini: {str(e)}"
