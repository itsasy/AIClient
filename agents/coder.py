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
    version = "2.7"
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

        task = str(
            params.get("task")
            or plan.objective
            or plan.original_task
            or ""
        )

        requested_paths = self._collect_requested_paths(plan, step)

        if requested_paths:
            context["requested_paths"] = requested_paths

        path = str(
            params.get("path")
            or (requested_paths[0] if requested_paths else "")
            or ""
        )

        landing = self._is_landing_request(task, path)

        context.setdefault("agent_role", self.role)
        context["coding_task"] = task
        context["lean_prompt"] = True
        plan.metadata["lean_prompt"] = True

        if landing:
            context["requested_output"] = self._landing_requested_output(
                path or "landing.html"
            )
        else:
            context.setdefault(
                "requested_output",
                (
                    "Responde SOLO con JSON code_artifact válido.\n"
                    'Formato: {"type":"code_artifact",'
                    '"files":[{"path":"...","content":"..."}]}\n'
                    "content debe contener el código completo.\n"
                    "No envíes markdown ni explicaciones."
                ),
            )

        # -----------------------------------------------------
        # Primer intento
        # -----------------------------------------------------

        raw = self._generate(plan, context)

        logger.info(
            "CoderAgent respuesta LLM | intento=1 | chars=%s | suffix=%r",
            len(raw),
            raw[-300:].replace("\n", " "),
        )

        artifact = self._parse_llm_to_artifact(
            raw,
            fallback_paths=requested_paths,
            fallback_path=path or None,
        )

        if not landing:
            return artifact

        # -----------------------------------------------------
        # Validación de landing
        # -----------------------------------------------------

        artifact = self._finalize_landing_artifact(
            artifact,
            path or "landing.html",
        )

        ok, reason = self._validate_landing_content(artifact)

        if ok:
            self._log_valid_landing(artifact, path)
            return artifact

        logger.warning(
            "CoderAgent landing inválida | intento=1 | reason=%s",
            reason,
        )

        # -----------------------------------------------------
        # Segundo intento
        # -----------------------------------------------------

        context["requested_output"] = self._landing_retry_output(
            path or "landing.html",
            reason,
        )

        raw2 = self._generate(plan, context)

        logger.info(
            "CoderAgent respuesta LLM | intento=2 | chars=%s | suffix=%r",
            len(raw2),
            raw2[-300:].replace("\n", " "),
        )

        artifact = self._parse_llm_to_artifact(
            raw2,
            fallback_paths=requested_paths,
            fallback_path=path or None,
        )

        artifact = self._finalize_landing_artifact(
            artifact,
            path or "landing.html",
        )

        ok, reason = self._validate_landing_content(artifact)

        if not ok:
            logger.error(
                "CoderAgent landing inválida tras retry | reason=%s",
                reason,
            )

            return {
                "type": "code_artifact",
                "files": [],
                "error": reason,
            }

        self._log_valid_landing(artifact, path)

        return artifact

    # =========================================================
    # LLM
    # =========================================================

    @staticmethod
    def _generate(
        plan: ExecutionPlan,
        context: dict[str, Any],
    ) -> str:
        raw = LLMRouter().generate(
            plan=plan,
            context=context,
        )

        if not isinstance(raw, str):
            raw = str(raw)

        return raw.strip()

    # =========================================================
    # Paths
    # =========================================================

    @staticmethod
    def _collect_requested_paths(
        plan: ExecutionPlan,
        step: ExecutionStep,
    ) -> list[str]:
        paths: list[str] = []

        for other in plan.steps or []:
            if step.id in (other.depends_on or []):
                if other.unit_name == "write_file":
                    path = (other.params or {}).get("path")
                    if path:
                        paths.append(str(path))

        direct_path = (step.params or {}).get("path")

        if direct_path:
            paths.insert(0, str(direct_path))

        seen: set[str] = set()
        result: list[str] = []

        for path in paths:
            if path not in seen:
                seen.add(path)
                result.append(path)

        return result

    # =========================================================
    # Parsing
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
            return self._empty_artifact("respuesta vacía")

        if self._looks_like_confirmation(text):
            logger.warning(
                "CoderAgent recibió confirmación textual en lugar de código"
            )
            return self._empty_artifact("confirmación textual")

        # HTML crudo
        html = self._extract_raw_html(text)

        if html is not None:
            path = (
                (fallback_paths[0] if fallback_paths else None)
                or fallback_path
                or "index.html"
            )

            logger.info(
                "CoderAgent detectó HTML | path=%s | chars=%s",
                path,
                len(html),
            )

            return {
                "type": "code_artifact",
                "files": [
                    {
                        "path": str(path),
                        "content": html,
                    }
                ],
            }

        # Markdown fences
        fenced = re.search(
            r"```(?:json|html|htm)?\s*([\s\S]*?)```",
            text,
            re.IGNORECASE,
        )

        candidate = (
            fenced.group(1).strip()
            if fenced
            else text
        )

        # JSON directo
        data = self._try_load_json(candidate)

        # JSON envuelto en texto
        if data is None:
            match = re.search(
                r"\{[\s\S]*\}",
                candidate,
            )

            if match:
                data = self._try_load_json(match.group(0))

        if isinstance(data, dict):
            artifact = self._normalize_dict(data)

            if artifact is not None:
                return artifact

        # HTML dentro de fence
        html = self._extract_raw_html(candidate)

        if html is not None:
            path = (
                (fallback_paths[0] if fallback_paths else None)
                or fallback_path
                or "index.html"
            )

            return {
                "type": "code_artifact",
                "files": [
                    {
                        "path": str(path),
                        "content": html,
                    }
                ],
            }

        logger.warning(
            "CoderAgent no pudo interpretar la respuesta | chars=%s",
            len(text),
        )

        path = (
            (fallback_paths[0] if fallback_paths else None)
            or fallback_path
            or "src/generated/output.txt"
        )

        return {
            "type": "code_artifact",
            "files": [
                {
                    "path": str(path),
                    "content": text,
                }
            ],
        }

    @staticmethod
    def _try_load_json(text: str) -> Any | None:
        try:
            return json.loads(text)
        except (json.JSONDecodeError, TypeError, ValueError):
            return None

    @staticmethod
    def _normalize_dict(
        data: dict[str, Any],
    ) -> dict[str, Any] | None:
        if (
            data.get("type") == "code_artifact"
            and isinstance(data.get("files"), list)
        ):
            files: list[dict[str, str]] = []

            for item in data["files"]:
                if not isinstance(item, dict):
                    continue

                path = item.get("path")

                if path is None:
                    continue

                content = str(
                    item.get("content")
                    or ""
                )

                files.append(
                    {
                        "path": str(path),
                        "content": content,
                    }
                )

            if files:
                return {
                    "type": "code_artifact",
                    "files": files,
                }

        if data.get("path") is not None and "content" in data:
            return {
                "type": "code_artifact",
                "files": [
                    {
                        "path": str(data["path"]),
                        "content": str(
                            data.get("content")
                            or ""
                        ),
                    }
                ],
            }

        return None

    # =========================================================
    # Landing
    # =========================================================

    @staticmethod
    def _is_landing_request(
        task: str,
        path: str,
    ) -> bool:
        task_lower = (task or "").lower()
        path_lower = (path or "").lower()

        if path_lower.endswith((".html", ".htm")):
            return True

        return bool(
            re.search(
                r"\b("
                r"landing|"
                r"html\s+completo|"
                r"página\s+web|"
                r"pagina\s+web"
                r")\b",
                task_lower,
            )
        )

    @staticmethod
    def _landing_requested_output(path: str) -> str:
        return f"""
Generá una landing page HTML completa y profesional para:

{path}

FORMATO DE SALIDA:
- HTML crudo.
- NO JSON.
- NO markdown.
- NO ``` fences.
- NO explicaciones.
- La primera línea debe ser <!DOCTYPE html>.
- La última línea debe ser </html>.

REQUISITOS:
- <html lang="es">
- charset UTF-8
- viewport responsive
- title
- meta description
- Tailwind mediante CDN
- Hero principal
- Título, subtítulo y CTA
- Al menos 3 secciones de contenido
- Beneficios o características
- Testimonios o sección equivalente
- CTA final
- Footer
- Diseño mobile-first
- Un color primario y neutros
- HTML útil y profesional
- Mínimo aproximado de 2500 caracteres

IMPORTANTE:
- Priorizá terminar el documento antes que agregar contenido innecesario.
- No dejes tags abiertos.
- No termines dentro de un atributo.
- No termines dentro de un string.
- No termines dentro de un script.
- Antes de responder verificá que existan:
  </body>
  </html>

La respuesta debe ser exclusivamente el documento HTML completo.
""".strip()

    @staticmethod
    def _landing_retry_output(
        path: str,
        reason: str,
    ) -> str:
        return f"""
Generá nuevamente la landing HTML completa para:

{path}

El intento anterior fue rechazado por:

{reason}

FORMATO OBLIGATORIO:
- HTML crudo.
- NO JSON.
- NO markdown.
- NO ``` fences.
- NO explicaciones.
- Primera línea: <!DOCTYPE html>
- Última línea: </html>

REQUISITOS:
- <html lang="es">
- charset UTF-8
- viewport
- title
- meta description
- Tailwind CDN
- Hero con título, descripción y CTA
- Al menos 3 secciones
- Beneficios o características
- Testimonios o sección equivalente
- CTA final
- Footer
- Responsive/mobile-first
- Diseño profesional para una vinoteca/licorería

REGLA CRÍTICA:
Reducí contenido si es necesario para garantizar que la respuesta termine
completamente con:

</body>
</html>

No cortes la respuesta.
No dejes ningún tag abierto.
No termines a mitad de atributo, string, script o comentario.

Respondé solamente con HTML.
""".strip()

    @staticmethod
    def _finalize_landing_artifact(
        artifact: dict[str, Any],
        path: str,
    ) -> dict[str, Any]:
        files = list(artifact.get("files") or [])

        if not files:
            return artifact

        first = dict(files[0])

        content = str(
            first.get("content")
            or ""
        ).strip()

        # Elimina accidentalmente fences si el modelo los agregó.
        content = re.sub(
            r"^\s*```(?:html|htm)?\s*",
            "",
            content,
            flags=re.IGNORECASE,
        )

        content = re.sub(
            r"\s*```\s*$",
            "",
            content,
        ).strip()

        # Garantiza lang="es" si existe <html> pero no lang.
        if re.search(r"<html\b", content, re.IGNORECASE):
            if not re.search(
                r"<html\b[^>]*\blang\s*=",
                content,
                re.IGNORECASE,
            ):
                content = re.sub(
                    r"<html\b",
                    '<html lang="es"',
                    content,
                    count=1,
                    flags=re.IGNORECASE,
                )

        first["path"] = str(
            first.get("path")
            or path
        )

        first["content"] = content
        files[0] = first

        return {
            "type": "code_artifact",
            "files": files,
        }

    @staticmethod
    def _validate_landing_content(
        artifact: dict[str, Any],
    ) -> tuple[bool, str]:
        files = artifact.get("files") or []

        if not files:
            return False, "no existe ningún archivo."

        content = str(
            files[0].get("content")
            or ""
        ).strip()

        if not content:
            return False, "content vacío."

        if len(content) < 400:
            return False, (
                f"HTML demasiado corto ({len(content)} chars)."
            )

        lower = content.lower()

        # Documento HTML
        if (
            "<!doctype" not in lower
            and "<html" not in lower
        ):
            return False, (
                "no parece HTML "
                "(falta doctype/html)."
            )

        # Si empezó como documento HTML, exige cierre.
        if "<html" in lower:
            if "</body>" not in lower:
                return False, (
                    "HTML incompleto: falta </body>."
                )

            if "</html>" not in lower:
                return False, (
                    "HTML incompleto: falta </html> "
                    "(posible truncado)."
                )

        # El documento debe terminar correctamente.
        stripped = content.rstrip()

        if not re.search(
            r"</body>\s*</html>\s*$",
            stripped,
            re.IGNORECASE,
        ):
            return False, (
                "HTML incompleto: </body></html> "
                "no está al final del documento."
            )

        # Señales simples de truncamiento.
        if stripped.endswith("\\"):
            return False, (
                "HTML truncado a mitad de escape."
            )

        if stripped.endswith('="'):
            return False, (
                "HTML truncado a mitad de atributo."
            )

        # Estructura mínima.
        structure = (
            len(re.findall(
                r"<section\b",
                lower,
            ))
            + len(re.findall(
                r"<h[1-3]\b",
                lower,
            ))
            + len(re.findall(
                r"<header\b",
                lower,
            ))
            + len(re.findall(
                r"<main\b",
                lower,
            ))
        )

        if structure < 1:
            return False, (
                "faltan elementos de estructura "
                "(section/header/main/h1-h3)."
            )

        return True, "ok"

    @staticmethod
    def _extract_raw_html(
        text: str,
    ) -> str | None:
        text = (text or "").strip()

        if not text:
            return None

        # HTML completo.
        match = re.search(
            r"(<!DOCTYPE\s+html[\s\S]*?</html\s*>)",
            text,
            re.IGNORECASE,
        )

        if match:
            return match.group(1).strip()

        # HTML crudo aunque esté incompleto.
        # El validador será quien determine si está truncado.
        if re.match(
            r"^\s*(<!DOCTYPE\s+html\b|<html\b)",
            text,
            re.IGNORECASE,
        ):
            return text

        return None

    # =========================================================
    # Helpers
    # =========================================================

    @staticmethod
    def _empty_artifact(
        error: str,
    ) -> dict[str, Any]:
        return {
            "type": "code_artifact",
            "files": [],
            "error": error,
        }

    @staticmethod
    def _log_valid_landing(
        artifact: dict[str, Any],
        path: str,
    ) -> None:
        files = artifact.get("files") or []

        content = ""

        if files:
            content = str(
                files[0].get("content")
                or ""
            )

        logger.info(
            "CoderAgent landing válida | path=%s | chars=%s",
            path,
            len(content),
        )

    @staticmethod
    def _looks_like_confirmation(
        text: str,
    ) -> bool:
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
            any(
                pattern in normalized
                for pattern in patterns
            )
            and "<html" not in normalized
            and "<!doctype" not in normalized
        )
