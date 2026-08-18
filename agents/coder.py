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
    version = "2.5"
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

        task = str(params.get("task") or plan.objective or plan.original_task or "")

        requested_paths = self._collect_requested_paths(plan, step)

        if requested_paths:
            context["requested_paths"] = requested_paths

        # ---------------------------------------------------------
        # Detectar landing / HTML
        # ---------------------------------------------------------

        is_landing = any(
            p.lower().endswith((".html", ".htm")) or "landing" in p.lower() for p in requested_paths
        )

        task_lower = task.lower()

        is_landing = (
            is_landing
            or "landing" in task_lower
            or ".html" in task_lower
            or "página web" in task_lower
            or "pagina web" in task_lower
        )

        context.setdefault("agent_role", self.role)

        dependency_text = context.get("dependency_text")
        has_analysis = isinstance(dependency_text, str) and bool(dependency_text.strip())

        logger.info(
            "CoderAgent contexto | plan=%s | landing=%s | "
            "requested_paths=%s | dependency_text=%s | dependency_chars=%s",
            plan.id,
            is_landing,
            requested_paths,
            has_analysis,
            len(dependency_text.strip()) if has_analysis else 0,
        )

        target_path = (
            requested_paths[0] if requested_paths else str(params.get("path") or "landing.html")
        )

        # ---------------------------------------------------------
        # Construir prompt
        # ---------------------------------------------------------

        if is_landing:
            analysis_block = ""

            if has_analysis:
                analysis_block = f"""
ANÁLISIS PREVIO DE LA LANDING DE REFERENCIA
===========================================
Usa el siguiente análisis como inspiración de estructura,
copy y elementos de conversión.

Adapta TODO al producto "chocolate artesanal".

No copies marcas, nombres ni claims de terceros.

--- BEGIN ANALYSIS ---
{dependency_text[:6000]}
--- END ANALYSIS ---
"""

            context["requested_output"] = f"""
CONTRATO OBLIGATORIO – LANDING HTML
===================================

Devuelve ÚNICAMENTE JSON válido.
No uses markdown.
No agregues explicaciones.
No agregues confirmaciones.

{{
  "type": "code_artifact",
  "files": [
    {{
      "path": "{target_path}",
      "content": "<!DOCTYPE html>...HTML completo...</html>"
    }}
  ]
}}

REGLAS ABSOLUTAS:

1. "type" debe ser exactamente "code_artifact".
2. Debe existir exactamente un archivo.
3. "path" debe ser exactamente "{target_path}".
4. "content" debe contener HTML5 completo.
5. El contenido debe comenzar con <!DOCTYPE html>.
6. El contenido debe terminar con </html>.
7. Debe existir <title>.
8. Debe existir meta name="description".
9. Debe existir og:title.
10. Debe existir og:description.
11. Debe existir og:type="website".
12. Debe existir <header>, <main>, <section> y <footer>.
13. Debe existir exactamente un <h1>.
14. Debe existir <style> con CSS autocontenido.
15. Debe existir meta viewport para comportamiento mobile-first.
16. Debe existir un CTA mediante <a> o <button>.
17. Producto: chocolate artesanal.
18. La página debe ser autocontenida.
19. No escribas archivos ni confirmes que escribiste archivos.
20. Escapa correctamente saltos de línea y comillas para producir JSON válido.

{analysis_block}
"""

        else:
            context.setdefault(
                "requested_output",
                (
                    "Responde ÚNICAMENTE con JSON válido de tipo "
                    "code_artifact. "
                    '{"type":"code_artifact","files":['
                    '{"path":"...","content":"..."}]}. '
                    "No uses markdown ni texto adicional. "
                    "Escapa correctamente el contenido."
                ),
            )

        context["coding_task"] = task

        # ---------------------------------------------------------
        # Primer intento
        # ---------------------------------------------------------

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
            fallback_path=params.get("path"),
        )

        if not is_landing:
            return artifact

        # ---------------------------------------------------------
        # Validar contrato de landing
        # ---------------------------------------------------------

        artifact = self._enforce_landing_contract(
            artifact=artifact,
            expected_path=target_path,
            raw=raw,
        )

        if artifact.get("files"):
            return artifact

        # ---------------------------------------------------------
        # Segundo intento:
        # pedir HTML PURO, no JSON.
        #
        # Esto elimina una capa completa de posibles errores
        # de escaping JSON.
        # ---------------------------------------------------------

        logger.warning(
            "CoderAgent landing inválida en 1er intento. "
            "Ejecutando segundo intento con HTML puro."
        )

        html_context = dict(context)

        html_context["requested_output"] = f"""
DEVUELVE ÚNICAMENTE HTML PURO.

No devuelvas JSON.
No uses markdown.
No uses ```html.
No agregues explicaciones.
No confirmes que creaste un archivo.

El resultado debe comenzar exactamente con:
<!DOCTYPE html>

Y debe terminar con:
</html>

Requisitos obligatorios:

- <html>
- <head>
- <meta charset="UTF-8">
- meta viewport
- <title>
- meta name="description"
- og:title
- og:description
- og:type="website"
- <style>
- <body>
- <header>
- <main>
- <section>
- exactamente un <h1>
- un CTA mediante <a> o <button>
- <footer>

Producto:
chocolate artesanal.

La página debe ser autocontenida y mobile-first.
"""

        # El análisis largo puede provocar que el segundo intento
        # vuelva a desviarse del formato.
        html_context.pop("dependency_text", None)

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
            fallback_path=params.get("path"),
        )

        artifact = self._enforce_landing_contract(
            artifact=artifact,
            expected_path=target_path,
            raw=raw2,
        )

        return artifact

    # =========================================================
    # PARSER
    # =========================================================

    def _parse_artifact(
        self,
        raw: Any,
        fallback_paths: list[str] | None = None,
        fallback_path: str | None = None,
    ) -> dict[str, Any]:
        text = raw if isinstance(raw, str) else json.dumps(raw, ensure_ascii=False)

        text = text.strip()

        if not text:
            return {
                "type": "code_artifact",
                "files": [],
                "error": "La respuesta del LLM está vacía.",
            }

        # ---------------------------------------------------------
        # HTML puro primero
        #
        # Si el modelo respondió HTML, no intentamos interpretarlo
        # como JSON.
        # ---------------------------------------------------------

        html_text = self._extract_raw_html(text)

        if html_text is not None:
            path = (
                (fallback_paths[0] if fallback_paths else None)
                or fallback_path
                or "src/generated/output.html"
            )

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

        # ---------------------------------------------------------
        # Quitar fences markdown
        # ---------------------------------------------------------

        fenced = re.search(
            r"```(?:json)?\s*([\s\S]*?)```",
            text,
            re.IGNORECASE,
        )

        if fenced:
            text = fenced.group(1).strip()

        # ---------------------------------------------------------
        # JSON directo
        # ---------------------------------------------------------

        data = self._try_load_json(text)

        if data is not None:
            normalized = self._normalize_dict(data)

            if normalized is not None:
                return normalized

        # ---------------------------------------------------------
        # Buscar candidatos JSON y aceptar solamente candidatos
        # que realmente normalicen a code_artifact.
        # ---------------------------------------------------------

        candidates = self._extract_json_candidates(text)

        for candidate in candidates:
            normalized = self._normalize_dict(candidate)

            if normalized is not None:
                return normalized

        # ---------------------------------------------------------
        # Reparación tolerante
        # ---------------------------------------------------------

        repaired = self._try_repair_code_artifact(text)

        if repaired is not None:
            normalized = self._normalize_dict(repaired)

            if normalized is not None:
                return normalized

        # ---------------------------------------------------------
        # Confirmación / texto no-code
        # ---------------------------------------------------------

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
                    "CoderAgent recibió una confirmación o texto " "en lugar de un code_artifact."
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

        # Para una landing el contrato establece exactamente un
        # archivo.
        if len(files) != 1:
            logger.warning(
                "CoderAgent landing devolvió %s archivos; " "se utilizará únicamente el primero.",
                len(files),
            )

        file = files[0]

        if not isinstance(file, dict):
            logger.error("CoderAgent landing inválida: primer archivo no es dict.")

            return {
                "type": "code_artifact",
                "files": [],
                "error": ("La generación de landing falló: " "artifact inválido."),
            }

        content = str(file.get("content") or "")
        actual_path = str(file.get("path") or "")

        # ---------------------------------------------------------
        # Forzar path esperado
        # ---------------------------------------------------------

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
            actual_path = "landing.html"

        # ---------------------------------------------------------
        # Validar contenido
        # ---------------------------------------------------------

        validation_error = self._validate_landing_content(content)

        if validation_error:
            logger.error(
                "CoderAgent landing inválida | path=%s | error=%s",
                actual_path,
                validation_error,
            )

            result = {
                "type": "code_artifact",
                "files": [],
                "error": validation_error,
            }

            # Útil para diagnóstico, pero limitado para no generar
            # artifacts gigantes.
            if raw is not None:
                result["raw_response"] = (raw if isinstance(raw, str) else str(raw))[:2000]

            return result

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

    def _validate_landing_content(
        self,
        content: str,
    ) -> str | None:
        if not content.strip():
            return "La generación de landing falló: " "el HTML está vacío."

        if self._looks_like_confirmation(content):
            return (
                "La generación de landing falló: "
                "el modelo devolvió una confirmación en lugar de HTML."
            )

        # ---------------------------------------------------------
        # Estructura básica
        # ---------------------------------------------------------

        stripped = content.lstrip()
        lower = content.lower()

        if not stripped.lower().startswith("<!doctype html"):
            return "La generación de landing falló: " "el HTML debe comenzar con <!DOCTYPE html>."

        if "</html>" not in lower:
            return "La generación de landing falló: " "el HTML no contiene </html>."

        required_markers = {
            "<html": "<html>",
            "<head": "<head>",
            "<body": "<body>",
            "<header": "<header>",
            "<main": "<main>",
            "<section": "<section>",
            "<footer": "<footer>",
            "<style": "<style>",
            "<title": "<title>",
            "</html>": "</html>",
        }

        missing = [label for marker, label in required_markers.items() if marker not in lower]

        if missing:
            return "La generación de landing falló: " "faltan elementos obligatorios: " + ", ".join(
                missing
            )

        # ---------------------------------------------------------
        # Meta description
        # ---------------------------------------------------------

        if not re.search(
            r'<meta\b[^>]*\bname\s*=\s*["\']description["\']',
            lower,
        ):
            return "La generación de landing falló: " 'falta meta name="description".'

        # ---------------------------------------------------------
        # Open Graph
        # ---------------------------------------------------------

        og_requirements = (
            ("og:title", "og:title"),
            ("og:description", "og:description"),
            ("og:type", "og:type"),
        )

        for property_name, label in og_requirements:
            pattern = r'<meta\b[^>]*\bproperty\s*=\s*["\']' + re.escape(property_name) + r'["\']'

            if not re.search(pattern, lower):
                return "La generación de landing falló: " f"falta {label}."

        # ---------------------------------------------------------
        # og:type debe ser website
        # ---------------------------------------------------------

        og_type_match = re.search(
            r'<meta\b[^>]*\bproperty\s*=\s*["\']og:type["\']'
            r'[^>]*\bcontent\s*=\s*["\']([^"\']+)["\']',
            lower,
        )

        if not og_type_match:
            # Permitir atributos en orden inverso.
            og_type_match = re.search(
                r'<meta\b[^>]*\bcontent\s*=\s*["\']([^"\']+)["\']'
                r'[^>]*\bproperty\s*=\s*["\']og:type["\']',
                lower,
            )

        if not og_type_match:
            return "La generación de landing falló: " "no se pudo determinar og:type."

        if og_type_match.group(1).strip() != "website":
            return "La generación de landing falló: " 'og:type debe ser "website".'

        # ---------------------------------------------------------
        # Viewport
        # ---------------------------------------------------------

        if not re.search(
            r'<meta\b[^>]*\bname\s*=\s*["\']viewport["\']',
            lower,
        ):
            return "La generación de landing falló: " "falta meta viewport."

        # ---------------------------------------------------------
        # H1: exactamente uno
        # ---------------------------------------------------------

        h1_count = len(
            re.findall(
                r"<h1\b",
                lower,
            )
        )

        if h1_count != 1:
            return (
                "La generación de landing falló: "
                f"debe existir exactamente un H1, encontrado={h1_count}."
            )

        # ---------------------------------------------------------
        # CTA
        # ---------------------------------------------------------

        has_anchor_cta = bool(
            re.search(
                r"<a\b[^>]*>[\s\S]*?</a\s*>",
                lower,
            )
        )

        has_button_cta = bool(
            re.search(
                r"<button\b[^>]*>[\s\S]*?</button\s*>",
                lower,
            )
        )

        if not has_anchor_cta and not has_button_cta:
            return (
                "La generación de landing falló: "
                "no se encontró ningún CTA mediante <a> o <button>."
            )

        # ---------------------------------------------------------
        # Cuerpo real
        # ---------------------------------------------------------

        body_match = re.search(
            r"<body\b[^>]*>([\s\S]*?)</body\s*>",
            lower,
        )

        if not body_match:
            return "La generación de landing falló: " "no se pudo localizar correctamente <body>."

        body_content = body_match.group(1).strip()

        if not body_content:
            return "La generación de landing falló: " "el <body> está vacío."

        return None

    # =========================================================
    # PATHS
    # =========================================================

    def _collect_requested_paths(
        self,
        plan: ExecutionPlan,
        step: ExecutionStep,
    ) -> list[str]:
        paths: list[str] = []

        # Primero el path explícito del coder.
        if (step.params or {}).get("path"):
            paths.append(str(step.params["path"]))

        # Buscar write_file que dependa del coder.
        for other in plan.steps:
            if step.id not in (other.depends_on or []):
                continue

            if other.unit_name != "write_file":
                continue

            path = (other.params or {}).get("path")

            if path:
                paths.append(str(path))

        seen: set[str] = set()
        ordered: list[str] = []

        for path in paths:
            if path not in seen:
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

        lower = stripped.lower()

        if lower.startswith("<!doctype html"):
            return stripped

        if lower.startswith("<html"):
            return stripped

        # Algunos modelos pueden devolver una explicación antes
        # del HTML. Solo aceptamos ese caso si podemos localizar
        # un documento HTML completo.
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
        Busca objetos JSON válidos dentro de una respuesta que
        contiene texto adicional.

        A diferencia de _extract_json_object() original, no devuelve
        automáticamente el primer objeto encontrado. Devuelve todos
        los candidatos para que _parse_artifact() pueda elegir el que
        realmente normaliza a code_artifact.
        """

        decoder = json.JSONDecoder()
        candidates: list[dict[str, Any]] = []

        for match in re.finditer(r"\{", text):
            start = match.start()

            try:
                data, _ = decoder.raw_decode(text[start:])
            except json.JSONDecodeError:
                continue

            if not isinstance(data, dict):
                continue

            # Evitar duplicados por igualdad.
            if data not in candidates:
                candidates.append(data)

        return candidates

    def _extract_json_object(
        self,
        text: str,
    ) -> dict[str, Any] | None:
        """
        Compatibilidad con el método anterior.

        Devuelve el primer candidato que exista.
        La selección real del code_artifact se hace en
        _parse_artifact() mediante _extract_json_candidates().
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

        No utiliza rfind('"'), porque eso puede cortar el content
        incorrectamente.

        Primero localiza path y content.
        Para content intenta leer una cadena JSON completa respetando
        escapes. Si el modelo produjo HTML con comillas sin escapar,
        utiliza un cierre contextual como fallback.
        """

        if "code_artifact" not in text and '"files"' not in text:
            return None

        # ---------------------------------------------------------
        # Path
        # ---------------------------------------------------------

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

        # ---------------------------------------------------------
        # Content marker
        # ---------------------------------------------------------

        content_match = re.search(
            r'"content"\s*:\s*"',
            text,
            re.IGNORECASE,
        )

        if not content_match:
            return None

        quote_start = content_match.end() - 1

        # ---------------------------------------------------------
        # Primer intento:
        # interpretar el string con JSONDecoder.
        # ---------------------------------------------------------

        decoder = json.JSONDecoder()

        try:
            content, consumed = decoder.raw_decode(text[quote_start:])

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

        # ---------------------------------------------------------
        # Segundo intento:
        # encontrar un cierre contextual.
        #
        # Buscamos una comilla que sea seguida por la estructura
        # esperada del artifact:
        #
        # "content": "...." }
        #
        # o
        #
        # "content": "...." }
        # ]
        # }
        # ---------------------------------------------------------

        start = content_match.end()
        end = self._find_repair_content_end(
            text=text,
            start=start,
        )

        if end is None:
            return None

        raw_content = text[start:end]

        # ---------------------------------------------------------
        # Decodificar escapes JSON.
        # ---------------------------------------------------------

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
        """
        Encuentra una comilla candidata al cierre de content.

        Se priorizan comillas seguidas por:
            }
            },
            }]
            }]
        etc.

        Esto evita utilizar simplemente la última comilla de toda
        la respuesta.
        """

        escaped = False

        for index in range(start, len(text)):
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
                r"\s*(?:\}|\]\s*\}|\}\s*\]|\}\s*,|\]\s*,)",
                suffix,
            ):
                return index

        return None

    def _decode_repaired_content(
        self,
        raw_content: str,
    ) -> str:
        """
        Fallback para contenido casi-JSON.

        Conserva escapes comunes sin destruir HTML.
        """

        return (
            raw_content.replace("\\r\\n", "\n")
            .replace("\\n", "\n")
            .replace("\\r", "\r")
            .replace("\\t", "\t")
            .replace('\\"', '"')
            .replace("\\/", "/")
            .replace("\\\\", "\\")
        )

    # =========================================================
    # NORMALIZATION
    # =========================================================

    def _normalize_dict(
        self,
        data: dict[str, Any],
    ) -> dict[str, Any] | None:

        # -----------------------------------------------------
        # code_artifact explícito
        # -----------------------------------------------------

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
                        "content": ("" if content is None else str(content)),
                    }
                )

            if files:
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

        if isinstance(data.get("files"), list):
            normalized = dict(data)
            normalized["type"] = "code_artifact"

            return self._normalize_dict(normalized)

        # -----------------------------------------------------
        # path + content
        # -----------------------------------------------------

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
