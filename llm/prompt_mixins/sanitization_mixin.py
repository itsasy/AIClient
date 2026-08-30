from __future__ import annotations

import json
import logging
from typing import Any

from core.execution_plan import ExecutionPlan
from llm.prompt_type import PromptType

logger = logging.getLogger(__name__)

class PromptSanitizationMixin:
    def _prepare_context(
        self,
        context: dict[str, Any],
        *,
        lean: bool,
    ) -> dict[str, Any]:
        prepared: dict[str, Any] = {}
        processed: set[str] = set()
        budgets = self.LEAN_KEY_BUDGETS if lean else self.KEY_BUDGETS

        # Normalizar aliases → claves canónicas
        context = self._normalize_aliases(dict(context))

        for key in self.CONTEXT_PRIORITY:
            if key not in context or key in self.DROP_KEYS:
                continue
            value = context[key]
            if value is None:
                continue
            value = self._sanitize_context_value(key, value, lean=lean)
            value = self._apply_budget(key, value, budgets)
            if value is None or value == "" or value == {} or value == []:
                continue
            prepared[key] = value
            processed.add(key)

        for key, value in context.items():
            if key in processed or key in self.DROP_KEYS:
                continue
            if value is None:
                continue
            value = self._sanitize_context_value(key, value, lean=lean)
            value = self._apply_budget(key, value, budgets)
            if value is None or value == "" or value == {} or value == []:
                continue
            prepared[key] = value

        return prepared

    def _normalize_aliases(self, context: dict[str, Any]) -> dict[str, Any]:
        # architecture_context → architecture (sin contents)
        if "architecture" not in context and "architecture_context" in context:
            context["architecture"] = context.get("architecture_context")

        # project_analysis dict → summary preferido
        pa = context.get("project_analysis")
        if isinstance(pa, dict):
            if not context.get("project_summary"):
                summary = pa.get("summary") or pa.get("project_summary")
                if summary:
                    context["project_summary"] = summary
            # No arrastrar snapshot embebido
            if "snapshot" in pa:
                pa = {k: v for k, v in pa.items() if k in {"summary", "project_summary", "type"}}
                context["project_analysis"] = pa

        # locale_summary desde dict locale_info
        if not context.get("locale_summary") and isinstance(context.get("locale"), dict):
            loc = context["locale"]
            context["locale_summary"] = loc.get("locale_summary") or loc.get("summary")
            if not context.get("locale") or isinstance(context.get("locale"), dict):
                code = loc.get("locale_code") or loc.get("code")
                if code:
                    context["locale"] = code

        return context

    def _sanitize_context_value(
        self,
        key: str,
        value: Any,
        *,
        lean: bool,
    ) -> Any:
        if key == "architecture":
            return self._sanitize_architecture(value, lean=lean)
        if key == "execution":
            return self._sanitize_execution(value, lean=lean)
        if key == "project_analysis":
            return self._sanitize_project_analysis(value)
        if key in {"retry_issues", "retry_corrections"}:
            return self._sanitize_list(value)
        if key == "standards" and isinstance(value, (dict, list)):
            return value
        if key == "lean_prompt":
            return bool(value)
        return value

    def _apply_budget(
        self,
        key: str,
        value: Any,
        budgets: dict[str, int],
    ) -> Any:
        budget = budgets.get(key)
        if budget is None:
            return value
        if isinstance(value, str):
            if len(value) <= budget:
                return value
            return value[: budget - 20] + "\n[...truncado]"
        serialized = self._serialize(value)
        if len(serialized) <= budget:
            return value
        # Truncar representación serializada y devolver string
        return serialized[: budget - 20] + "\n[...truncado]"

    def _sanitize_architecture(
        self,
        architecture: Any,
        *,
        lean: bool,
    ) -> Any:
        if not isinstance(architecture, dict):
            return architecture

        result: dict[str, Any] = {}

        for key in (
            "project_name",
            "root_path",
            "summary",
            "project_summary",
            "languages",
            "extensions",
            "directory_count",
            "file_count",
            "layers",
            "modules",
        ):
            if key in architecture and architecture[key] is not None:
                result[key] = architecture[key]

        files = architecture.get("files")
        if isinstance(files, list):
            clean_files = []
            limit = 40 if lean else 80
            for file_data in files[:limit]:
                if not isinstance(file_data, dict):
                    if isinstance(file_data, str):
                        clean_files.append({"path": file_data})
                    continue
                clean_file = {
                    k: file_data.get(k)
                    for k in (
                        "path",
                        "filename",
                        "extension",
                        "language",
                        "lines",
                        "size",
                    )
                    if k in file_data and file_data.get(k) is not None
                }
                # Nunca contents
                clean_files.append(clean_file)
            result["files"] = clean_files

        dirs = architecture.get("directories")
        if isinstance(dirs, list):
            clean_dirs = []
            for d in dirs[:40]:
                if isinstance(d, dict):
                    clean_dirs.append(
                        {
                            k: d.get(k)
                            for k in ("path", "name", "files_count", "directories_count")
                            if k in d
                        }
                    )
                elif isinstance(d, str):
                    clean_dirs.append({"path": d})
            result["directories"] = clean_dirs

        result.pop("content", None)
        result.pop("contents", None)
        result.pop("snapshot", None)
        return result

    @staticmethod
    def _sanitize_project_analysis(value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        return {
            k: value.get(k)
            for k in ("type", "summary", "project_summary")
            if value.get(k) is not None
        }

    @staticmethod
    def _sanitize_execution(execution: Any, *, lean: bool) -> Any:
        if not isinstance(execution, dict):
            return execution

        if lean:
            allowed = {
                "task",
                "current_step",
                "result",
            }
        else:
            allowed = {
                "plan_id",
                "task",
                "current_step",
                "dependencies",
                "steps",
                "result",
            }

        out = {key: execution.get(key) for key in allowed if key in execution}

        # Evitar volcar dependencias enormes en lean
        if lean and "result" in out and isinstance(out["result"], (dict, list, str)):
            blob = (
                out["result"]
                if isinstance(out["result"], str)
                else json.dumps(out["result"], ensure_ascii=False, default=str)
            )
            if len(blob) > 1200:
                out["result"] = blob[:1180] + "...[truncado]"
        return out

    @staticmethod
    def _sanitize_list(value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [value]
        if not isinstance(value, (list, tuple, set)):
            return [str(value)]
        return [str(item) for item in value if item is not None]

