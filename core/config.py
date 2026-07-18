import logging
import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent

load_dotenv(
    dotenv_path=PROJECT_ROOT / ".env",
)

logger = logging.getLogger(__name__)


class Config:
    PROJECT_ROOT = PROJECT_ROOT
    TARGET_PROJECT_ROOT = PROJECT_ROOT

    # Gemini
    GEMINI_API_KEY = os.getenv(
        "GEMINI_API_KEY",
        "",
    )

    GEMINI_MODEL = os.getenv(
        "GEMINI_MODEL",
        "gemini-2.5-flash",
    )

    # NVIDIA NIM
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

    # Provider routing
    DEFAULT_PROVIDER = (
        os.getenv(
            "DEFAULT_PROVIDER",
            "gemini",
        )
        .strip()
        .lower()
    )

    CODE_PROVIDER = (
        os.getenv(
            "CODE_PROVIDER",
            DEFAULT_PROVIDER,
        )
        .strip()
        .lower()
    )

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

    FALLBACK_PROVIDERS = [
        provider.strip().lower()
        for provider in os.getenv(
            "FALLBACK_PROVIDERS",
            "nim",
        ).split(",")
        if provider.strip()
    ]

    SHELL_TIMEOUT = int(os.getenv("SHELL_TIMEOUT", "180"))
    DOCKER_TIMEOUT = int(os.getenv("DOCKER_TIMEOUT", "120"))

    # Obsidian
    OBSIDIAN_VAULT_PATH = Path(
        os.getenv(
            "OBSIDIAN_VAULT_PATH",
            str(PROJECT_ROOT / "obsidian_vault"),
        )
    ).expanduser()

    @classmethod
    def validate(cls) -> None:
        if not cls.GEMINI_API_KEY:
            logger.warning("GEMINI_API_KEY no configurada.")

        if not cls.NVIDIA_API_KEY:
            logger.warning("NVIDIA_API_KEY no configurada.")

        logger.info(
            "Configuración LLM | default=%s | code=%s | "
            "architecture=%s | fallbacks=%s",
            cls.DEFAULT_PROVIDER,
            cls.CODE_PROVIDER,
            cls.ARCHITECTURE_PROVIDER,
            cls.FALLBACK_PROVIDERS,
        )

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
