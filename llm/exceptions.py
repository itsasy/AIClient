class LLMError(Exception):
    """
    Excepción base para errores de la capa LLM.
    """


class ProviderError(LLMError):
    """
    Error general producido por un proveedor LLM.
    """


class ProviderUnavailableError(ProviderError):
    """
    El proveedor no está disponible temporalmente.
    """


class ProviderAuthenticationError(ProviderError):
    """
    Las credenciales del proveedor son inválidas
    o no están configuradas.
    """


class ProviderRateLimitError(ProviderUnavailableError):
    """
    El proveedor alcanzó un límite de uso.
    """


class AllProvidersFailedError(LLMError):
    """
    Ningún proveedor pudo completar la solicitud.
    """

    def __init__(self, errors: dict[str, Exception]):
        self.errors = errors

        details = "; ".join(
            f"{provider}: {error}"
            for provider, error in errors.items()
        )

        super().__init__(
            f"Todos los proveedores LLM fallaron. {details}"
        )