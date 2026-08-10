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

    Contrato de salida preferido:
        {
          "ok": true,
          "type": "code_artifact",
          "files": [{"path": "...", "content": "..."}],
          "notes": "...",
          "error": null
        }
    """

    name = "coder"
    role = "Generador e Implementador de Código"
    version = "2.2"
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
        params = dict(step.params or {})

        target_path = (
            params.get("path")
            or plan.params.get("path")
            or self._guess_path_from_task(plan.original_task or "")
            or ""
        )

        agent_context = {
            **context,
            "agent_role": {
                "name": self.name,
                "responsibility": (
                    "Implementar soluciones técnicas siguiendo el ExecutionPlan. "
                    "Debes devolver ÚNICAMENTE un JSON válido con los archivos "
                    "a crear o modificar. Sin markdown. Sin explicaciones fuera del JSON."
                ),
                "priorities": [
                    "Código limpio y completo",
                    "Buenas prácticas",
                    "Seguridad",
                    "Legibilidad",
                    "Compatibilidad con la tarea solicitada",
                ],
            },
            "requested_output": {
                "format": "json_only",
                "schema": {
                    "type": "code_artifact",
                    "files": [
                        {
                            "path": target_path or "ruta/relativa.ext",
                            "content": "contenido completo del archivo",
                        }
                    ],
                    "notes": "opcional",
                },
                "rules": [
                    "Devuelve ÚNICAMENTE JSON válido.",
                    "No uses bloques ``` ni markdown.",
                    "No inventes rutas fuera del proyecto.",
                    "Cada 'content' debe ser el archivo completo, listo para escribir.",
                    (
                        f'Si la tarea pide un archivo concreto, usa path="{target_path}".'
                        if target_path
                        else "Incluye un path relativo razonable."
                    ),
                ],
            },
            "coding_task": {
                "task": plan.original_task or params.get("task", ""),
                "suggested_path": target_path,
            },
        }

        # Evitar que el prompt se hinche con snapshots enormes irrelevantes
        for heavy_key in (
            "project",
            "project_analysis",
            "architecture",
            "documents",
            "obsidian",
            "swarmforge",
        ):
            agent_context.pop(heavy_key, None)

        raw = LLMRouter().generate(
            plan=plan,
            context=agent_context,
        )

        artifact = self._parse_artifact(raw, fallback_path=target_path)

        if artifact is None:
            logger.warning(
                "CoderAgent no pudo construir code_artifact. " "raw_chars=%s path=%s",
                len(raw or ""),
                target_path,
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
            "files": artifact["files"],
            "notes": artifact.get("notes", ""),
            "error": None,
        }

    def validate_plan(self, plan: ExecutionPlan) -> list[str]:
        errors: list[str] = []
        if not plan.params.get("task") and not plan.original_task:
            errors.append("CoderAgent requiere una tarea de implementación.")
        return errors

    # =========================================================
    # Parsing
    # =========================================================

    def _parse_artifact(
        self,
        raw: str,
        fallback_path: str = "",
    ) -> dict[str, Any] | None:
        if not raw or not isinstance(raw, str):
            return None

        text = raw.strip()

        # Quitar fences accidentales
        if "```" in text:
            text = re.sub(r"^```(?:json|html|python|javascript|css)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
            text = text.strip()

        data = self._try_load_json(text)

        if data is not None:
            files = self._normalize_files(data, fallback_path=fallback_path)
            if files:
                return {
                    "type": "code_artifact",
                    "files": files,
                    "notes": str(data.get("notes", "") or ""),
                }

        # Fallback: texto libre + path conocido → un solo archivo
        if fallback_path and text and not text.startswith("{"):
            logger.info(
                "CoderAgent fallback texto libre → code_artifact | path=%s",
                fallback_path,
            )
            return {
                "type": "code_artifact",
                "files": [
                    {
                        "path": fallback_path,
                        "content": text,
                    }
                ],
                "notes": "fallback_raw_text",
            }

        # Último intento: extraer HTML/código entre delimitadores obvios
        html_match = re.search(
            r"(<!DOCTYPE html>[\s\S]*?</html>)",
            raw,
            re.IGNORECASE,
        )
        if html_match and fallback_path:
            return {
                "type": "code_artifact",
                "files": [
                    {
                        "path": fallback_path,
                        "content": html_match.group(1).strip(),
                    }
                ],
                "notes": "fallback_html_extract",
            }

        return None

    @staticmethod
    def _try_load_json(text: str) -> dict[str, Any] | None:
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass

        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            return None

        try:
            data = json.loads(match.group(0))
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            return None

        return None

    @staticmethod
    def _normalize_files(
        data: dict[str, Any],
        fallback_path: str = "",
    ) -> list[dict[str, str]]:
        files_raw = data.get("files")

        # Formas alternativas que a veces devuelve el modelo
        if files_raw is None and "path" in data and "content" in data:
            files_raw = [
                {
                    "path": data.get("path"),
                    "content": data.get("content"),
                }
            ]

        if not isinstance(files_raw, list):
            return []

        normalized: list[dict[str, str]] = []
        for item in files_raw:
            if not isinstance(item, dict):
                continue
            path = item.get("path") or fallback_path
            content = item.get("content")
            if isinstance(path, str) and path.strip() and content is not None:
                normalized.append(
                    {
                        "path": path.strip(),
                        "content": str(content),
                    }
                )
        return normalized

    @staticmethod
    def _guess_path_from_task(task: str) -> str:
        if not task:
            return ""
        match = re.search(
            r"\b([a-zA-Z0-9_\-./]+\.[a-zA-Z0-9]+)\b",
            task,
        )
        if match:
            return match.group(1).strip()
        return ""
