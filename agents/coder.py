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
        razonamiento de código -> code_artifact

    No escribe disco.
    La escritura corresponde a write_file.

    Contrato especial para landing HTML:
        - Si existe un path .html/.htm o se detecta una landing,
          el resultado DEBE contener HTML real.
        - Nunca se considera válida una confirmación textual.
        - El path esperado se conserva y se fuerza en el artifact.
        - El HTML debe cumplir un contrato mínimo verificable.
    """

    name = "coder"
    role = "Ingeniero de software"
    version = "2.7"
    aliases = ("code", "developer")
    capabilities = (
        "code_generation",
        "code_artifact",
        "ui_generation",
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

        # -----------------------------------------------------
        # Tarea original
        # -----------------------------------------------------

        original_task = str(
            params.get("task") or plan.original_task or plan.objective or ""
        ).strip()

        requested_paths = self._collect_requested_paths(
            plan,
            step,
        )

        if requested_paths:
            context["requested_paths"] = requested_paths

        # -----------------------------------------------------
        # Detectar landing
        # -----------------------------------------------------

        task_lower = original_task.lower()

        is_landing = any(
            path.lower().endswith((".html", ".htm")) for path in requested_paths
        ) or any(
            token in task_lower
            for token in (
                "landing",
                ".html",
                ".htm",
                "landing page",
                "página web",
                "pagina web",
                "sitio web",
                "website",
                "página html",
                "pagina html",
                "web html",
            )
        )

        context.setdefault(
            "agent_role",
            self.role,
        )

        dependency_text = context.get("dependency_text")

        has_analysis = isinstance(dependency_text, str) and bool(dependency_text.strip())

        # -----------------------------------------------------
        # Determinar path objetivo
        # -----------------------------------------------------

        if requested_paths:
            target_path = requested_paths[0]
        elif params.get("path"):
            target_path = str(params["path"])
        elif is_landing:
            target_path = "output.html"
        else:
            target_path = "output.txt"

        logger.info(
            "CoderAgent contexto | plan=%s | landing=%s | "
            "requested_paths=%s | dependency_text=%s | "
            "dependency_chars=%s | target_path=%s",
            plan.id,
            is_landing,
            requested_paths,
            has_analysis,
            len(dependency_text.strip()) if has_analysis else 0,
            target_path,
        )

        # =====================================================
        # ENRIQUECER TAREA
        # =====================================================

        enrichment_lines = [
            f"Archivo objetivo (path exacto): {target_path}",
            "Si generas archivos, usa exactamente ese path.",
            "No escribas en disco; solo produce el artefacto de código.",
        ]

        if is_landing:
            enrichment_lines.extend(
                [
                    "La tarea requiere una landing HTML real.",
                    "La salida preferida es un code_artifact JSON válido.",
                    "También se acepta HTML5 puro como fallback.",
                    "No respondas solo con confirmaciones.",
                    "No respondas solo con análisis.",
                ]
            )

        coding_task = original_task

        if enrichment_lines:
            coding_task = (
                original_task
                + "\n\n---\n"
                + "Restricciones de ejecución:\n- "
                + "\n- ".join(enrichment_lines)
            )

        context["coding_task"] = coding_task

        # =====================================================
        # CONTRATO LANDING
        # =====================================================

        if is_landing:
            context["lean_prompt"] = True

            analysis_block = ""

            if has_analysis:
                analysis_block = f"""
ANÁLISIS DE REFERENCIA

======================

Usa este análisis únicamente como inspiración de estructura,
copy y patrones de conversión.

NO copies marcas, nombres, claims ni contenido propietario
de terceros.

---

{dependency_text[:4500]}

---

Adapta completamente el resultado a la TAREA DEL USUARIO.
"""

            context["requested_output"] = f"""
CONTRATO OBLIGATORIO

====================

FORMATO PREFERIDO:

Devuelve ÚNICAMENTE un JSON válido de tipo code_artifact.

{{
  "type": "code_artifact",
  "files": [
    {{
      "path": "{target_path}",
      "content": "<!DOCTYPE html>...HTML completo...</html>"
    }}
  ]
}}

Si no puedes producir correctamente el JSON anterior,
devuelve ÚNICAMENTE HTML5 puro.

El HTML puro debe comenzar con:

<!DOCTYPE html>

