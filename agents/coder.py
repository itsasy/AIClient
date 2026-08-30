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
    name = "coder"
    role = "Ingeniero de software"
    version = "2.6"
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
        task = str(params.get("task") or plan.objective or plan.original_task or "")

        requested_paths = self._collect_requested_paths(plan, step)
        if requested_paths:
            context["requested_paths"] = requested_paths

        path = str(params.get("path") or (requested_paths[0] if requested_paths else "") or "")
        landing = self._is_landing_request(task, path)

        context.setdefault("agent_role", self.role)
        context["coding_task"] = task
        context["lean_prompt"] = True
        plan.metadata["lean_prompt"] = True

        if landing:
            context["requested_output"] = self._landing_requested_output(path or "landing.html")
        else:
            context.setdefault(
                "requested_output",
                (
                    "Responde SOLO con JSON code_artifact válido.\n"
                    'Formato: {"type":"code_artifact","files":[{"path":"...","content":"..."}]}\n'
                    "content: string con el código completo (escapa \\n y comillas en JSON).\n"
                    "No envíes confirmaciones textuales ni markdown fuera del JSON."
                ),
            )

        raw = LLMRouter().generate(plan=plan, context=context)
        if not isinstance(raw, str):
            raw = str(raw)

        logger.info(
            "CoderAgent respuesta LLM (1er intento) | chars=%s | prefix=%r",
            len(raw),
            raw[:180].replace("\n", " "),
        )

        artifact = self._parse_llm_to_artifact(
            raw,
            fallback_paths=requested_paths,
            fallback_path=path or None,
        )

        if landing:
            artifact = self._finalize_landing_artifact(artifact, path or "landing.html")
            ok, reason = self._validate_landing_content(artifact)
            if not ok:
                logger.error("CoderAgent landing inválida: %s", reason)
                # 2º intento: pedir HTML crudo
                context["requested_output"] = (
                    self._landing_requested_output(path or "landing.html")
                    + "\nIMPORTANTE: responde SOLO con HTML completo empezando por <!DOCTYPE html>."
                    "\nNo uses JSON. No uses markdown fences."
                )
                context["retry_issues"] = [reason]
                context["retry_corrections"] = [
                    "Generar HTML completo con hero, ≥3 secciones, CTA y footer.",
                    "Incluir Tailwind CDN o CSS :root con tokens.",
                ]
                raw2 = LLMRouter().generate(plan=plan, context=context)
                if not isinstance(raw2, str):
                    raw2 = str(raw2)
                logger.info(
                    "CoderAgent respuesta LLM (2º intento HTML) | chars=%s | prefix=%r",
                    len(raw2),
                    raw2[:180].replace("\n", " "),
                )
                artifact = self._parse_llm_to_artifact(
                    raw2,
                    fallback_paths=requested_paths,
                    fallback_path=path or None,
                )
                artifact = self._finalize_landing_artifact(artifact, path or "landing.html")
                ok2, reason2 = self._validate_landing_content(artifact)
                if not ok2:
                    logger.error("CoderAgent landing inválida tras retry: %s", reason2)
                    return {
                        "type": "code_artifact",
                        "files": [],
                        "error": reason2,
                    }
                logger.info(
                    "CoderAgent landing válida | path=%s | chars=%s",
                    path,
                    len((artifact.get("files") or [{}])[0].get("content") or ""),
                )
            else:
                logger.info(
                    "CoderAgent landing válida | path=%s | chars=%s",
                    path,
                    len((artifact.get("files") or [{}])[0].get("content") or ""),
                )

        return artifact

    # =========================================================
    # Paths
    # =========================================================

    def _collect_requested_paths(
        self,
        plan: ExecutionPlan,
        step: ExecutionStep,
    ) -> list[str]:
        paths: list[str] = []
        for other in plan.steps or []:
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

    # =========================================================
    # Parse pipeline
    # =========================================================

    def _parse_llm_to_artifact(
        self,
        raw: str,
        fallback_paths: list[str] | str | None = None,
        fallback_path: str | None = None,
    ) -> dict[str, Any]:
        if isinstance(fallback_paths, str):
            fallback_path = fallback_path or fallback_paths
            fallback_paths = [fallback_paths]

        text = (raw or "").strip()
        if not text:
            return {
                "type": "code_artifact",
                "files": [],
                "error": "respuesta vacía",
            }

        if self._looks_like_confirmation(text):
            logger.warning("CoderAgent recibió confirmación textual, no código")
            return {"type": "code_artifact", "files": [], "error": "confirmación textual"}

        # HTML crudo
        html = self._extract_raw_html(text)
        if html:
            path = (fallback_paths[0] if fallback_paths else None) or fallback_path or "index.html"
            logger.info("CoderAgent recibió HTML crudo | path=%s | chars=%s", path, len(html))
            return {
                "type": "code_artifact",
                "files": [{"path": str(path), "content": html}],
            }

        # Fences
        fenced = re.search(r"```(?:json|html|htm)?\s*([\s\S]*?)```", text, re.I)
        candidate = fenced.group(1).strip() if fenced else text

        data = self._try_load_json(candidate)
        if data is None:
            m = re.search(r"\{[\s\S]*\}", candidate)
            if m:
                data = self._try_load_json(m.group(0))

        if isinstance(data, dict):
            normalized = self._normalize_dict(data)
            if normalized is not None:
                return normalized

        repaired = self._try_repair_code_artifact(candidate)
        if repaired is not None:
            normalized = self._normalize_dict(repaired)
            if normalized is not None:
                return normalized

        # HTML dentro de fence sin json
        html2 = self._extract_raw_html(candidate)
        if html2:
            path = (fallback_paths[0] if fallback_paths else None) or fallback_path or "index.html"
            return {
                "type": "code_artifact",
                "files": [{"path": str(path), "content": html2}],
            }

        logger.warning(
            "CoderAgent no pudo parsear JSON ni detectar HTML | chars=%s",
            len(text),
        )
        path = (
            (fallback_paths[0] if fallback_paths else None)
            or fallback_path
            or "src/generated/output.txt"
        )
        return {
            "type": "code_artifact",
            "files": [{"path": str(path), "content": text}],
        }

    def _try_load_json(self, text: str) -> Any | None:
        try:
            return json.loads(text)
        except Exception:
            return None

    def _try_repair_code_artifact(self, text: str) -> dict[str, Any] | None:
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
            content_match = re.search(r'"content"\s*:\s*"(.*)"\s*\}', text, re.DOTALL)
        if not content_match:
            marker = re.search(r'"content"\s*:\s*', text)
            if not marker:
                return None
            rest = text[marker.end() :]
            if rest.startswith('"'):
                rest = rest[1:]
            end = rest.rfind('"')
            if end <= 0:
                return None
            raw_content = rest[:end]
        else:
            raw_content = content_match.group(1)

        content = self._unescape_html_content(
            raw_content.replace("\\n", "\n")
            .replace("\\t", "\t")
            .replace('\\"', '"')
            .replace("\\\\", "\\")
        )
        return {"type": "code_artifact", "files": [{"path": path, "content": content}]}

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
                content_s = "" if content is None else str(content)
                if re.search(r"<html\b", content_s, re.I):
                    content_s = self._unescape_html_content(content_s)
                files.append({"path": str(path), "content": content_s})
            if files:
                return {"type": "code_artifact", "files": files}

        if data.get("path") is not None and "content" in data:
            content_s = str(data.get("content") or "")
            if re.search(r"<html\b", content_s, re.I):
                content_s = self._unescape_html_content(content_s)
            return {
                "type": "code_artifact",
                "files": [{"path": str(data["path"]), "content": content_s}],
            }
        return None

    # =========================================================
    # Landing helpers
    # =========================================================

    @staticmethod
    def _is_landing_request(task: str, path: str) -> bool:
        t = (task or "").lower()
        p = (path or "").lower()
        if p.endswith((".html", ".htm")):
            return True
        return bool(re.search(r"\b(landing|html\s+completo|página\s+web|pagina\s+web)\b", t))

    @staticmethod
    def _landing_requested_output(path: str) -> str:
        return f"""
    Generá una landing page HTML completa y profesional para el path: {path}

    Contrato mínimo:
    - <!DOCTYPE html> y <html lang="es">
    - <head> con charset, viewport, title, meta description
    - Tailwind CDN (https://cdn.tailwindcss.com) O CSS propio con :root tokens
    - Hero con título, subtítulo y CTA primario
    - Al menos 3 secciones de valor (beneficios, características, testimonios o similar)
    - Footer
    - Mínimo ~2500 caracteres de HTML útil
    - DEBE ser un documento HTML completo y válido.
    - DEBE terminar EXACTAMENTE con </body></html> (permitiendo únicamente whitespace después).
    - NO puede terminar dentro de un tag, atributo, string, script, comentario o bloque HTML incompleto.
    - NO cortes ni trunques la respuesta antes del cierre completo.
    - Priorizá siempre completar </body></html> aunque tengas que reducir contenido no esencial.
    - Antes de finalizar, verificá que existan </body> y </html> y que sean los últimos tags del documento.
    - Incluí footer con nombre del negocio
    - Mobile-first, limpia, un color primario + neutros

    Prohibido:
    - Confirmaciones ("archivo creado", "he ejecutado write_file")
    - Copiar marcas, logos o claims de sitios de referencia (Slack, etc.)
    - HTML de una sola línea vacía o placeholder de 2 frases

    Preferí JSON code_artifact:
    {{"type":"code_artifact","files":[{{"path":"{path}","content":"<!DOCTYPE html>..."}}]}}
    Alternativa aceptada: HTML crudo empezando por <!DOCTYPE html>.

    IMPORTANTE: La salida solo se considera válida si el HTML está completo y termina con </body></html>.
    """.strip()

    def _finalize_landing_artifact(
        self,
        artifact: dict[str, Any],
        path: str,
    ) -> dict[str, Any]:
        files = list(artifact.get("files") or [])
        if not files:
            return artifact
        first = dict(files[0])
        content = str(first.get("content") or "")
        content = self._unescape_html_content(content)
        if re.search(r"<html\b", content, re.I) and not re.search(
            r"<html\b[^>]*\blang\s*=", content, re.I
        ):
            content = re.sub(r"<html\b", '<html lang="es"', content, count=1, flags=re.I)
        first["path"] = str(first.get("path") or path)
        first["content"] = content
        files[0] = first
        return {"type": "code_artifact", "files": files}

    def _validate_landing_content(
        self,
        artifact: dict[str, Any],
    ) -> tuple[bool, str]:
        """
        Valida que el artefacto contenga HTML razonablemente completo.

        El objetivo es detectar:
        - archivo inexistente o vacío
        - contenido demasiado corto
        - contenido que no parece HTML
        - HTML de documento incompleto/truncado
        - falta de estructura mínima

        No exige una estructura concreta de landing (footer, número de
        sections, etc.) para evitar falsos negativos con templates válidos.
        """
        files = artifact.get("files") or []
        if not files:
            return False, "no existe ningún archivo."

        content = str(files[0].get("content") or "").strip()
        if not content:
            return False, "content vacío."

        if len(content) < 400:
            return False, f"HTML demasiado corto ({len(content)} chars)."

        lower = content.lower()

        if "<!doctype" not in lower and "<html" not in lower:
            return False, "no parece HTML (falta doctype/html)."

        if "<html" in lower and "</html>" not in lower:
            return False, "HTML incompleto: falta </html> (posible truncado)."

        stripped = content.rstrip()

        if stripped.endswith("\\") or stripped.endswith('="'):
            return False, "HTML truncado a mitad de atributo/escape."

        if re.search(
            r'<(?:p|div|span|a|h[1-6])\s+class\s*=\s*\\?\s*$',
            content,
            re.IGNORECASE | re.MULTILINE,
        ):
            return False, "HTML truncado en atributo class."

        structure = (
            len(re.findall(r"<section\b", lower))
            + len(re.findall(r"<h[1-3]\b", lower))
            + len(re.findall(r"<header\b", lower))
            + len(re.findall(r"<main\b", lower))
        )

        if structure < 1:
            return False, (
                "faltan secciones/estructura "
                "(section/header/main/h1-h3)."
            )

        return True, "ok"

    @staticmethod
    def _extract_raw_html(text: str) -> str | None:
        t = text.strip()
        if re.search(r"<!doctype\s+html", t, re.I) or re.search(r"<html\b", t, re.I):
            # quitar fences si envuelven
            m = re.search(
                r"(<!DOCTYPE\s+html[\s\S]*</html\s*>)",
                t,
                re.I,
            )
            if m:
                return m.group(1).strip()
            if t.lower().startswith("<!doctype") or t.lower().startswith("<html"):
                return t
        return None

    @staticmethod
    def _unescape_html_content(content: str) -> str:
        if not content:
            return content
        # Si viene con escapes literales de JSON mal reparado
        if "\\n" in content and content.count("\\n") > content.count("\n"):
            content = (
                content.replace("\\n", "\n")
                .replace("\\t", "\t")
                .replace('\\"', '"')
                .replace("\\/", "/")
            )
        return content

    def _looks_like_confirmation(self, text: str) -> bool:
        normalized = text.lower().strip()
        if not normalized or len(normalized) > 1000:
            return False
        patterns = (
            "archivo creado",
            "archivo generado",
            "archivo guardado",
            "guardado correctamente",
            "write_file",
            "he creado",
            "he generado",
            "he ejecutado",
            "ejecutado la skill",
            "ruta absoluta",
        )
        return (
            any(p in normalized for p in patterns)
            and "<html" not in normalized
            and "<!doctype" not in normalized
        )
