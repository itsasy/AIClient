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
        razonamiento de código → code_artifact

    No escribe disco. La escritura corresponde a write_file.

    Contrato landing HTML:
        - path .html/.htm o señales de landing → resultado con HTML real
        - JSON code_artifact o HTML puro (con o sin fences)
        - path del plan se fuerza en el artifact
        - validación mínima verificable (no confirma solo texto)
    """

    name = "coder"
    role = "Ingeniero de software"
    version = "3.0"
    aliases = ("code", "developer")

    capabilities = (
        "code_generation",
        "code_artifact",
        "ui_generation",
    )

    LANDING_HINTS = (
        "landing",
        "html",
        "tailwind",
        "página",
        "pagina",
        "web page",
        "hero",
        "cta",
    )

    # =========================================================
    # PROCESS
    # =========================================================

    def process(
        self,
        plan: ExecutionPlan,
        step: ExecutionStep,
        context: dict[str, Any] | None = None,
    ) -> Any:
        context = dict(context or {})
        params = dict(step.params or {})
        original_task = str(
            params.get("task") or plan.original_task or plan.objective or ""
        ).strip()

        requested_paths = self._collect_requested_paths(plan, step, context)
        target_path = self._resolve_target_path(requested_paths, original_task, params)
        is_landing = self._is_landing_request(original_task, target_path, requested_paths)

        dependency_text = context.get("dependency_text") or ""
        if not dependency_text:
            # fallback desde execution.dependencies si el engine no materializó
            dependency_text = self._dependency_text_from_execution(context)
        has_analysis = bool(str(dependency_text).strip())

        logger.info(
            "CoderAgent contexto | plan=%s | landing=%s | requested_paths=%s | "
            "dependency_text=%s | dependency_chars=%s | target_path=%s",
            plan.id,
            is_landing,
            requested_paths,
            bool(has_analysis),
            len(str(dependency_text)),
            target_path,
        )

        context["agent_role"] = self.role
        context["requested_paths"] = requested_paths or ([target_path] if target_path else [])
        context["coding_task"] = original_task

        if is_landing:
            context["lean_prompt"] = True
            context["requested_output"] = self._landing_requested_output(
                target_path=target_path,
                task=original_task,
                has_analysis=has_analysis,
            )
            if has_analysis:
                context["dependency_text"] = str(dependency_text)[:6000]
            # Evitar ruido: el PromptBuilder en lean no debe volcar execution completo
            context.pop("execution", None)
        else:
            context.setdefault(
                "requested_output",
                (
                    "Devuelve un JSON code_artifact:\n"
                    '{"type":"code_artifact","files":[{"path":"...","content":"..."}]}\n'
                    "Sin markdown fuera del JSON. Sin explicaciones."
                ),
            )

        response = LLMRouter().generate(plan=plan, context=context)
        logger.info(
            "CoderAgent respuesta LLM (1er intento) | chars=%s | prefix=%r",
            len(response or ""),
            (response or "")[:180],
        )

        artifact = self._parse_llm_to_artifact(response or "", target_path or "output.txt")

        if is_landing:
            return self._handle_landing(
                plan=plan,
                original_task=original_task,
                target_path=target_path or "landing.html",
                artifact=artifact,
                response=response or "",
                dependency_text=str(dependency_text) if has_analysis else "",
            )

        if artifact:
            return artifact

        if self._looks_like_confirmation(response or ""):
            logger.warning("CoderAgent recibió confirmación textual; se descarta.")
            return {
                "type": "code_artifact",
                "files": [],
                "error": "Respuesta de confirmación sin código.",
            }

        return response

    def _handle_landing(
        self,
        plan: ExecutionPlan,
        original_task: str,
        target_path: str,
        artifact: dict[str, Any] | None,
        response: str,
        dependency_text: str,
    ) -> dict[str, Any]:
        if artifact:
            finalized = self._finalize_landing_artifact(artifact, target_path)
            if isinstance(finalized, dict):
                logger.info(
                    "CoderAgent landing válida | path=%s | chars=%s",
                    finalized["files"][0]["path"],
                    len(finalized["files"][0]["content"]),
                )
                return finalized
            logger.error("CoderAgent landing inválida: %s", finalized)
        else:
            logger.warning(
                "CoderAgent no pudo parsear JSON ni detectar HTML | chars=%s",
                len(response),
            )

        logger.warning(
            "CoderAgent landing inválida en 1er intento. "
            "Segundo intento HTML puro, manteniendo la tarea original."
        )

        context_retry: dict[str, Any] = {
            "agent_role": self.role,
            "lean_prompt": True,
            "requested_paths": [target_path],
            "coding_task": (
                f"{original_task}\n\n"
                f"Archivo objetivo: {target_path}\n"
                "Devuelve ÚNICAMENTE HTML5 completo.\n"
                "Debe empezar con <!DOCTYPE html> y terminar con </html>.\n"
                "Sin markdown, sin JSON, sin explicaciones.\n"
                "Si el usuario pidió Tailwind, incluye el script CDN de Tailwind.\n"
                "No copies marcas ni copy de sitios de referencia; producto original."
            ),
            "requested_output": (
                "Solo HTML5. Primera línea: <!DOCTYPE html>. " f"Path lógico: {target_path}."
            ),
        }
        if dependency_text:
            context_retry["dependency_text"] = dependency_text[:4000]

        response2 = LLMRouter().generate(plan=plan, context=context_retry)
        logger.info(
            "CoderAgent respuesta LLM (2º intento HTML) | chars=%s | prefix=%r",
            len(response2 or ""),
            (response2 or "")[:180],
        )

        artifact2 = self._parse_llm_to_artifact(response2 or "", target_path)
        if artifact2:
            finalized2 = self._finalize_landing_artifact(artifact2, target_path)
            if isinstance(finalized2, dict):
                logger.info(
                    "CoderAgent landing válida (2º) | path=%s | chars=%s",
                    finalized2["files"][0]["path"],
                    len(finalized2["files"][0]["content"]),
                )
                return finalized2
            logger.error("CoderAgent landing inválida (2º): %s", finalized2)

        logger.error("CoderAgent landing inválida: no existe ningún archivo.")
        return {
            "type": "code_artifact",
            "files": [],
            "error": "No se pudo obtener HTML válido para la landing.",
        }

    # =========================================================
    # Landing detection / paths
    # =========================================================

    def _collect_requested_paths(
        self,
        plan: ExecutionPlan,
        step: ExecutionStep,
        context: dict[str, Any],
    ) -> list[str]:
        paths: list[str] = []
        for source in (
            context.get("requested_paths"),
            (step.params or {}).get("requested_paths"),
            (plan.params or {}).get("requested_paths"),
            plan.metadata.get("requested_paths"),
        ):
            if isinstance(source, str) and source.strip():
                paths.append(source.strip())
            elif isinstance(source, (list, tuple)):
                for item in source:
                    if isinstance(item, str) and item.strip():
                        paths.append(item.strip())

        # path explícito en params del step/plan
        for key in ("path", "output_path", "file_path"):
            for bag in (step.params or {}, plan.params or {}):
                val = bag.get(key)
                if isinstance(val, str) and val.strip():
                    paths.append(val.strip())

        # regex en la tarea
        task = plan.original_task or ""
        for match in re.finditer(
            r"([A-Za-z0-9_.\-/]+\.(?:html?|css|js|tsx?|jsx|py|md))",
            task,
            re.I,
        ):
            paths.append(match.group(1))

        # únicos preservando orden
        seen: set[str] = set()
        ordered: list[str] = []
        for p in paths:
            if p not in seen:
                seen.add(p)
                ordered.append(p)
        return ordered

    def _resolve_target_path(
        self,
        requested_paths: list[str],
        task: str,
        params: dict[str, Any],
    ) -> str:
        for p in requested_paths:
            if re.search(r"\.html?$", p, re.I):
                return p
        if requested_paths:
            return requested_paths[0]
        for key in ("path", "output_path", "file_path"):
            val = params.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
        m = re.search(
            r"([A-Za-z0-9_.\-/]+\.html?)\b",
            task or "",
            re.I,
        )
        if m:
            return m.group(1)
        return "landing.html"

    def _is_landing_request(
        self,
        task: str,
        target_path: str,
        requested_paths: list[str],
    ) -> bool:
        if target_path and re.search(r"\.html?$", target_path, re.I):
            return True
        if any(re.search(r"\.html?$", p, re.I) for p in requested_paths):
            return True
        lower = (task or "").lower()
        return any(h in lower for h in self.LANDING_HINTS)

    def _landing_requested_output(
        self,
        target_path: str,
        task: str,
        has_analysis: bool,
    ) -> str:
        analysis_rule = ""
        if has_analysis:
            analysis_rule = (
                "- Si hay 'Análisis de referencia', úsalo solo como inspiración de "
                "estructura/conversión. NO copies marca, logos ni claims del sitio analizado.\n"
            )
        return (
            f"Objetivo de archivo: {target_path}\n"
            "Prioridad: el producto/tarea del usuario, no el sitio de referencia.\n"
            f"{analysis_rule}"
            "Formato preferido (JSON):\n"
            "{\n"
            '  "type": "code_artifact",\n'
            '  "files": [\n'
            f'    {{"path": "{target_path}", "content": "<!DOCTYPE html>...HTML completo..."}}\n'
            "  ]\n"
            "}\n\n"
            "Alternativa aceptada: HTML5 puro empezando por <!DOCTYPE html> "
            "sin markdown ni texto alrededor.\n\n"
            "Requisitos del HTML:\n"
            '- lang="es" en <html>\n'
            "- <head> con charset, viewport, title\n"
            "- <h1> visible\n"
            "- al menos hero + una sección de valor + CTA\n"
            "- CSS propio en <style> y/o Tailwind CDN si el usuario lo pidió\n"
            "- HTML legible (no minificar todo en una línea)\n"
            "- Sin explicaciones fuera del artifact/HTML\n"
        )

    @staticmethod
    def _dependency_text_from_execution(context: dict[str, Any]) -> str:
        execution = context.get("execution")
        if not isinstance(execution, dict):
            return ""
        deps = execution.get("dependencies")
        if not isinstance(deps, dict):
            return ""
        chunks: list[str] = []
        for dep in deps.values():
            raw = dep
            if isinstance(dep, dict):
                raw = dep.get("result", dep)
                if isinstance(raw, dict) and "ok" in raw and "result" in raw:
                    raw = raw.get("result")
            if isinstance(raw, str) and raw.strip():
                chunks.append(raw.strip())
                continue
            if isinstance(raw, dict):
                parts: list[str] = []
                for key in ("title", "url", "description", "text", "content", "summary"):
                    val = raw.get(key)
                    if val:
                        parts.append(f"{key}: {val}")
                if parts:
                    chunks.append("\n".join(parts))
        return "\n\n".join(chunks)[:6000]

    # =========================================================
    # PARSE / NORMALIZE
    # =========================================================

    @staticmethod
    def _strip_fences(text: str) -> str:
        t = (text or "").strip()
        if not t.startswith("```"):
            return t
        lines = t.split("\n")
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        return "\n".join(lines).strip()

    @staticmethod
    def _unescape_html_content(content: str) -> str:
        if not content:
            return content
        text = content
        if "\\n" in text or '\\"' in text or "\\/" in text:
            try:
                # intentar como string JSON
                text = json.loads(json.dumps(content))
            except Exception:
                text = (
                    content.replace("\\r\\n", "\n")
                    .replace("\\n", "\n")
                    .replace("\\r", "\r")
                    .replace("\\t", "\t")
                    .replace('\\"', '"')
                    .replace("\\/", "/")
                    .replace("\\\\", "\\")
                )
        return text

    def _extract_raw_html(self, text: str) -> str | None:
        stripped = (text or "").strip()
        if not stripped:
            return None

        if stripped.startswith("```"):
            stripped = self._strip_fences(stripped)

        lower = stripped.lower()
        if lower.startswith("<!doctype html") or lower.startswith("<html"):
            if re.search(r"</html\s*>", stripped, re.I):
                return stripped
            if len(stripped) > 400 and "<body" in lower:
                return stripped if stripped.rstrip().endswith(">") else stripped + "\n</html>"

        match = re.search(
            r"<!doctype\s+html[\s\S]*?</html\s*>",
            stripped,
            re.IGNORECASE,
        )
        if match:
            return match.group(0).strip()

        match = re.search(
            r"<html\b[\s\S]*?</html\s*>",
            stripped,
            re.IGNORECASE,
        )
        if match:
            return match.group(0).strip()

        return None

    def _try_load_json(self, text: str) -> Any | None:
        try:
            return json.loads(text)
        except (json.JSONDecodeError, TypeError, ValueError):
            return None

    def _extract_json_candidates(self, text: str) -> list[dict[str, Any]]:
        decoder = json.JSONDecoder()
        candidates: list[dict[str, Any]] = []
        body = self._strip_fences(text or "")
        for match in re.finditer(r"\{", body):
            start = match.start()
            try:
                data, _ = decoder.raw_decode(body[start:])
            except json.JSONDecodeError:
                continue
            if isinstance(data, dict) and data not in candidates:
                candidates.append(data)
        return candidates

    def _normalize_dict(self, data: dict[str, Any]) -> dict[str, Any] | None:
        if data.get("type") == "code_artifact" and isinstance(data.get("files"), list):
            files: list[dict[str, str]] = []
            for item in data["files"]:
                if not isinstance(item, dict):
                    continue
                path = item.get("path")
                if path is None:
                    continue
                content = item.get("content")
                if content is None:
                    content = ""
                if not isinstance(content, str):
                    content = str(content)
                content = self._unescape_html_content(content)
                files.append({"path": str(path), "content": content})
            if not files:
                return None
            return {"type": "code_artifact", "files": files}

        if isinstance(data.get("files"), list):
            normalized = dict(data)
            normalized["type"] = "code_artifact"
            return self._normalize_dict(normalized)

        if data.get("path") is not None and "content" in data:
            content = data.get("content")
            if content is None:
                content = ""
            if not isinstance(content, str):
                content = str(content)
            content = self._unescape_html_content(content)
            return {
                "type": "code_artifact",
                "files": [{"path": str(data["path"]), "content": content}],
            }
        return None

    def _parse_llm_to_artifact(
        self,
        response: str,
        default_path: str,
    ) -> dict[str, Any] | None:
        """Texto LLM → code_artifact o None."""
        text = (response or "").strip()
        if not text:
            return None

        for candidate in (text, self._strip_fences(text)):
            data = self._try_load_json(candidate)
            if isinstance(data, dict):
                art = self._normalize_dict(data)
                if art:
                    return art

        for data in self._extract_json_candidates(text):
            art = self._normalize_dict(data)
            if art:
                return art

        html = self._extract_raw_html(text)
        if html:
            html = self._unescape_html_content(html)
            if re.search(r"<html\b", html, re.I) and not re.search(
                r"<html\b[^>]*\blang\s*=",
                html,
                re.I,
            ):
                html = re.sub(
                    r"<html\b",
                    '<html lang="es"',
                    html,
                    count=1,
                    flags=re.I,
                )
            return {
                "type": "code_artifact",
                "files": [{"path": default_path, "content": html}],
            }

        return None

    def _validate_landing_content(self, content: str) -> str | None:
        html = (content or "").strip()
        if len(html) < 400:
            return "HTML demasiado corto."
        lower = html.lower()
        if "<!doctype" not in lower and "<html" not in lower:
            return "Falta DOCTYPE o <html>."
        if "<body" not in lower:
            return "Falta <body>."
        if not re.search(r"<h1\b", lower):
            return "Falta <h1>."
        has_style = bool(re.search(r"<style\b", lower))
        has_tw = "tailwindcss" in lower or "cdn.tailwindcss" in lower
        if not has_style and not has_tw:
            return "Falta <style> o Tailwind CDN."
        return None

    def _finalize_landing_artifact(
        self,
        artifact: dict[str, Any],
        target_path: str,
    ) -> dict[str, Any] | str:
        files = artifact.get("files") or []
        if not files:
            return "no existe ningún archivo"

        f0 = files[0]
        content = self._unescape_html_content(str(f0.get("content") or ""))
        path = (target_path or str(f0.get("path") or "")).strip() or "landing.html"

        if re.search(r"<html\b", content, re.I) and not re.search(
            r"<html\b[^>]*\blang\s*=",
            content,
            re.I,
        ):
            content = re.sub(
                r"<html\b",
                '<html lang="es"',
                content,
                count=1,
                flags=re.I,
            )

        err = self._validate_landing_content(content)
        if err:
            return err

        return {
            "type": "code_artifact",
            "files": [{"path": path, "content": content}],
        }

    # =========================================================
    # CONFIRMATION DETECTION
    # =========================================================

    def _looks_like_confirmation(self, text: str) -> bool:
        normalized = text.lower().strip()
        if not normalized:
            return False
        patterns = (
            "archivo creado",
            "archivo generado",
            "archivo guardado",
            "archivo escrito",
            "guardado correctamente",
            "generado correctamente",
            "escrito correctamente",
            "write_file",
            "he creado",
            "he generado",
            "he guardado",
            "se ha creado",
            "se ha generado",
            "se ha guardado",
            "ruta:",
            "path:",
            "he ejecutado",
            "ejecutado la skill",
        )
        return (
            len(normalized) < 1000
            and any(p in normalized for p in patterns)
            and "<html" not in normalized
            and "<!doctype" not in normalized
        )
