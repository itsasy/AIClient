import requests
from .base import LLMProvider
from core.config import Config

class NIMProvider(LLMProvider):
    def __init__(self):
        self.api_key = Config.NIM_API_KEY
        self.base_url = Config.NIM_BASE_URL
    
    def generate(self, prompt: str, **kwargs) -> str:
        if not self.api_key:
            return "NIM_API_KEY no configurada"
        # Implementación simplificada (puedes completarla después)
        return "NIM no implementado completamente aún. Usa --model gemini"
