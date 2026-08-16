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
    Genera código y lo normaliza a code_artifact.

    Responsabilidad:
        razonar código → JSON tipado (code_artifact)
        no escribe disco (write_file / skills lo hacen)
    """

    name = "coder"
    role = "Ingeniero de software"
    version = "2.2"
    aliases = ("code", "developer")
    capabilities = (
        "code_generation",
        "code_artifact",
        "ui_generation",
    )

    def process(
        self,
        plan: ExecutionPlan,
        step: ExecutionStep,
        context: dict[str, Any] | None = None,
    ) -> Any:
        context = dict(context or {})
        params = dict(step.params or {})
        task = str(params.get("task") or plan.objective or plan.original_task)

        requested_paths = self._collect_requested_paths(plan, step)
        if requested_paths:
            context["requested_paths"] = requested_paths

        context.setdefault("agent_role", self.role)
        context.setdefault(
            "requested_output",
            (
                "Responde SOLO con JSON code_artifact. "
                'Formato: {"type":"code_artifact","files":[{"path":"...","content":"..."}]}. '
                "En content escapa saltos de línea como \\n (JSON válido estricto)."
            ),
        )
        context["coding_task"] = task

        raw = LLMRouter().generate(plan=plan, context=context)
        artifact = self._parse_artifact(
            raw=raw,
            fallback_paths=requested_paths,
            fallback_path=params.get("path"),
        )
        return artifact

    def _collect_requested_paths(
        self,
        plan: ExecutionPlan,
        step: ExecutionStep,
    ) -> list[str]:
        paths: list[str] = []
        for other in plan.steps:
            if step.id in (other.depends_on or []):
                if other.unit_name == "write_file":
                    p = (other.params or {}).get("path")
                    if p:
                        paths.append(str(p))
        if (step.params or {}).get("path"):
            paths.insert(0, str(step.params["path"]))
        seen: set[str] = set()
        ordered: list[str] = []
        for p in paths:
            if p not in seen:
                seen.add(p)
                ordered.append(p)
        return ordered

    def _parse_artifact(
        self,
        raw: Any,
        fallback_paths: list[str] | None = None,
        fallback_path: str | None = None,
    ) -> dict[str, Any]:
        text = raw if isinstance(raw, str) else json.dumps(raw, ensure_ascii=False)
        text = text.strip()

        fenced = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if fenced:
            text = fenced.group(1).strip()

        data = self._try_load_json(text)
        if data is None:
            m = re.search(r"\{[\s\S]*\}", text)
            if m:
                data = self._try_load_json(m.group(0))

        if isinstance(data, dict):
            normalized = self._normalize_dict(data)
            if normalized is not None:
                return normalized

        repaired = self._try_repair_code_artifact(text)
        if repaired is not None:
            normalized = self._normalize_dict(repaired)
            if normalized is not None:
                return normalized

        logger.warning("CoderAgent no pudo parsear JSON. Fallback texto libre.")
        path = (
            (fallback_paths[0] if fallback_paths else None)
            or fallback_path
            or "src/generated/output.txt"
        )
        content = text
        if text.lstrip().startswith("{") and "code_artifact" in text:
            again = self._try_repair_code_artifact(text)
            if again and again.get("files"):
                return again

        return {
            "type": "code_artifact",
            "files": [
                {
                    "path": path,
                    "content": content if isinstance(raw, str) else str(raw),
                }
            ],
        }

    def _try_load_json(self, text: str) -> Any | None:
        try:
            return json.loads(text)
        except Exception:
            return None

    def _try_repair_code_artifact(self, text: str) -> dict[str, Any] | None:
        """
        Repara JSON inválido cuando content trae saltos de línea literales.
        """
        if "code_artifact" not in text and '"files"' not in text:
            return None

        path_match = re.search(r'"path"\s*:\s*"([^"]+)"', text)
        if not path_match:
            return None
        path = path_match.group(1)

        content_match = re.search(
            r'"content"\s*:\s*"(.*)"\s*\}\s*\]\s*\}',
            text,
            re.DOTALL,
        )
        if not content_match:
            content_match = re.search(
                r'"content"\s*:\s*"(.*)"\s*\}',
                text,
                re.DOTALL,
            )
        if not content_match:
            # content como bloque tras "content": sin comillas bien cerradas
            marker = re.search(r'"content"\s*:\s*', text)
            if not marker:
                return None
            rest = text[marker.end() :]
            if rest.startswith('"'):
                rest = rest[1:]
            # cortar en la última comilla antes del cierre del objeto file
            end = rest.rfind('"')
            if end <= 0:
                return None
            raw_content = rest[:end]
        else:
            raw_content = content_match.group(1)

        content = (
            raw_content.replace("\\n", "\n")
            .replace("\\t", "\t")
            .replace('\\"', '"')
            .replace("\\\\", "\\")
        )

        return {
            "type": "code_artifact",
            "files": [{"path": path, "content": content}],
        }

    def _normalize_dict(self, data: dict[str, Any]) -> dict[str, Any] | None:
        if data.get("type") == "code_artifact" and isinstance(data.get("files"), list):
            files = []
            for item in data["files"]:
                if not isinstance(item, dict):
                    continue
                path = item.get("path")
                content = item.get("content")
                if path is None:
                    continue
                files.append(
                    {
                        "path": str(path),
                        "content": "" if content is None else str(content),
                    }
                )
            if files:
                return {"type": "code_artifact", "files": files}

        if isinstance(data.get("files"), list):
            data = dict(data)
            data["type"] = "code_artifact"
            return self._normalize_dict(data)

        if data.get("path") is not None and "content" in data:
            return {
                "type": "code_artifact",
                "files": [
                    {
                        "path": str(data["path"]),
                        "content": str(data.get("content") or ""),
                    }
                ],
            }

        return None
