import logging
import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent

load_dotenv(
    dotenv_path=PROJECT_ROOT / ".env",
    override=False,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


class Config:
    PROJECT_ROOT = PROJECT_ROOT

    # Gemini
    GEMINI_API_KEY = os.getenv(
        "GEMINI_API_KEY",
        "",
    ).strip()

    GEMINI_MODEL = os.getenv(
        "GEMINI_MODEL",
        "gemini-2.5-flash",
    ).strip()

    # NVIDIA NIM
    NVIDIA_API_KEY = os.getenv(
        "NVIDIA_API_KEY",
        "",
    ).strip()

    NVIDIA_BASE_URL = os.getenv(
        "NVIDIA_BASE_URL",
        "https://integrate.api.nvidia.com/v1",
    ).strip()

    NVIDIA_MODEL = os.getenv(
        "NVIDIA_MODEL",
        "meta/llama-3.1-70b-instruct",
    ).strip()

    # Provider priority
    DEFAULT_PROVIDER = os.getenv(
        "DEFAULT_PROVIDER",
        "gemini",
    ).strip().lower()

    FALLBACK_PROVIDERS = [
        provider.strip().lower()
        for provider in os.getenv(
            "FALLBACK_PROVIDERS",
            "nim",
        ).split(",")
        if provider.strip()
    ]

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
            logger.warning(
                "GEMINI_API_KEY no configurada. "
                "Gemini no podrá utilizarse."
            )

        if not cls.NVIDIA_API_KEY:
            logger.warning(
                "NVIDIA_API_KEY no configurada. "
                "NVIDIA NIM no podrá utilizarse."
            )

        logger.info(
            "Configuración de providers | Principal: %s | Fallbacks: %s",
            cls.DEFAULT_PROVIDER,
            ", ".join(cls.FALLBACK_PROVIDERS) or "ninguno",
        )

        if not cls.OBSIDIAN_VAULT_PATH.exists():
            logger.warning(
                "Obsidian no encontrado en %s",
                cls.OBSIDIAN_VAULT_PATH,
            )
            return

        markdown_files = list(
            cls.OBSIDIAN_VAULT_PATH.glob("**/*.md")
        )

        logger.info(
            "Obsidian encontrado (%s archivos .md)",
            len(markdown_files),
        )