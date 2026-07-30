import logging
import os
import secrets
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=PROJECT_ROOT / ".env")

logger = logging.getLogger(__name__)


class Config:
    """
    Configuración global del sistema, cargada desde variables de entorno.
    """

    PROJECT_ROOT = PROJECT_ROOT
    TARGET_PROJECT_ROOT = PROJECT_ROOT

    # ----- Gemini -----
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    # ----- Gemini vision -----
    GEMINI_VISION_MODEL = os.getenv("GEMINI_VISION_MODEL", "gemini-2.0-flash-exp")

    # ----- NVIDIA NIM -----
    NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "")
    NVIDIA_BASE_URL = os.getenv(
        "NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1"
    )
    NVIDIA_MODEL = os.getenv("NVIDIA_MODEL", "meta/llama-3.1-70b-instruct")

    # ----- DeepSeek (nuevo) -----
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
    DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    DEEPSEEK_CODER_MODEL = os.getenv("DEEPSEEK_CODER_MODEL", "deepseek-coder")

    # ----- Proveedores primarios por categoría -----
    DEFAULT_PROVIDER = os.getenv("DEFAULT_PROVIDER", "gemini").strip().lower()
    CODE_PROVIDER = os.getenv("CODE_PROVIDER", DEFAULT_PROVIDER).strip().lower()
    ARCHITECTURE_PROVIDER = (
        os.getenv("ARCHITECTURE_PROVIDER", DEFAULT_PROVIDER).strip().lower()
    )
    DOCUMENTATION_PROVIDER = (
        os.getenv("DOCUMENTATION_PROVIDER", DEFAULT_PROVIDER).strip().lower()
    )
    FAST_PROVIDER = os.getenv("FAST_PROVIDER", "gemini_flash")

    # ----- Fallbacks por categoría (listas separadas por coma) -----
    DEFAULT_FALLBACKS = [
        p.strip().lower()
        for p in os.getenv("DEFAULT_FALLBACKS", "nim,deepseek").split(",")
        if p.strip()
    ]
    CODE_FALLBACKS = [
        p.strip().lower()
        for p in os.getenv("CODE_FALLBACKS", "nim,gemini").split(",")
        if p.strip()
    ]
    ARCHITECTURE_FALLBACKS = [
        p.strip().lower()
        for p in os.getenv("ARCHITECTURE_FALLBACKS", "deepseek,nim").split(",")
        if p.strip()
    ]
    FAST_FALLBACKS = [
        p.strip().lower()
        for p in os.getenv("FAST_FALLBACKS", "deepseek").split(",")
        if p.strip()
    ]

    # FALLBACK_PROVIDERS por compatibilidad con código antiguo
    FALLBACK_PROVIDERS = DEFAULT_FALLBACKS

    # ----- Timeouts -----
    SHELL_TIMEOUT = int(os.getenv("SHELL_TIMEOUT", "180"))
    DOCKER_TIMEOUT = int(os.getenv("DOCKER_TIMEOUT", "120"))
    LARAVEL_TIMEOUT = int(os.getenv("LARAVEL_TIMEOUT", "600"))

    # ----- Obsidian -----
    OBSIDIAN_VAULT_PATH = Path(
        os.getenv("OBSIDIAN_VAULT_PATH", str(PROJECT_ROOT / "obsidian_vault"))
    ).expanduser()

    # ----- Dashboard -----
    DASHBOARD_API_KEY = os.getenv("DASHBOARD_API_KEY", "")
    DASHBOARD_DEBUG = os.getenv("DASHBOARD_DEBUG", "false").lower() == "true"
    DASHBOARD_HOST = os.getenv("DASHBOARD_HOST", "127.0.0.1")
    DASHBOARD_PORT = int(os.getenv("DASHBOARD_PORT", "5000"))

    # ----- Sandbox (Docker) -----
    SANDBOX_TIMEOUT = int(os.getenv("SANDBOX_TIMEOUT", "30"))
    SANDBOX_MEMORY = os.getenv("SANDBOX_MEMORY", "128m")
    SANDBOX_CPU = os.getenv("SANDBOX_CPU", "0.5")
    SANDBOX_IMAGE = os.getenv("SANDBOX_IMAGE", "python:3.11-slim")

    # ----- Self-Critic -----
    ENABLE_SELF_CRITIC = os.getenv("ENABLE_SELF_CRITIC", "true").lower() == "true"

    # ----- Continuous Learner -----
    LEARNER_BACKEND = os.getenv("LEARNER_BACKEND", "both")  # "engram", "legacy", "both"

    # ----- Modo de operación: "safe" o "powerful" -----
    POWER_MODE = os.getenv("POWER_MODE", "safe").lower()

    @classmethod
    def validate(cls) -> None:
        """Valida la configuración y genera claves si faltan."""
        if not cls.GEMINI_API_KEY:
            logger.warning("GEMINI_API_KEY no configurada.")

        if not cls.NVIDIA_API_KEY:
            logger.warning("NVIDIA_API_KEY no configurada.")

        if not cls.DEEPSEEK_API_KEY:
            logger.warning("DEEPSEEK_API_KEY no configurada.")

        logger.info(
            "Proveedores primarios | default=%s | code=%s | architecture=%s | fast=%s",
            cls.DEFAULT_PROVIDER,
            cls.CODE_PROVIDER,
            cls.ARCHITECTURE_PROVIDER,
            cls.FAST_PROVIDER,
        )

        logger.info(
            "Fallbacks por categoría | default=%s | code=%s | architecture=%s | fast=%s",
            cls.DEFAULT_FALLBACKS,
            cls.CODE_FALLBACKS,
            cls.ARCHITECTURE_FALLBACKS,
            cls.FAST_FALLBACKS,
        )

        logger.info("Modo de operación: %s", cls.POWER_MODE)

        # Generar API Key para el dashboard si no está definida
        if not cls.DASHBOARD_API_KEY:
            generated_key = secrets.token_urlsafe(32)
            logger.warning(
                "DASHBOARD_API_KEY no configurada. Usando clave generada: %s",
                generated_key,
            )
            cls.DASHBOARD_API_KEY = generated_key

        if not cls.OBSIDIAN_VAULT_PATH.exists():
            logger.warning("Obsidian no encontrado en %s", cls.OBSIDIAN_VAULT_PATH)
        else:
            markdown_files = list(cls.OBSIDIAN_VAULT_PATH.glob("**/*.md"))
            logger.info("Obsidian encontrado (%s archivos .md)", len(markdown_files))
