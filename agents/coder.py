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

        artifact = self._parse_artifact(
            raw=raw,
            fallback_paths=requested_paths,
            fallback_path=(params.get("path") or target_path),
        )

        # -----------------------------------------------------
        # Código general
        # -----------------------------------------------------

        if not is_landing:
            return artifact

        # -----------------------------------------------------
        # Landing: validar contrato
        # -----------------------------------------------------

        artifact = self._enforce_landing_contract(
            artifact=artifact,
            expected_path=target_path,
            raw=raw,
        )

        if artifact.get("files"):
            return artifact

        # =====================================================
        # SEGUNDO INTENTO
        # =====================================================

        logger.warning(
            "CoderAgent landing inválida en 1er intento. "
            "Segundo intento HTML puro, manteniendo la tarea "
            "original y sin producto hardcodeado."
        )

        html_context: dict[str, Any] = {
            "agent_role": self.role,
            "lean_prompt": True,
            "coding_task": (
                coding_task + "\n\n"
                "SEGUNDO INTENTO:\n"
                "Devuelve ÚNICAMENTE HTML5 completo.\n"
                "No devuelvas JSON.\n"
                "No uses markdown.\n"
                "No escribas prosa.\n"
                f"El documento corresponde al path {target_path}."
            ),
            "requested_output": f"""
SEGUNDO INTENTO — HTML PURO
===========================

DEVUELVE ÚNICAMENTE HTML PURO.

No devuelvas JSON.
No uses markdown.
No uses ```html.
No escribas análisis.
No escribas explicaciones.
No escribas confirmaciones.

El resultado debe comenzar exactamente con:

<!DOCTYPE html>

Y terminar exactamente con:

</html>

REQUISITOS:

- <html lang="es">
- <head>
- <meta charset="UTF-8">
- meta viewport
- <title>
- meta description de máximo 155 caracteres
- og:title
- og:description
- og:type="website"
- <style> con CSS autocontenido
- <body>
- <header>
- <main>
- al menos 4 <section>
- <footer>
- exactamente un <h1>
- CTA mediante <a> o <button>
- diseño mobile-first
- HTML completo
- contenido específico de la TAREA DEL USUARIO
- no inventar otro producto
- no devolver confirmaciones
- no devolver análisis
- no devolver texto fuera del HTML

PATH CONCEPTUAL:

{target_path}
""".strip(),
            "requested_paths": requested_paths,
        }

        raw2 = LLMRouter().generate(
            plan=plan,
            context=html_context,
        )

        logger.info(
            "CoderAgent respuesta LLM (2º intento HTML) | chars=%s | prefix=%r",
            len(raw2) if isinstance(raw2, str) else -1,
            raw2[:250] if isinstance(raw2, str) else raw2,
        )

        artifact = self._parse_artifact(
            raw=raw2,
            fallback_paths=requested_paths,
            fallback_path=(params.get("path") or target_path),
        )

        return self._enforce_landing_contract(
            artifact=artifact,
            expected_path=target_path,
            raw=raw2,
        )

    # =========================================================
    # PARSER
    # =========================================================

    def _parse_artifact(
        self,
        raw: Any,
        fallback_paths: list[str] | None = None,
        fallback_path: str | None = None,
    ) -> dict[str, Any]:
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

        if not text:
            return {
                "type": "code_artifact",
                "files": [],
                "error": "La respuesta del LLM está vacía.",
            }

        # =====================================================
        # HTML PURO
        # =====================================================

        html_text = self._extract_raw_html(text)

        if html_text is not None:
            path = (fallback_paths[0] if fallback_paths else None) or fallback_path or "output.html"

            logger.info(
                "CoderAgent recibió HTML crudo | path=%s | chars=%s",
                path,
                len(html_text),
            )

            return {
                "type": "code_artifact",
                "files": [
                    {
                        "path": path,
                        "content": html_text,
                    }
                ],
            }

        # =====================================================
        # MARKDOWN FENCES
        # =====================================================

        fenced = re.search(
            r"```(?:json|javascript|js|html)?\s*([\s\S]*?)```",
            text,
            re.IGNORECASE,
        )

        if fenced:
            text = fenced.group(1).strip()

            html_text = self._extract_raw_html(text)

            if html_text is not None:
                path = (
                    (fallback_paths[0] if fallback_paths else None)
                    or fallback_path
                    or "output.html"
                )

                return {
                    "type": "code_artifact",
                    "files": [
                        {
                            "path": path,
                            "content": html_text,
                        }
                    ],
                }

        # =====================================================
        # JSON DIRECTO
        # =====================================================

        data = self._try_load_json(text)

        if data is not None:
            normalized = self._normalize_data(data)

            if normalized is not None:
                return normalized

        # =====================================================
        # JSON EMBEBIDO
        # =====================================================

        candidates = self._extract_json_candidates(text)

        for candidate in candidates:
            normalized = self._normalize_data(candidate)

            if normalized is not None:
                return normalized

        # =====================================================
        # REPAIR
        # =====================================================

        repaired = self._try_repair_code_artifact(text)

        if repaired is not None:
            normalized = self._normalize_dict(repaired)

            if normalized is not None:
                return normalized

        # =====================================================
        # CONFIRMACIÓN
        # =====================================================

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

    @staticmethod
    def _unescape_html_content(content: str) -> str:
        """
        Normaliza HTML que puede haber quedado doble-escapado
        durante el parseo/reparación del JSON.
        """

        if not content:
            return content

        text = content

        if "\\\n" in text or '\\"' in text or "\\/" in text:
            try:
                text = json.loads(f'"{text}"')
            except Exception:
                text = (
                    content.replace("\\\r\n", "\n")
                    .replace("\\\n", "\n")
                    .replace("\\\r", "\r")
                    .replace("\\\t", "\t")
                    .replace('\\"', '"')
                    .replace("\\/", "/")
                    .replace("\\\\", "\\")
                )

        return text

    @staticmethod
    def _ensure_html_lang_es(content: str) -> str:
        """
        Garantiza lang="es" en el tag <html> cuando no existe.
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

    # =========================================================
    # LANDING CONTRACT
    # =========================================================

    def _enforce_landing_contract(
        self,
        artifact: dict[str, Any],
        expected_path: str | None,
        raw: Any,
    ) -> dict[str, Any]:
        files = artifact.get("files")

        if not isinstance(files, list) or not files:
            logger.error("CoderAgent landing inválida: no existe ningún archivo.")

            return {
                "type": "code_artifact",
                "files": [],
                "error": ("La generación de landing falló: " "el CoderAgent no produjo HTML."),
            }

        if len(files) != 1:
            logger.warning(
                "CoderAgent landing devolvió %s archivos; " "se utilizará únicamente el primero.",
                len(files),
            )

        file = files[0]

        if not isinstance(file, dict):
            logger.error("CoderAgent landing inválida: " "primer archivo no es dict.")

            return {
                "type": "code_artifact",
                "files": [],
                "error": ("La generación de landing falló: " "artifact inválido."),
            }

        # =====================================================
        # CONTENT
        # =====================================================

        content = str(file.get("content") or "")

        content = self._unescape_html_content(content)
        content = self._ensure_html_lang_es(content)

        actual_path = str(file.get("path") or "")

        # =====================================================
        # PATH
        # =====================================================

        if expected_path:
            expected_path = str(expected_path)

            if actual_path != expected_path:
                logger.warning(
                    "CoderAgent corrigiendo path de landing | " "actual=%s | esperado=%s",
                    actual_path,
                    expected_path,
                )

            actual_path = expected_path

        if not actual_path:
            actual_path = "output.html"

        # =====================================================
        # VALIDAR EXTENSIÓN
        # =====================================================

        if not actual_path.lower().endswith((".html", ".htm")):
            logger.warning(
                "CoderAgent path de landing no termina en " ".html/.htm | path=%s",
                actual_path,
            )

            return {
                "type": "code_artifact",
                "files": [],
                "error": (
                    "La generación de landing falló: " "el path debe terminar en .html o .htm."
                ),
            }

        # =====================================================
        # VALIDAR CONTENIDO
        # =====================================================

        validation_error = self._validate_landing_content(content)

        if validation_error:
            logger.error(
                "CoderAgent landing inválida | " "path=%s | error=%s",
                actual_path,
                validation_error,
            )

            result: dict[str, Any] = {
                "type": "code_artifact",
                "files": [],
                "error": validation_error,
            }

            if raw is not None:
                raw_text = raw if isinstance(raw, str) else str(raw)

                result["raw_response"] = raw_text[:2000]

            return result

        # =====================================================
        # RESULTADO NORMALIZADO
        # =====================================================

        result = {
            "type": "code_artifact",
            "files": [
                {
                    "path": actual_path,
                    "content": content,
                }
            ],
        }

        logger.info(
            "CoderAgent landing válida | path=%s | chars=%s",
            actual_path,
            len(content),
        )

        return result

    # =========================================================
    # LANDING VALIDATION
    # =========================================================

    def _validate_landing_content(
        self,
        content: str,
    ) -> str | None:
        if not content.strip():
            return "La generación de landing falló: " "el HTML está vacío."

        if self._looks_like_confirmation(content):
            return (
                "La generación de landing falló: "
                "el modelo devolvió una confirmación "
                "en lugar de HTML."
            )

        html = content.strip()
        lower = html.lower()

        # =====================================================
        # DOCTYPE
        # =====================================================

        if not re.match(
            r"^<!doctype\s+html\b",
            html,
            re.IGNORECASE,
        ):
            return "La generación de landing falló: " "el HTML debe comenzar con <!DOCTYPE html>."

        # =====================================================
        # HTML END
        # =====================================================

        if not re.search(
            r"</html\s*>\s*$",
            html,
            re.IGNORECASE,
        ):
            return "La generación de landing falló: " "el HTML debe terminar con </html>."

        # =====================================================
        # HTML LANG
        # =====================================================

        html_tag = re.search(
            r"<html\b([^>]*)>",
            html,
            re.IGNORECASE,
        )

        if not html_tag:
            return "La generación de landing falló: " "falta <html>."

        lang_match = re.search(
            r"""\blang\s*=\s*["']([^"']+)["']""",
            html_tag.group(1),
            re.IGNORECASE,
        )

        if not lang_match:
            return "La generación de landing falló: " 'falta lang="es" en <html>.'

        if lang_match.group(1).strip().lower() != "es":
            return "La generación de landing falló: " '<html> debe tener lang="es".'

        # =====================================================
        # TAGS OBLIGATORIOS
        # =====================================================

        required_tags = (
            "head",
            "body",
            "header",
            "main",
            "footer",
            "style",
            "title",
        )

        for tag in required_tags:
            if not re.search(
                rf"<{tag}\b",
                lower,
            ):
                return "La generación de landing falló: " f"falta <{tag}>."

        # =====================================================
        # CIERRES
        # =====================================================

        if not re.search(
            r"</head\s*>",
            lower,
        ):
            return "La generación de landing falló: " "falta </head>."

        if not re.search(
            r"</body\s*>",
            lower,
        ):
            return "La generación de landing falló: " "falta </body>."

        # =====================================================
        # CHARSET
        # =====================================================

        if not re.search(
            r'<meta\b[^>]*charset\s*=\s*["\']?\s*utf-8',
            lower,
            re.IGNORECASE,
        ):
            return "La generación de landing falló: " 'falta <meta charset="UTF-8">.'

        # =====================================================
        # VIEWPORT
        # =====================================================

        viewport_match = re.search(
            r'<meta\b[^>]*name\s*=\s*["\']viewport["\']' r'[^>]*content\s*=\s*["\'][^"\']+["\']',
            html,
            re.IGNORECASE,
        )

        if not viewport_match:
            viewport_match = re.search(
                r'<meta\b[^>]*content\s*=\s*["\'][^"\']+["\']'
                r'[^>]*name\s*=\s*["\']viewport["\']',
                html,
                re.IGNORECASE,
            )

        if not viewport_match:
            return "La generación de landing falló: " "falta meta viewport."

        # =====================================================
        # TITLE
        # =====================================================

        title_match = re.search(
            r"<title\b[^>]*>([\s\S]*?)</title\s*>",
            html,
            re.IGNORECASE,
        )

        if not title_match:
            return "La generación de landing falló: " "falta <title>."

        if not title_match.group(1).strip():
            return "La generación de landing falló: " "el <title> está vacío."

        # =====================================================
        # META DESCRIPTION
        # =====================================================

        description = self._get_meta_name_content(
            html,
            "description",
        )

        if description is None:
            return "La generación de landing falló: " 'falta meta name="description".'

        description = description.strip()

        if not description:
            return "La generación de landing falló: " "la meta description está vacía."

        if len(description) > 155:
            return (
                "La generación de landing falló: "
                "la meta description supera 155 caracteres "
                f"({len(description)})."
            )

        # =====================================================
        # OPEN GRAPH
        # =====================================================

        for property_name in (
            "og:title",
            "og:description",
            "og:type",
        ):
            if not self._has_meta_property(
                html,
                property_name,
            ):
                return "La generación de landing falló: " f'falta meta property="{property_name}".'

        og_type = self._get_meta_property_content(
            html,
            "og:type",
        )

        if not og_type:
            return "La generación de landing falló: " "og:type no tiene contenido."

        if og_type.strip().lower() != "website":
            return "La generación de landing falló: " 'og:type debe ser "website".'

        # =====================================================
        # H1
        # =====================================================

        h1_count = len(
            re.findall(
                r"<h1\b",
                lower,
            )
        )

        if h1_count != 1:
            return (
                "La generación de landing falló: "
                "debe existir exactamente un H1, "
                f"encontrado={h1_count}."
            )

        # =====================================================
        # SECTIONS
        # =====================================================

        section_count = len(
            re.findall(
                r"<section\b",
                lower,
            )
        )

        if section_count < 4:
            return (
                "La generación de landing falló: "
                "debe contener al menos 4 <section>, "
                f"encontrado={section_count}."
            )

        # =====================================================
        # CTA
        # =====================================================

        if not self._has_conversion_cta(html):
            return "La generación de landing falló: " "no se encontró un CTA de conversión."

        # =====================================================
        # STYLE
        # =====================================================

        style_match = re.search(
            r"<style\b[^>]*>([\s\S]*?)</style\s*>",
            html,
            re.IGNORECASE,
        )

        if not style_match:
            return "La generación de landing falló: " "falta <style>."

        if not style_match.group(1).strip():
            return "La generación de landing falló: " "el <style> está vacío."

        # =====================================================
        # BODY
        # =====================================================

        body_match = re.search(
            r"<body\b[^>]*>([\s\S]*?)</body\s*>",
            html,
            re.IGNORECASE,
        )

        if not body_match:
            return "La generación de landing falló: " "no se pudo localizar correctamente <body>."

        if not body_match.group(1).strip():
            return "La generación de landing falló: " "el <body> está vacío."

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
    # RAW HTML
    # =========================================================

    def _extract_raw_html(
        self,
        text: str,
    ) -> str | None:
        stripped = text.strip()

        if not stripped:
            return None

        # -----------------------------------------------------
        # Documento completo con DOCTYPE
        # -----------------------------------------------------

        if re.match(
            r"^<!doctype\s+html\b",
            stripped,
            re.IGNORECASE,
        ):
            if re.search(
                r"</html\s*>\s*$",
                stripped,
                re.IGNORECASE,
            ):
                return stripped

        # -----------------------------------------------------
        # HTML completo sin DOCTYPE
        # -----------------------------------------------------

        if re.match(
            r"^<html\b",
            stripped,
            re.IGNORECASE,
        ):
            if re.search(
                r"</html\s*>\s*$",
                stripped,
                re.IGNORECASE,
            ):
                return stripped

        # -----------------------------------------------------
        # HTML rodeado de texto
        # -----------------------------------------------------

        match = re.search(
            r"<!doctype\s+html[\s\S]*?</html\s*>",
            stripped,
            re.IGNORECASE,
        )

        if match:
            return match.group(0).strip()

        return None

    # =========================================================
    # JSON
    # =========================================================

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
        que puede contener texto adicional.
        """

        decoder = json.JSONDecoder()
        candidates: list[dict[str, Any]] = []

        for match in re.finditer(
            r"\{",
            text,
        ):
            start = match.start()

            try:
                data, _ = decoder.raw_decode(text[start:])
            except json.JSONDecodeError:
                continue

            if not isinstance(data, dict):
                continue

            if data not in candidates:
                candidates.append(data)

        return candidates

    def _extract_json_object(
        self,
        text: str,
    ) -> dict[str, Any] | None:
        """
        Compatibilidad con versiones anteriores.
        """

        candidates = self._extract_json_candidates(text)

        return candidates[0] if candidates else None

    # =========================================================
    # REPAIR
    # =========================================================

    def _try_repair_code_artifact(
        self,
        text: str,
    ) -> dict[str, Any] | None:
        """
        Intenta reparar respuestas casi-JSON.
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
    # NORMALIZATION
    # =========================================================

    def _normalize_data(
        self,
        data: Any,
    ) -> dict[str, Any] | None:
        if not isinstance(data, dict):
            return None

        return self._normalize_dict(data)

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
