from __future__ import annotations
import logging
from typing import Any
import requests

from core.config import Config
from llm.base import LLMProvider
from llm.exceptions import ProviderError, ProviderAuthenticationError

logger = logging.getLogger(__name__)

class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self) -> None:
        if not Config.OPENAI_API_KEY:
            raise ProviderAuthenticationError("OPENAI_API_KEY no está configurada.")
        self.api_key = Config.OPENAI_API_KEY
        self.model = Config.OPENAI_MODEL

    def generate(self, prompt: str, *, model: str | None = None, system_prompt: str | None = None, temperature: float = 0.2, max_tokens: int = 4096, **kwargs: Any) -> str:
        if not prompt or not prompt.strip():
            raise ProviderError("El prompt no puede estar vacío.")

        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model or self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
        except requests.exceptions.RequestException as exc:
            raise ProviderError(f"Error en OpenAI API: {exc}")
