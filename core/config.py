import logging
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - entorno sin dependency
    def load_dotenv(*args, **kwargs):
        return False

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_CANDIDATES = [PROJECT_ROOT / ".env", PROJECT_ROOT / "config" / ".env"]

for env_path in ENV_CANDIDATES:
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
        break

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class Config:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    NIM_API_KEY = os.getenv("NIM_API_KEY")
    NIM_BASE_URL = os.getenv("NIM_BASE_URL", "https://integrate.api.nvidia.com/v1")

    OBSIDIAN_VAULT_PATH = Path(os.getenv("OBSIDIAN_VAULT_PATH", str(PROJECT_ROOT / "obsidian_vault"))).expanduser()
    PROJECT_ROOT = PROJECT_ROOT

    @classmethod
    def validate(cls):
        if not cls.GEMINI_API_KEY:
            logger.warning("GEMINI_API_KEY no configurada")
        if not cls.OBSIDIAN_VAULT_PATH.exists():
            logger.warning(f"Obsidian no encontrado en {cls.OBSIDIAN_VAULT_PATH}")
        else:
            logger.info(f"Obsidian encontrado ({len(list(cls.OBSIDIAN_VAULT_PATH.glob('**/*.md')))} archivos .md)")
