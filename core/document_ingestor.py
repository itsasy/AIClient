import logging
import os
from pathlib import Path
from typing import List, Dict, Any, Optional

from core.config import Config
from core.engram_memory import EngramMemory

logger = logging.getLogger(__name__)

try:
    from pypdf import PdfReader

    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    logger.warning("pypdf no instalado. No se podrán leer PDFs.")

try:
    from docx import Document

    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False
    logger.warning("python-docx no instalado. No se podrán leer DOCX.")

try:
    from PIL import Image
    import io

    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False
    logger.warning("Pillow no instalado. No se podrán procesar imágenes.")


class DocumentIngestor:
    """
    Ingestor de documentos: extrae texto de PDF, DOCX, TXT e imágenes.
    Guarda el contenido fragmentado en Engram para búsqueda futura.
    """

    CHUNK_SIZE = 800  # Caracteres por fragmento
    OVERLAP = 100  # Superposición entre fragmentos

    def __init__(self):
        self.engram = EngramMemory()

    def ingest_file(self, filepath: Path, tags: List[str] = None) -> bool:
        """
        Ingiere un archivo y guarda su contenido en Engram.

        Args:
            filepath: Ruta al archivo.
            tags: Etiquetas adicionales para los fragmentos.

        Returns:
            bool: True si se ingirió correctamente.
        """
        if not filepath.exists():
            logger.error("Archivo no encontrado: %s", filepath)
            return False

        ext = filepath.suffix.lower()
        filename = filepath.name

        # Tags base
        base_tags = ["document", "ingested", f"ext_{ext[1:]}", f"file_{filename}"]
        if tags:
            base_tags.extend(tags)

        try:
            if ext == ".pdf":
                content = self._extract_pdf(filepath)
            elif ext == ".docx":
                content = self._extract_docx(filepath)
            elif ext == ".txt":
                content = self._extract_txt(filepath)
            elif ext in (".png", ".jpg", ".jpeg", ".gif", ".bmp"):
                content = self._describe_image(filepath)
            else:
                logger.warning("Formato no soportado: %s", ext)
                return False

            if not content:
                logger.warning("No se extrajo contenido de: %s", filename)
                return False

            # Dividir en fragmentos y guardar
            chunks = self._chunk_text(content)
            for i, chunk in enumerate(chunks):
                chunk_tags = base_tags + [f"chunk_{i}"]
                self.engram.save(
                    f"Documento: {filename}\n\n{chunk}",
                    tags=chunk_tags,
                    source=f"ingestor_{ext[1:]}",
                    async_mode=False,
                )

            logger.info("✅ Documento ingerido: %s (%d fragmentos)", filename, len(chunks))
            return True

        except Exception as e:
            logger.exception("Error ingiriendo %s: %s", filename, e)
            return False

    def _extract_pdf(self, filepath: Path) -> str:
        """Extrae texto de un PDF."""
        if not PDF_AVAILABLE:
            raise ImportError("pypdf no instalado")
        reader = PdfReader(filepath)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text

    def _extract_docx(self, filepath: Path) -> str:
        """Extrae texto de un DOCX."""
        if not DOCX_AVAILABLE:
            raise ImportError("python-docx no instalado")
        doc = Document(filepath)
        return "\n".join([p.text for p in doc.paragraphs])

    def _extract_txt(self, filepath: Path) -> str:
        """Extrae texto de un archivo TXT."""
        return filepath.read_text(encoding="utf-8", errors="ignore")

    def _describe_image(self, filepath: Path) -> str:
        """
        Describe una imagen usando Gemini Vision.
        Si falla, devuelve una descripción básica con el nombre y dimensiones.
        """
        if not PILLOW_AVAILABLE:
            return f"Imagen: {filepath.name} (no se pudo procesar sin Pillow)"

        try:
            # Importar cliente de Gemini directamente (usando google-genai)
            from google import genai
            from google.genai.types import Part

            # Leer la imagen con Pillow
            img = Image.open(filepath)
            # Convertir a bytes (formato PNG para mantener calidad)
            img_bytes = io.BytesIO()
            img.save(img_bytes, format="PNG")
            img_data = img_bytes.getvalue()

            # Crear cliente de Gemini (usará la API key de Config)
            client = genai.Client(api_key=Config.GEMINI_API_KEY)

            # Prompt en español para la descripción
            prompt = """
            Describe esta imagen en detalle. Incluye:
            - El contexto o escena general.
            - Colores predominantes y composición.
            - Objetos, personas o elementos principales.
            - Cualquier texto visible (léelo si es posible).
            - El estilo o tipo de imagen (fotografía, ilustración, captura de pantalla, etc.).
            Sé conciso pero informativo, en español.
            """

            # Enviar la solicitud con la imagen
            response = client.models.generate_content(
                model=Config.GEMINI_VISION_MODEL,
                contents=[Part.from_bytes(data=img_data, mime_type="image/png"), prompt],
            )

            description = response.text.strip()
            if description:
                return f"📷 Imagen: {filepath.name}\nDescripción: {description}"
            else:
                return f"Imagen: {filepath.name} (Gemini no devolvió descripción)"

        except ImportError as e:
            logger.warning("No se pudo importar genai o Pillow: %s", e)
            return f"Imagen: {filepath.name} (dependencias faltantes)"
        except Exception as e:
            logger.warning("Error describiendo imagen con Gemini: %s", e)
            return f"Imagen: {filepath.name} (no se pudo describir automáticamente: {str(e)[:100]})"

    def _chunk_text(self, text: str) -> List[str]:
        """Divide el texto en fragmentos superpuestos."""
        if len(text) <= self.CHUNK_SIZE:
            return [text.strip()]

        chunks = []
        start = 0
        while start < len(text):
            end = min(start + self.CHUNK_SIZE, len(text))
            # Intentar cortar en un espacio o salto de línea
            if end < len(text):
                # Buscar el último espacio o salto de línea en los últimos 50 caracteres
                search_start = max(start, end - 50)
                last_space = text.rfind(" ", search_start, end)
                last_newline = text.rfind("\n", search_start, end)
                cut_at = max(last_space, last_newline)
                if cut_at > start:
                    end = cut_at
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            start = max(start + 1, end - self.OVERLAP)  # Avanzar con solapamiento
            if start >= len(text):
                break
        return chunks

    def list_ingested(self) -> List[Dict]:
        """Lista los documentos ingeridos (basado en tags)."""
        memories = self.engram.recall("document ingested", limit=50)
        files = {}
        for m in memories:
            # Extraer nombre del archivo de los tags o del contenido
            content = m.get("content", "")
            if content.startswith("[") and "]" in content:
                filename = content[1 : content.index("]")]
                if filename not in files:
                    files[filename] = {"name": filename, "chunks": 0}
                files[filename]["chunks"] += 1
        return list(files.values())