Y terminar con:

</html>

REGLAS OBLIGATORIAS:

- "path" debe ser exactamente "{target_path}" cuando uses JSON.
- HTML5 completo.
- <html lang="es">.
- <head>.
- <meta charset="UTF-8">.
- meta viewport.
- <title> atractivo y orientado a SEO.
- meta description de máximo 155 caracteres.
- og:title.
- og:description.
- og:type="website".
- <style> con CSS autocontenido.
- <header>.
- <main>.
- al menos 4 <section>.
- <footer>.
- exactamente un <h1>.
- al menos un CTA mediante <a> o <button>.
- diseño mobile-first.
- página autocontenida.
- HTML bien formateado.
- No minifiques el HTML.
- El producto, marca y copy deben salir de la TAREA DEL USUARIO.
- No inventes otro producto.
- No sustituyas la tarea original por un ejemplo.
- No escribas análisis.
- No escribas explicaciones.
- No escribas confirmaciones.
- No uses markdown.
- No uses bloques ```html.
- No devuelvas solamente "archivo creado", "listo", "generado", etc.
- El resultado debe contener HTML REAL.

{analysis_block}

""".strip()

        # =====================================================
        # CONTRATO CÓDIGO GENERAL
        # =====================================================

        else:
            context.setdefault(
                "requested_output",
                (
                    "Responde ÚNICAMENTE con JSON válido de tipo "
                    "code_artifact: "
                    '{"type":"code_artifact","files":['
                    '{"path":"...","content":"..."}'
                    "]}. "
                    "No uses markdown ni texto adicional."
                ),
            )

        # =====================================================
        # PRIMER INTENTO
        # =====================================================

        raw = LLMRouter().generate(
            plan=plan,
            context=context,
        )

        logger.info(
            "CoderAgent respuesta LLM (1er intento) | chars=%s | prefix=%r",
            len(raw) if isinstance(raw, str) else -1,
            raw[:250] if isinstance(raw, str) else raw,
        )

        artifact = self._parse_llm_to_artifact(
            response=raw,
            default_path=target_path,
        )

        # -----------------------------------------------------
        # Código general
        # -----------------------------------------------------

        if not is_landing:
            if artifact:
                return artifact
            return raw

        # -----------------------------------------------------
        # Landing:
        # NORMALIZAR HTML ANTES DE VALIDAR / ENFORCE
        # -----------------------------------------------------

        if artifact:
            finalized = self._finalize_landing_artifact(
                artifact=artifact,
                target_path=target_path,
            )

            if isinstance(finalized, dict):
                logger.info(
                    "CoderAgent landing válida | path=%s | chars=%s",
                    finalized["files"][0]["path"],
                    len(finalized["files"][0]["content"]),
                )
                return finalized

            logger.error(
                "CoderAgent landing inválida: %s",
                finalized,
            )
        else:
            logger.warning(
                "CoderAgent no pudo parsear JSON ni detectar HTML | chars=%s",
                len(raw or "") if isinstance(raw, str) else 0,
            )

        # =====================================================
        # SEGUNDO INTENTO: HTML PURO
        # =====================================================

        logger.warning(
            "CoderAgent landing inválida en 1er intento. "
            "Segundo intento HTML puro, manteniendo la tarea "
            "original y sin producto hardcodeado."
        )

        context_retry: dict[str, Any] = {
            "agent_role": self.role,
            "lean_prompt": True,
            "requested_paths": [target_path],
            "coding_task": (
                f"{original_task}\n\n"
                f"Archivo objetivo: {target_path}\n"
                "SEGUNDO INTENTO:\n"
                "Devuelve ÚNICAMENTE HTML5 completo.\n"
                "Debe empezar con <!DOCTYPE html> y terminar con </html>.\n"
                "Sin markdown, sin JSON, sin explicaciones.\n"
                "No escribas análisis.\n"
                "No escribas confirmaciones.\n"
                "El contenido debe corresponder exactamente a la tarea original.\n"
                "No inventes otro producto, marca o caso de uso.\n"
                "Si pediste Tailwind, incluye el script CDN de Tailwind."
            ),
            "requested_output": (
                "Solo HTML5. Primera línea: <!DOCTYPE html>. " f"Path lógico: {target_path}."
            ),
        }

        if has_analysis:
            context_retry["dependency_text"] = str(dependency_text)[:4000]

        response2 = LLMRouter().generate(
            plan=plan,
            context=context_retry,
        )

        logger.info(
            "CoderAgent respuesta LLM (2º intento HTML) | chars=%s | prefix=%r",
            len(response2) if isinstance(response2, str) else -1,
            response2[:250] if isinstance(response2, str) else response2,
        )

        artifact2 = self._parse_llm_to_artifact(
            response=response2,
            default_path=target_path,
        )

        if artifact2:
            finalized2 = self._finalize_landing_artifact(
                artifact=artifact2,
                target_path=target_path,
            )

            if isinstance(finalized2, dict):
                logger.info(
                    "CoderAgent landing válida en 2º intento | path=%s | chars=%s",
                    finalized2["files"][0]["path"],
                    len(finalized2["files"][0]["content"]),
                )
                return finalized2

            logger.error(
                "CoderAgent landing inválida (2º): %s",
                finalized2,
            )
        else:
            logger.error(
                "CoderAgent landing inválida: " "no se pudo parsear HTML del segundo intento."
            )

        # -----------------------------------------------------
        # Fallback mínimo para no tumbar el engine
        # -----------------------------------------------------

        return {
            "type": "code_artifact",
            "files": [],
            "error": "No se pudo obtener HTML válido para la landing.",
        }

    # =========================================================
    # PARSE / NORMALIZE
    # =========================================================

    @staticmethod
    def _strip_fences(text: str) -> str:
        """
        Elimina fences markdown del tipo:

            ```json
            {...}
            ```

        o:

            ```html
            <!DOCTYPE html>
            ...
            ```

        También tolera BOM y espacios alrededor.
        """

        t = (text or "").strip().lstrip("\ufeff")

        if not t.startswith("```"):
            return t

        lines = t.splitlines()

        if lines and lines[0].lstrip().startswith("```"):
            lines = lines[1:]

        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]

        return "\n".join(lines).strip()

    @staticmethod
    def _unescape_html_content(content: str) -> str:
        """
        Desescapa HTML que haya quedado serializado dentro de
        un JSON/string.

        Ejemplos:

            <html>\\n -> <html>\n
            \\" -> "
            \\/ -> /
            \\\\ -> \\

        """

        if not content:
            return content

        text = content

        # JSON escaped HTML.
        if "\\n" in text or '\\"' in text or "\\/" in text:
            try:
                text = json.loads('"' + text.replace('"', '\\"') + '"')
            except Exception:
                try:
                    text = json.loads(f'"{text}"')
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

    @staticmethod
    def _ensure_html_lang_es(content: str) -> str:
        """
        Garantiza lang="es" en <html> cuando no existe.
        """

        if not content:
            return content

        if not re.search(
            r"<html\b",
            content,
            re.IGNORECASE,
        ):
            return content

        if re.search(
            r"<html\b[^>]*\blang\s*=",
            content,
            re.IGNORECASE,
        ):
            return content

        return re.sub(
            r"<html\b",
            '<html lang="es"',
            content,
            count=1,
            flags=re.IGNORECASE,
        )

    def _extract_raw_html(
        self,
        text: str,
    ) -> str | None:
        """
        Detecta HTML completo aunque exista:

        - BOM
        - fence markdown
        - texto residual alrededor
        - ausencia de cierre </html> en respuestas suficientemente largas
        """

        stripped = (text or "").strip().lstrip("\ufeff")

        if not stripped:
            return None

        # Quitar fence ```html ... ```
        if stripped.startswith("```"):
            stripped = self._strip_fences(stripped)

        # Volver a quitar BOM después del fence.
        stripped = stripped.lstrip("\ufeff").strip()

        lower = stripped.lower()

        # -----------------------------------------------------
        # Documento completo empezando directamente por DOCTYPE
        # -----------------------------------------------------

        if lower.startswith("<!doctype html"):
            if re.search(
                r"</html\s*>",
                stripped,
                re.IGNORECASE,
            ):
                return stripped

            # El modelo puede haber cortado el cierre.
            if len(stripped) > 400 and "<body" in lower:
                return (stripped if stripped.rstrip().endswith(">") else stripped + "\n") + (
                    "" if re.search(r"</html\s*>$", stripped, re.I) else "\n</html>"
                )

        # -----------------------------------------------------
        # Documento completo empezando por <html>
        # -----------------------------------------------------

        if lower.startswith("<html"):
            if re.search(
                r"</html\s*>",
                stripped,
                re.IGNORECASE,
            ):
                return stripped

            if len(stripped) > 400 and "<body" in lower:
                return (
                    stripped if stripped.rstrip().endswith(">") else stripped + "\n"
                ) + "\n</html>"

        # -----------------------------------------------------
        # HTML completo rodeado de texto
        # -----------------------------------------------------

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

    def _try_load_json(
        self,
        text: str,
    ) -> Any | None:
        try:
            return json.loads(text)
        except (
            json.JSONDecodeError,
            TypeError,
            ValueError,
        ):
            return None

    def _extract_json_candidates(
        self,
        text: str,
    ) -> list[dict[str, Any]]:
        """
        Busca objetos JSON válidos dentro de una respuesta
        que puede contener texto adicional o fences.
        """

        decoder = json.JSONDecoder()
        candidates: list[dict[str, Any]] = []

        body = self._strip_fences(text or "")

        for match in re.finditer(
            r"\{",
            body,
        ):
            start = match.start()

            try:
                data, _ = decoder.raw_decode(body[start:])
            except json.JSONDecodeError:
                continue

            if isinstance(data, dict) and data not in candidates:
                candidates.append(data)

        return candidates

    def _normalize_dict(
        self,
        data: dict[str, Any],
    ) -> dict[str, Any] | None:

        # -----------------------------------------------------
        # code_artifact explícito
        # -----------------------------------------------------

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

                files.append(
                    {
                        "path": str(path),
                        "content": content,
                    }
                )

            if not files:
                return None

            result: dict[str, Any] = {
                "type": "code_artifact",
                "files": files,
            }

            if data.get("error"):
                result["error"] = str(data["error"])

            return result

        # -----------------------------------------------------
        # files sin type
        # -----------------------------------------------------

        if isinstance(
            data.get("files"),
            list,
        ):
            normalized = dict(data)
            normalized["type"] = "code_artifact"

            return self._normalize_dict(normalized)

        # -----------------------------------------------------
        # path + content
        # -----------------------------------------------------

        if data.get("path") is not None and "content" in data:
            content = data.get("content")

            if content is None:
                content = ""

            if not isinstance(content, str):
                content = str(content)

            content = self._unescape_html_content(content)

            return {
                "type": "code_artifact",
                "files": [
                    {
                        "path": str(data["path"]),
                        "content": content,
                    }
                ],
            }

        return None

    def _parse_llm_to_artifact(
        self,
        response: str,
        default_path: str,
    ) -> dict[str, Any] | None:
        """
        Única puerta de entrada:

            texto LLM -> code_artifact | None

        Acepta:

        - JSON puro
        - JSON con ```json
        - JSON embebido
        - HTML puro
        - HTML con ```html
        - HTML rodeado de texto
        - HTML con BOM
        - HTML sin </html> cuando la respuesta parece truncada
        """

        text = (response or "").strip()

        if not text:
            return None

        # =====================================================
        # 1) JSON DIRECTO / FENCES
        # =====================================================

        for candidate in (
            text,
            self._strip_fences(text),
        ):
            data = self._try_load_json(candidate)

            if isinstance(data, dict):
                artifact = self._normalize_dict(data)

                if artifact:
                    return artifact

        # =====================================================
        # 2) JSON EMBEBIDO
        # =====================================================

        for data in self._extract_json_candidates(text):
            artifact = self._normalize_dict(data)

            if artifact:
                return artifact

        # =====================================================
        # 3) HTML CRUDO
        # =====================================================

        html = self._extract_raw_html(text)

        if html:
            html = self._unescape_html_content(html)
            html = self._ensure_html_lang_es(html)

            return {
                "type": "code_artifact",
                "files": [
                    {
                        "path": default_path,
                        "content": html,
                    }
                ],
            }

        return None

    # =========================================================
    # COMPATIBILITY PARSER
    # =========================================================

    def _parse_artifact(
        self,
        raw: Any,
        fallback_paths: list[str] | None = None,
        fallback_path: str | None = None,
    ) -> dict[str, Any]:
        """
        Compatibilidad con versiones anteriores del CoderAgent.

        El parser definitivo es _parse_llm_to_artifact().
        """

        if isinstance(raw, str):
            text = raw.strip()
        else:
            try:
                text = json.dumps(
                    raw,
                    ensure_ascii=False,
                ).strip()
            except (TypeError, ValueError):
                text = str(raw).strip()

        default_path = (
            (fallback_paths[0] if fallback_paths else None) or fallback_path or "output.txt"
        )

        artifact = self._parse_llm_to_artifact(
            response=text,
            default_path=default_path,
        )

        if artifact:
            return artifact

        if self._looks_like_confirmation(text):
            logger.error(
                "CoderAgent recibió confirmación en lugar de código | " "chars=%s | response=%r",
                len(text),
                text[:500],
            )

            return {
                "type": "code_artifact",
                "files": [],
                "error": (
                    "CoderAgent recibió una confirmación " "o texto en lugar de un code_artifact."
                ),
            }

        logger.warning(
            "CoderAgent no pudo parsear JSON ni detectar HTML | chars=%s",
            len(text),
        )

        return {
            "type": "code_artifact",
            "files": [],
            "error": (
                "La respuesta del LLM no pudo normalizarse " "correctamente como code_artifact."
            ),
        }

    # =========================================================
    # HTML NORMALIZATION
    # =========================================================

    def _normalize_landing_artifact(
        self,
        artifact: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Normaliza el contenido HTML del artifact.

        Flujo:

            content
                -> unescape
                -> lang="es"
                -> artifact normalizado
        """

        files = artifact.get("files")

        if not isinstance(files, list):
            return artifact

        normalized_files: list[dict[str, Any]] = []

        for file in files:
            if not isinstance(file, dict):
                continue

            normalized_file = dict(file)

            content = normalized_file.get("content")

            if content is None:
                content = ""

            if not isinstance(content, str):
                content = str(content)

            content = self._unescape_html_content(content)
            content = self._ensure_html_lang_es(content)

            normalized_file["content"] = content

            normalized_files.append(normalized_file)

        normalized_artifact = dict(artifact)
        normalized_artifact["files"] = normalized_files

        return normalized_artifact

    # =========================================================
    # LANDING FINALIZATION
    # =========================================================

    def _finalize_landing_artifact(
        self,
        artifact: dict[str, Any],
        target_path: str,
    ) -> dict[str, Any] | str:
        """
        Fuerza path, unescape, lang y validación mínima.

        Returns:
            artifact válido
            o mensaje de error
        """

        files = artifact.get("files") or []

        if not files:
            return "no existe ningún archivo"

        f0 = files[0]

        if not isinstance(f0, dict):
            return "el primer archivo no es válido"

        content = self._unescape_html_content(str(f0.get("content") or ""))

        # Si el parser obtuvo un HTML pero quedó rodeado de
        # fences/texto residual, volver a extraerlo.
        extracted_html = self._extract_raw_html(content)

        if extracted_html:
            content = extracted_html

        content = self._ensure_html_lang_es(content)

        path = str(f0.get("path") or target_path).strip() or target_path

        # Preferir path planificado.
        path = target_path or path

        err = self._validate_landing_content(content)

        if err:
            return err

        return {
            "type": "code_artifact",
            "files": [
                {
                    "path": path,
                    "content": content,
                }
            ],
        }

    # =========================================================
    # LANDING CONTRACT
    # =========================================================

    def _enforce_landing_contract(
        self,
        artifact: dict[str, Any],
        expected_path: str | None,
        raw: Any,
    ) -> dict[str, Any]:
        """
        Compatibilidad con la implementación anterior.

        Mantiene el mismo contrato externo pero delega la
        normalización/finalización en la nueva lógica.
        """

        artifact = self._normalize_landing_artifact(artifact)

        result = self._finalize_landing_artifact(
            artifact=artifact,
            target_path=expected_path or "output.html",
        )

        if isinstance(result, dict):
            return result

        logger.error(
            "CoderAgent landing inválida | error=%s",
            result,
        )

        error_result: dict[str, Any] = {
            "type": "code_artifact",
            "files": [],
            "error": result,
        }

        if raw is not None:
            raw_text = raw if isinstance(raw, str) else str(raw)
            error_result["raw_response"] = raw_text[:2000]

        return error_result

    # =========================================================
    # LANDING VALIDATION
    # =========================================================

    def _validate_landing_content(
        self,
        content: str,
    ) -> str | None:

        html = (content or "").strip()

        if len(html) < 400:
            return "HTML demasiado corto."

        lower = html.lower()

        if "<!doctype" not in lower and "<html" not in lower:
            return "Falta DOCTYPE o <html>."

        if not re.search(
            r"<body\b",
            lower,
        ):
            return "Falta <body>."

        if not re.search(
            r"<h1\b",
            lower,
        ):
            return "Falta <h1>."

        # Tailwind o style.
        has_style = bool(
            re.search(
                r"<style\b",
                lower,
            )
        )

        has_tw = "tailwindcss" in lower or "cdn.tailwindcss" in lower

        if not has_style and not has_tw:
            return "Falta <style> o Tailwind."

        return None

    # =========================================================
    # META HELPERS
    # =========================================================

    def _get_meta_name_content(
        self,
        html: str,
        name: str,
    ) -> str | None:

        escaped = re.escape(name)

        patterns = (
            rf'<meta\b[^>]*\bname\s*=\s*["\']{escaped}["\']'
            rf'[^>]*\bcontent\s*=\s*["\']([^"\']*)["\']',
            rf'<meta\b[^>]*\bcontent\s*=\s*["\']([^"\']*)["\']'
            rf'[^>]*\bname\s*=\s*["\']{escaped}["\']',
        )

        for pattern in patterns:
            match = re.search(
                pattern,
                html,
                re.IGNORECASE,
            )

            if match:
                return match.group(1)

        return None

    def _has_meta_property(
        self,
        html: str,
        property_name: str,
    ) -> bool:

        return (
            self._get_meta_property_content(
                html,
                property_name,
            )
            is not None
        )

    def _get_meta_property_content(
        self,
        html: str,
        property_name: str,
    ) -> str | None:

        escaped = re.escape(property_name)

        patterns = (
            rf'<meta\b[^>]*\bproperty\s*=\s*["\']'
            rf'{escaped}["\']'
            rf'[^>]*\bcontent\s*=\s*["\']([^"\']*)["\']',
            rf'<meta\b[^>]*\bcontent\s*=\s*["\']'
            rf'([^"\']*)["\']'
            rf'[^>]*\bproperty\s*=\s*["\']'
            rf'{escaped}["\']',
        )

        for pattern in patterns:
            match = re.search(
                pattern,
                html,
                re.IGNORECASE,
            )

            if match:
                return match.group(1).strip()

        return None

    # =========================================================
    # CTA
    # =========================================================

    def _has_conversion_cta(
        self,
        html: str,
    ) -> bool:

        conversion_words = (
            "comprar",
            "compra",
            "pedir",
            "pedido",
            "reservar",
            "reserva",
            "descubrir",
            "probar",
            "quiero",
            "conseguir",
            "contactar",
            "empezar",
            "comenzar",
            "solicitar",
            "cotizar",
            "suscribirme",
            "suscribirse",
            "shop",
            "buy",
            "order",
            "start",
            "discover",
        )

        patterns = (
            r"<a\b[^>]*>([\s\S]*?)</a\s*>",
            r"<button\b[^>]*>([\s\S]*?)</button\s*>",
        )

        for pattern in patterns:
            for match in re.finditer(
                pattern,
                html,
                re.IGNORECASE,
            ):
                text = re.sub(
                    r"<[^>]+>",
                    " ",
                    match.group(1),
                )

                text = (
                    re.sub(
                        r"\s+",
                        " ",
                        text,
                    )
                    .strip()
                    .lower()
                )

                if any(word in text for word in conversion_words):
                    return True

        return False

    # =========================================================
    # PATHS
    # =========================================================

    def _collect_requested_paths(
        self,
        plan: ExecutionPlan,
        step: ExecutionStep,
    ) -> list[str]:

        paths: list[str] = []

        # -----------------------------------------------------
        # Path explícito del coder
        # -----------------------------------------------------

        step_path = (step.params or {}).get("path")

        if step_path:
            paths.append(str(step_path))

        # -----------------------------------------------------
        # write_file dependiente del coder
        # -----------------------------------------------------

        for other in plan.steps:
            if step.id not in (other.depends_on or []):
                continue

            if other.unit_name != "write_file":
                continue

            path = (other.params or {}).get("path")

            if path:
                paths.append(str(path))

        # -----------------------------------------------------
        # Deduplicar conservando orden
        # -----------------------------------------------------

        seen: set[str] = set()
        ordered: list[str] = []

        for path in paths:
            if path in seen:
                continue

            seen.add(path)
            ordered.append(path)

        return ordered

    # =========================================================
    # JSON COMPATIBILITY
    # =========================================================

    def _extract_json_object(
        self,
        text: str,
    ) -> dict[str, Any] | None:
        """
        Compatibilidad con versiones anteriores.
        """

        candidates = self._extract_json_candidates(text)

        return candidates[0] if candidates else None

    def _normalize_data(
        self,
        data: Any,
    ) -> dict[str, Any] | None:

        if not isinstance(data, dict):
            return None

        return self._normalize_dict(data)

    # =========================================================
    # REPAIR
    # =========================================================

    def _try_repair_code_artifact(
        self,
        text: str,
    ) -> dict[str, Any] | None:
        """
        Intenta reparar respuestas casi-JSON.

        Se conserva para compatibilidad con versiones anteriores.
        """

        if "code_artifact" not in text and '"files"' not in text:
            return None

        # -----------------------------------------------------
        # PATH
        # -----------------------------------------------------

        path_match = re.search(
            r'"path"\s*:\s*"((?:\\.|[^"\\])*)"',
            text,
            re.IGNORECASE,
        )

        if not path_match:
            return None

        try:
            path = json.loads('"' + path_match.group(1) + '"')
        except (
            json.JSONDecodeError,
            TypeError,
            ValueError,
        ):
            path = path_match.group(1)

        # -----------------------------------------------------
        # CONTENT
        # -----------------------------------------------------

        content_match = re.search(
            r'"content"\s*:\s*"',
            text,
            re.IGNORECASE,
        )

        if not content_match:
            return None

        quote_start = content_match.end() - 1
        decoder = json.JSONDecoder()

        try:
            content, _ = decoder.raw_decode(text[quote_start:])

            if isinstance(content, str):
                return {
                    "type": "code_artifact",
                    "files": [
                        {
                            "path": str(path),
                            "content": content,
                        }
                    ],
                }

        except json.JSONDecodeError:
            pass

        # -----------------------------------------------------
        # FALLBACK CONTEXTUAL
        # -----------------------------------------------------

        start = content_match.end()

        end = self._find_repair_content_end(
            text=text,
            start=start,
        )

        if end is None:
            return None

        raw_content = text[start:end]

        try:
            content = json.loads('"' + raw_content + '"')
        except (
            json.JSONDecodeError,
            TypeError,
            ValueError,
        ):
            content = self._decode_repaired_content(raw_content)

        if not isinstance(content, str):
            return None

        return {
            "type": "code_artifact",
            "files": [
                {
                    "path": str(path),
                    "content": content,
                }
            ],
        }

    def _find_repair_content_end(
        self,
        text: str,
        start: int,
    ) -> int | None:

        escaped = False

        for index in range(
            start,
            len(text),
        ):
            char = text[index]

            if escaped:
                escaped = False
                continue

            if char == "\\":
                escaped = True
                continue

            if char != '"':
                continue

            suffix = text[index + 1 :]

            if re.match(
                r"\s*(?:" r"\}" r"|\]\s*\}" r"|\}\s*\]" r"|\}\s*," r"|\]\s*," r")",
                suffix,
            ):
                return index

        return None

    def _decode_repaired_content(
        self,
        raw_content: str,
    ) -> str:

        return (
            raw_content.replace("\\\r\n", "\n")
            .replace("\\\n", "\n")
            .replace("\\\r", "\r")
            .replace("\\\t", "\t")
            .replace('\\"', '"')
            .replace("\\/", "/")
            .replace("\\\\", "\\")
        )

    # =========================================================
    # CONFIRMATION DETECTION
    # =========================================================

    def _looks_like_confirmation(
        self,
        text: str,
    ) -> bool:

        normalized = text.lower().strip()

        if not normalized:
            return False

        confirmation_patterns = (
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
            and any(pattern in normalized for pattern in confirmation_patterns)
            and "<html" not in normalized
            and "<!doctype" not in normalized
        )
