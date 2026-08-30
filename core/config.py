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
    ConfiguraciÃ³n global del sistema, cargada desde variables de entorno.
    """

    AVAILABLE_PROVIDERS = {
        "gemini",
        "deepseek",
        "nim",
        "openai",
        "anthropic",
        "groq",
    }

    POWER_MODES = {
        "safe",
        "powerful",
    }

    PROJECT_ROOT = PROJECT_ROOT

    APP_DATA_DIR = Path(
        os.getenv(
            "APP_DATA_DIR",
            str(Path.home() / ".aiclient"),
        )
    ).expanduser()

    TARGET_PROJECT_ROOT = Path(
        os.getenv(
            "TARGET_PROJECT_ROOT",
            str(PROJECT_ROOT),
        )
    ).expanduser()

    # ==========================================================
    # Gemini
    # ==========================================================

    GEMINI_API_KEY = os.getenv(
        "GEMINI_API_KEY",
        "",
    )

    GEMINI_MODEL = os.getenv(
        "GEMINI_MODEL",
        "gemini-2.5-flash",
    )

    GEMINI_VISION_MODEL = os.getenv(
        "GEMINI_VISION_MODEL",
        "gemini-2.0-flash-exp",
    )

    # ==========================================================
    # NVIDIA NIM
    # ==========================================================

    NVIDIA_API_KEY = os.getenv(
        "NVIDIA_API_KEY",
        "",
    )

    NVIDIA_BASE_URL = os.getenv(
        "NVIDIA_BASE_URL",
        "https://integrate.api.nvidia.com/v1",
    )

    NVIDIA_MODEL = os.getenv(
        "NVIDIA_MODEL",
        "meta/llama-3.1-70b-instruct",
    )

    # ==========================================================
    # DeepSeek
    # ==========================================================

    DEEPSEEK_API_KEY = os.getenv(
        "DEEPSEEK_API_KEY",
        "",
    )

    DEEPSEEK_BASE_URL = os.getenv(
        "DEEPSEEK_BASE_URL",
        "https://api.deepseek.com/v1",
    )

    DEEPSEEK_MODEL = os.getenv(
        "DEEPSEEK_MODEL",
        "deepseek-chat",
    )

    DEEPSEEK_CODER_MODEL = os.getenv(
        "DEEPSEEK_CODER_MODEL",
        "deepseek-coder",
    )

    # ==========================================================
    # OpenAI, Anthropic, Groq
    # ==========================================================

    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest")

    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-70b-versatile")

    # ==========================================================
    # Providers por categorÃ­a
    # ==========================================================

    DEFAULT_PROVIDER = (
        os.getenv(
            "DEFAULT_PROVIDER",
            "gemini",
        )
        .strip()
        .lower()
    )

    CODE_PROVIDER = os.getenv("CODE_PROVIDER", DEFAULT_PROVIDER).strip().lower()

    CODE_FALLBACKS = [
        x.strip().lower()
        for x in os.getenv("CODE_FALLBACKS", "gemini,deepseek").split(",")
        if x.strip()
    ]

    ARCHITECTURE_PROVIDER = (
        os.getenv(
            "ARCHITECTURE_PROVIDER",
            DEFAULT_PROVIDER,
        )
        .strip()
        .lower()
    )

    DOCUMENTATION_PROVIDER = (
        os.getenv(
            "DOCUMENTATION_PROVIDER",
            DEFAULT_PROVIDER,
        )
        .strip()
        .lower()
    )

    FAST_PROVIDER = (
        os.getenv(
            "FAST_PROVIDER",
            DEFAULT_PROVIDER,
        )
        .strip()
        .lower()
    )

    # ==========================================================
    # Fallback helpers
    # ==========================================================

    @staticmethod
    def _parse_list(
        value: str,
    ) -> list[str]:

        return [item.strip().lower() for item in value.split(",") if item.strip()]

    # ==========================================================
    # Fallbacks
    # ==========================================================

    DEFAULT_FALLBACKS = _parse_list(
        os.getenv(
            "DEFAULT_FALLBACKS",
            "nim,deepseek",
        )
    )

    CODE_FALLBACKS = _parse_list(
        os.getenv(
            "CODE_FALLBACKS",
            "nim,gemini",
        )
    )

    ARCHITECTURE_FALLBACKS = _parse_list(
        os.getenv(
            "ARCHITECTURE_FALLBACKS",
            "deepseek,nim",
        )
    )

    DOCUMENTATION_FALLBACKS = _parse_list(
        os.getenv(
            "DOCUMENTATION_FALLBACKS",
            "gemini,deepseek",
        )
    )

    FAST_FALLBACKS = _parse_list(
        os.getenv(
            "FAST_FALLBACKS",
            "deepseek",
        )
    )

    # Compatibilidad legacy

    FALLBACK_PROVIDERS = DEFAULT_FALLBACKS

    # ==========================================================
    # Timeouts
    # ==========================================================

    SHELL_TIMEOUT = int(
        os.getenv(
            "SHELL_TIMEOUT",
            "180",
        )
    )

    DOCKER_TIMEOUT = int(
        os.getenv(
            "DOCKER_TIMEOUT",
            "120",
        )
    )

    LARAVEL_TIMEOUT = int(
        os.getenv(
            "LARAVEL_TIMEOUT",
            "600",
        )
    )

    # ==========================================================
    # Obsidian
    # ==========================================================

    OBSIDIAN_VAULT_PATH = Path(
        os.getenv(
            "OBSIDIAN_VAULT_PATH",
            str(PROJECT_ROOT / "obsidian_vault"),
        )
    ).expanduser()

    # ==========================================================
    # Dashboard
    # ==========================================================

    DASHBOARD_API_KEY = os.getenv(
        "DASHBOARD_API_KEY",
        "",
    )

    DASHBOARD_DEBUG = (
        os.getenv(
            "DASHBOARD_DEBUG",
            "false",
        ).lower()
        == "true"
    )

    DASHBOARD_HOST = os.getenv(
        "DASHBOARD_HOST",
        "127.0.0.1",
    )

    DASHBOARD_PORT = int(
        os.getenv(
            "DASHBOARD_PORT",
            "5000",
        )
    )

    # ==========================================================
    # Sandbox
    # ==========================================================

    SANDBOX_TIMEOUT = int(
        os.getenv(
            "SANDBOX_TIMEOUT",
            "30",
        )
    )

    SANDBOX_MEMORY = os.getenv(
        "SANDBOX_MEMORY",
        "128m",
    )

    SANDBOX_CPU = os.getenv(
        "SANDBOX_CPU",
        "0.5",
    )

    SANDBOX_IMAGE = os.getenv(
        "SANDBOX_IMAGE",
        "python:3.11-slim",
    )

    # ==========================================================
    # Sistema
    # ==========================================================

    ENABLE_SELF_CRITIC = (
        os.getenv(
            "ENABLE_SELF_CRITIC",
            "true",
        ).lower()
        == "true"
    )

    LEARNER_BACKEND = os.getenv(
        "LEARNER_BACKEND",
        "both",
    )

    POWER_MODE = os.getenv(
        "POWER_MODE",
        "safe",
    ).lower()

    HF_TOKEN = os.getenv(
        "HF_TOKEN",
        "",
    )

    # ==========================================================
    # Validation
    # ==========================================================

    @classmethod
    def validate_providers(
        cls,
    ) -> None:

        providers = {
            cls.DEFAULT_PROVIDER,
            cls.CODE_PROVIDER,
            cls.ARCHITECTURE_PROVIDER,
            cls.DOCUMENTATION_PROVIDER,
            cls.FAST_PROVIDER,
            *cls.DEFAULT_FALLBACKS,
            *cls.CODE_FALLBACKS,
            *cls.ARCHITECTURE_FALLBACKS,
            *cls.DOCUMENTATION_FALLBACKS,
            *cls.FAST_FALLBACKS,
        }

        invalid = providers - cls.AVAILABLE_PROVIDERS

        if invalid:

            raise ValueError(f"Proveedores LLM invÃ¡lidos: {invalid}")

    @classmethod
    def validate(
        cls,
    ) -> None:

        cls.validate_providers()

        if cls.POWER_MODE not in cls.POWER_MODES:

            logger.warning(
                "POWER_MODE invÃ¡lido '%s'. Usando safe.",
                cls.POWER_MODE,
            )

            cls.POWER_MODE = "safe"

        if not cls.GEMINI_API_KEY:

            logger.warning("GEMINI_API_KEY no configurada.")

        if not cls.NVIDIA_API_KEY:

            logger.warning("NVIDIA_API_KEY no configurada.")

        if not cls.DEEPSEEK_API_KEY:

            logger.warning("DEEPSEEK_API_KEY no configurada.")

        if not cls.HF_TOKEN:

            logger.warning("HF_TOKEN no configurado.")

        logger.info(
            "Providers | default=%s | code=%s | architecture=%s | fast=%s",
            cls.DEFAULT_PROVIDER,
            cls.CODE_PROVIDER,
            cls.ARCHITECTURE_PROVIDER,
            cls.FAST_PROVIDER,
        )

        logger.info(
            "Fallbacks | default=%s | code=%s | architecture=%s | documentation=%s | fast=%s",
            cls.DEFAULT_FALLBACKS,
            cls.CODE_FALLBACKS,
            cls.ARCHITECTURE_FALLBACKS,
            cls.DOCUMENTATION_FALLBACKS,
            cls.FAST_FALLBACKS,
        )

        logger.info(
            "Modo operaciÃ³n: %s",
            cls.POWER_MODE,
        )

        if not cls.DASHBOARD_API_KEY:

            cls.DASHBOARD_API_KEY = secrets.token_urlsafe(32)

            logger.warning("DASHBOARD_API_KEY generada automÃ¡ticamente.")

        if not cls.OBSIDIAN_VAULT_PATH.exists():

            logger.warning(
                "Obsidian no encontrado en %s",
                cls.OBSIDIAN_VAULT_PATH,
            )

        else:

            markdown_files = list(cls.OBSIDIAN_VAULT_PATH.glob("**/*.md"))

            logger.info(
                "Obsidian encontrado (%s archivos .md)",
                len(markdown_files),
            )
