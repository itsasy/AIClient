import os
from dotenv import load_dotenv
from pathlib import Path
import logging

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Config:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    NIM_API_KEY = os.getenv("NIM_API_KEY")
    NIM_BASE_URL = os.getenv("NIM_BASE_URL", "https://integrate.api.nvidia.com/v1")
    
    OBSIDIAN_VAULT_PATH = Path(os.getenv("OBSIDIAN_VAULT_PATH", "~/Workspace/Obsidian")).expanduser()
    PROJECT_ROOT = Path("/home/alexis/Workspace/AIClient")
    
    @classmethod
    def validate(cls):
        if not cls.GEMINI_API_KEY:
            logger.warning("GEMINI_API_KEY no configurada")
        if not cls.OBSIDIAN_VAULT_PATH.exists():
            logger.warning(f"Obsidian no encontrado en {cls.OBSIDIAN_VAULT_PATH}")
        else:
            logger.info(f"Obsidian encontrado ({len(list(cls.OBSIDIAN_VAULT_PATH.glob('**/*.md')))} archivos .md)")
