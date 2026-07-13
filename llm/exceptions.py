class LLMProviderError(Exception):
    """Error base producido por un proveedor LLM."""


class LLMProviderUnavailableError(LLMProviderError):
    """El proveedor no está disponible temporalmente."""


class LLMProviderConfigurationError(LLMProviderError):
    """El proveedor no está correctamente configurado."""