from __future__ import annotations

import json
import logging
import re
from typing import Any

from agents.base import Agent
from core.execution_plan import ExecutionPlan
from core.execution_step import ExecutionStep
from llm.router import LLMRouter

logger = logging.getLogger(__name__)


class CoderAgent(Agent):
    """
    Genera artefactos de código.

    Responsabilidad:
        - Razonar sobre la tarea.
        - Producir contenido listo para ser escrito por Skills.
        - NO escribir archivos.
        - NO ejecutar shell.
    """

    name = "coder"
    role = "Generador e Implementador de Código"
    version = "2.1"
    capabilities = (
        "code_generation",
        "implementation",
    )

    def process(
        self,
        plan: ExecutionPlan,
        step: ExecutionStep,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        context = dict(context or {})

        agent_context = {
            **context,
            "agent_role": {
                "name": self.name,
                "responsibility": (
                    "Implementar soluciones técnicas siguiendo el "
                    "ExecutionPlan. Debes devolver SOLO un JSON válido "
                    "con los archivos a crear/modificar."
                ),
                "priorities": [
                    "Código limpio",
                    "Buenas prácticas",
                    "Testing",
                    "Seguridad",
                    "Legibilidad",
                    "Compatibilidad con arquitectura existente",
                ],
            },
            "requested_output": {
                "format": "json",
                "schema": {
                    "type": "code_artifact",
                    "files": [
                        {
                            "path": "ruta/relativa.ext",
                            "content": "contenido completo del archivo",
                        }
                    ],
                    "notes": "comentarios opcionales",
                },
                "rules": [
                    "Devuelve ÚNICAMENTE JSON válido.",
                    "No uses markdown ni bloques ```.",
                    "No inventes rutas fuera del proyecto.",
                    "Cada 'content' debe ser el archivo completo.",
                ],
            },
        }

        raw = LLMRouter().generate(
            plan=plan,
            context=agent_context,
        )

        artifact = self._parse_artifact(raw)

        if artifact is None:
            logger.warning(
                "CoderAgent no pudo parsear JSON. " "Se devuelve fallback de texto libre."
            )
            return {
                "ok": False,
                "type": "code_artifact",
                "files": [],
                "raw": raw,
                "error": "Respuesta del modelo no es un code_artifact válido.",
            }

        return {
            "ok": True,
            "type": "code_artifact",
            "files": artifact.get("files", []),
            "notes": artifact.get("notes", ""),
            "error": None,
        }

    def validate_plan(self, plan: ExecutionPlan) -> list[str]:
        errors: list[str] = []
        if not plan.params.get("task") and not plan.original_task:
            errors.append("CoderAgent requiere una tarea de implementación.")
        return errors

    @staticmethod
    def _parse_artifact(raw: str) -> dict[str, Any] | None:
        if not raw or not isinstance(raw, str):
            return None

        text = raw.strip()

        # Quitar fences accidentales
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            # Intentar extraer el primer objeto JSON
            match = re.search(r"\{[\s\S]*\}", text)
            if not match:
                return None
            try:
                data = json.loads(match.group(0))
            except json.JSONDecodeError:
                return None

        if not isinstance(data, dict):
            return None

        files = data.get("files")
        if not isinstance(files, list):
            return None

        normalized_files = []
        for item in files:
            if not isinstance(item, dict):
                continue
            path = item.get("path")
            content = item.get("content")
            if isinstance(path, str) and path.strip() and content is not None:
                normalized_files.append(
                    {
                        "path": path.strip(),
                        "content": str(content),
                    }
                )

        if not normalized_files:
            return None

        return {
            "type": "code_artifact",
            "files": normalized_files,
            "notes": str(data.get("notes", "") or ""),
        }
