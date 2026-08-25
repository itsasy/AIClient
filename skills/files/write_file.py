from __future__ import annotations

from typing import Any

from core.execution_plan import ExecutionPlan
from core.execution_step import ExecutionStep
from core.tools.file import FileTool
from skills.base import Skill


class WriteFileSkill(Skill):
    name = "write_file"
    description = "Escribe archivo(s) dentro de TARGET_PROJECT_ROOT."
    version = "2.2"
    capabilities = ("file_write", "filesystem_operation")

    def __init__(self) -> None:
        self.tool = FileTool()

    def execute(
        self,
        plan: ExecutionPlan,
        step: ExecutionStep,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        params = dict(step.params or {})

        # Batch multi-file
        if params.get("write_all") and isinstance(params.get("files"), list):
            return self._write_all(params["files"])

        path = str(params.get("path") or "").strip()
        content = params.get("content")

        if not path:
            return {
                "ok": False,
                "result": None,
                "error": "write_file: falta path.",
            }

        if content is None or (isinstance(content, str) and content == ""):
            return {
                "ok": False,
                "result": None,
                "error": (
                    "write_file: content vacío "
                    "(coder no produjo artifact usable o el engine no materializó)."
                ),
            }

        if not isinstance(content, str):
            content = str(content)

        try:
            return self.tool.execute(
                operation="write",
                path=path,
                content=content,
            )
        except Exception as exc:
            return {
                "ok": False,
                "result": None,
                "error": str(exc),
            }

    def _write_all(self, files: list[Any]) -> dict[str, Any]:
        created: list[dict[str, Any]] = []
        errors: list[str] = []

        for item in files:
            if not isinstance(item, dict):
                continue
            path = str(item.get("path") or "").strip()
            content = item.get("content")
            if not path:
                errors.append("file sin path")
                continue
            if content is None or content == "":
                errors.append(f"{path}: content vacío")
                continue
            result = self.tool.execute(
                operation="write",
                path=path,
                content=str(content),
            )
            if result.get("ok"):
                created.append(result.get("result") or {"path": path})
            else:
                errors.append(f"{path}: {result.get('error')}")

        if not created:
            return {
                "ok": False,
                "result": None,
                "error": "; ".join(errors) or "write_all: ningún archivo escrito",
            }

        return {
            "ok": True,
            "result": {
                "type": "write_batch",
                "created": created,
                "errors": errors,
            },
            "error": None if not errors else "; ".join(errors),
        }
