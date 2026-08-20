from __future__ import annotations
import logging
from typing import Any
import requests

from core.config import Config
from llm.base import LLMProvider
from llm.exceptions import ProviderError, ProviderAuthenticationError

logger = logging.getLogger(__name__)

class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def __init__(self) -> None:
        if not Config.ANTHROPIC_API_KEY:
            raise ProviderAuthenticationError("ANTHROPIC_API_KEY no está configurada.")
        self.api_key = Config.ANTHROPIC_API_KEY
        self.model = Config.ANTHROPIC_MODEL

    def generate(self, prompt: str, *, model: str | None = None, system_prompt: str | None = None, temperature: float = 0.2, max_tokens: int = 4096, **kwargs: Any) -> str:
        if not prompt or not prompt.strip():
            raise ProviderError("El prompt no puede estar vacío.")

        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        payload = {
            "model": model or self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        if system_prompt:
            payload["system"] = system_prompt

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            return data["content"][0]["text"].strip()
        except requests.exceptions.RequestException as exc:
            raise ProviderError(f"Error en Anthropic API: {exc}")
