from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.config import Config
from core.engram_memory import EngramMemory
from core.standards_learner import StandardsLearner
from core.execution_plan import ExecutionPlan
from llm.provider_selector import ProviderSelector
from llm.provider_manager import ProviderManager

logger = logging.getLogger(__name__)


class ContinuousLearner:
    """
    Detecta correcciones/preferencias en el texto del usuario.

    Fase B:
        - extract_and_learn → solo CANDIDATO pendiente
        - approve_candidate → persiste estándar de verdad
        - reject_candidate → descarta

    No escribe standards/Engram estable sin aprobación.
    """

    PENDING_DIR = Path(getattr(Config, "PROJECT_ROOT", Path("."))) / ".memory" / "learning"

    def __init__(self) -> None:
        self.standards = StandardsLearner()
        self.engram = EngramMemory()
        self.provider_manager = ProviderManager()
        self.backend = getattr(Config, "LEARNER_BACKEND", "both")

        self.PENDING_DIR.mkdir(parents=True, exist_ok=True)

        logger.info(
            "ContinuousLearner inicializado (backend: %s | pending=%s)",
            self.backend,
            self.PENDING_DIR,
        )

    # =========================================================
    # Public API
    # =========================================================

    def extract_and_learn(
        self,
        user_query: str,
        assistant_response: str,
    ) -> bool:
        """
        Si el usuario expresa una preferencia/corrección explícita,
        crea un candidato pendiente. No persiste el estándar aún.
        """
        if not user_query or not user_query.strip():
            return False

        learn_patterns = [
            r"(aprende|recuerda|guarda|almacena)\s+que\s+(.+?)(?:\.|$)",
            r"(prefiero|prefieres|mejor usar|mejor utiliza)\s+(.+?)(?:\.|$)",
            r"(corrección|corrige|error|debiste|deberías)\s+(.+?)(?:\.|$)",
            r"(estándar|standard|norma)\s+es\s+(.+?)(?:\.|$)",
        ]

        for pattern in learn_patterns:
            match = re.search(pattern, user_query.lower())
            if not match:
                continue

            raw_text = match.group(2).strip()
            return self._propose_from_text(
                raw_text=raw_text,
                original_query=user_query,
                assistant_response=assistant_response or "",
            )

        return False

    def list_pending(self) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for path in sorted(self.PENDING_DIR.glob("pending-*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                data["_path"] = str(path)
                items.append(data)
            except Exception:
                logger.exception("No se pudo leer candidato %s", path)
        return items

    def approve_candidate(self, candidate_id: str) -> bool:
        path = self._pending_path(candidate_id)
        if not path.exists():
            logger.warning("Candidato no encontrado: %s", candidate_id)
            return False

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            logger.exception("Candidato ilegible: %s", candidate_id)
            return False

        key = str(data.get("key") or "").strip()
        value = str(data.get("value") or "").strip()
        if not key or not value:
            logger.warning("Candidato sin key/value: %s", candidate_id)
            return False

        self._persist_standard(
            key=key,
            value=value,
            original_query=str(data.get("original_query") or ""),
            raw_text=str(data.get("raw_text") or ""),
        )

        done = path.with_name(path.name.replace("pending-", "done-", 1))
        path.rename(done)
        logger.info("Candidato aprobado: %s → %s=%s", candidate_id, key, value)
        return True

    def reject_candidate(self, candidate_id: str) -> bool:
        path = self._pending_path(candidate_id)
        if not path.exists():
            logger.warning("Candidato no encontrado: %s", candidate_id)
            return False

        rejected = path.with_name(path.name.replace("pending-", "rejected-", 1))
        path.rename(rejected)
        logger.info("Candidato rechazado: %s", candidate_id)
        return True

    # =========================================================
    # Proposal (no persist estable)
    # =========================================================

    def _propose_from_text(
        self,
        raw_text: str,
        original_query: str,
        assistant_response: str,
    ) -> bool:
        extracted = self._extract_key_value(raw_text)
        if not extracted:
            return False

        key = str(extracted.get("key") or "").strip()
        value = str(extracted.get("value") or "").strip()
        if not key or not value:
            return False

        candidate_id = str(uuid.uuid4())
        payload = {
            "id": candidate_id,
            "status": "pending",
            "key": key,
            "value": value,
            "raw_text": raw_text,
            "original_query": original_query,
            "assistant_response_excerpt": (assistant_response or "")[:500],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "source": "continuous_learner",
        }

        path = self._pending_path(candidate_id)
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        logger.info(
            "Learning candidate pendiente | id=%s | key=%s",
            candidate_id,
            key,
        )
        return True

    def _pending_path(self, candidate_id: str) -> Path:
        return self.PENDING_DIR / f"pending-{candidate_id}.json"

    # =========================================================
    # Persist estable (solo tras approve)
    # =========================================================

    def _persist_standard(
        self,
        key: str,
        value: str,
        original_query: str,
        raw_text: str,
    ) -> None:
        backend = self.backend

        if backend in ("legacy", "both"):
            self.standards.learn(key, value)

        if backend in ("engram", "both"):
            content = f"Estándar aprendido: {key} = {value}"
            self.engram.save(
                content,
                tags=[
                    "standard",
                    "preference",
                    "continuous_learning",
                    f"key_{key}",
                    "approved",
                ],
                source="continuous_learner",
            )

            context_content = (
                f"Contexto de aprendizaje:\n"
                f"Original: {original_query}\n"
                f"Extraído: {raw_text}\n"
                f"→ {key} = {value}"
            )
            self.engram.save(
                context_content,
                tags=[
                    "learning_context",
                    "trazabilidad",
                    f"key_{key}",
                    "approved",
                ],
                source="continuous_learner",
            )

    # =========================================================
    # LLM extract — adaptá a tu ProviderManager actual
    # =========================================================

    def _extract_key_value(self, text: str) -> dict[str, str] | None:
        """
        Usa el LLM para extraer clave y valor del texto del usuario.
        Devuelve {"key": "...", "value": "..."} o None.
        """
        prompt = f"""
Extrae un estándar o preferencia de aprendizaje del siguiente texto del usuario.

Texto: "{text}"

Devuelve SOLO un JSON válido con dos campos: "key" y "value".

Ejemplo:
{{"key": "framework_preferido", "value": "Vue"}}

Si no se puede extraer, devuelve:
{{"key": null, "value": null}}

REGLAS:
- La "key" debe ser una etiqueta corta y descriptiva (minúsculas, guiones bajos).
- El "value" debe ser el contenido concreto de la preferencia.
- No inventes información que no esté en el texto.
- No uses markdown ni bloques de código.
""".strip()

        try:
            plan = ExecutionPlan(
                original_task="learn_extraction",
                intent="learning",
                intent_category="conversation",
            )

            provider, fallback = ProviderSelector.select(plan)

            try:
                response = self.provider_manager.generate(
                    prompt,
                    provider_name=provider,
                    fallback_chain=fallback,
                )
            except TypeError:
                response = self.provider_manager.generate(
                    prompt,
                    provider_name=provider,
                )

            if not isinstance(response, str):
                response = str(response)

            response = response.strip()

            start = response.find("{")
            end = response.rfind("}") + 1

            if start == -1 or end <= start:
                logger.warning(
                    "Respuesta de extracción sin JSON | raw=%s",
                    response[:200],
                )
                return None

            data = json.loads(response[start:end])

            if not isinstance(data, dict):
                return None

            key = data.get("key")
            value = data.get("value")

            if not key or not value:
                return None

            return {
                "key": str(key).strip(),
                "value": str(value).strip(),
            }

        except Exception:
            logger.exception(
                "No se pudo extraer key/value del texto de aprendizaje",
            )
            return None

    def get_context(self) -> str:
        """
        Estándares ya aprobados (legacy + engram), para prompts.
        Igual que antes; no incluye pendientes.
        """
        lines: list[str] = []
        seen_keys: set[str] = set()
        backend = self.backend

        if backend in ("engram", "both"):
            memories = self.engram.recall("standard preference", limit=10)
            for memory in memories:
                content = memory.get("content", "")
                if not content.startswith("Estándar aprendido:"):
                    continue
                try:
                    parts = content.replace("Estándar aprendido: ", "", 1).split(" = ", 1)
                    if len(parts) == 2:
                        key, value = parts[0].strip(), parts[1].strip()
                        if key not in seen_keys:
                            lines.append(f"- {key}: {value}")
                            seen_keys.add(key)
                except Exception:
                    continue

        if backend in ("legacy", "both"):
            # Si StandardsLearner expone listado, integralo aquí como ya lo tenías
            try:
                for key, value in getattr(self.standards, "all", lambda: {})().items():
                    if key not in seen_keys:
                        lines.append(f"- {key}: {value}")
                        seen_keys.add(key)
            except Exception:
                pass

        return "\n".join(lines)
