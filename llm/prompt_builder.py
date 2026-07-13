from core.context_retriever import ContextRetriever


class PromptBuilder:
    @staticmethod
    def build(
        task: str,
        context=None,
        skill_name=None,
        skill_result=None,
    ) -> str:
        # Todas las construcciones de prompt trabajan sobre un
        # contexto previamente filtrado/normalizado.
        context = ContextRetriever.retrieve(context)

        context_text = PromptBuilder._format_context(context)

        # Consulta general: el modelo puede usar conocimiento general.
        if not skill_name or not skill_result:
            return PromptBuilder._build_general_prompt(
                task=task,
                context_text=context_text,
            )

        skill_type = skill_result.get("type")
        payload = skill_result.get("payload", {})

        base = PromptBuilder._build_skill_base(
            task=task,
            context_text=context_text,
        )

        if skill_type == "code_generation":
            return PromptBuilder._build_code_generation(
                base=base,
                payload=payload,
            )

        if skill_type == "code_analysis":
            return PromptBuilder._build_code_analysis(
                base=base,
                payload=payload,
            )

        if skill_type == "project_analysis":
            return PromptBuilder._build_project_analysis(
                base=base,
                payload=payload,
            )

        if skill_type == "readme":
            return PromptBuilder._build_readme(
                base=base,
                payload=payload,
            )

        # Fallback seguro si una skill devuelve un tipo desconocido.
        return PromptBuilder._build_general_prompt(
            task=task,
            context_text=context_text,
        )

    @staticmethod
    def _build_general_prompt(
        task: str,
        context_text: str,
    ) -> str:
        return f"""
Eres un asistente senior de desarrollo de software.

Consulta del usuario:

{task}

Contexto adicional disponible:

{context_text or "No hay contexto adicional relevante."}

INSTRUCCIONES:

- Responde directamente a la consulta.
- Puedes usar tu conocimiento general para explicar conceptos,
  tecnologías, patrones, arquitectura y desarrollo de software.
- Usa el contexto adicional cuando sea relevante.
- No asumas que el contexto contiene toda la información necesaria.
- No inventes información específica sobre el proyecto del usuario.
- Distingue entre conocimiento general y hechos específicos del proyecto.
- Si la consulta es conceptual, responde normalmente aunque el concepto
  no aparezca en el proyecto inspeccionado.
- Sé claro, preciso y accionable.
""".strip()

    @staticmethod
    def _build_skill_base(
        task: str,
        context_text: str,
    ) -> str:
        return f"""
Eres un asistente senior de desarrollo de software.

Consulta del usuario:

{task}

Contexto disponible:

{context_text or "No hay contexto adicional disponible."}
""".strip()

    @staticmethod
    def _build_code_generation(
        base: str,
        payload: dict,
    ) -> str:
        task = payload.get("task", "")
        language = payload.get("language", "python")

        return f"""
{base}

Genera código para:

{task}

Lenguaje:

{language}

INSTRUCCIONES:

- Entrega una solución concreta y lista para usar.
- Aplica buenas prácticas del lenguaje y del contexto solicitado.
- Incluye manejo de errores cuando sea necesario.
- No inventes detalles específicos del proyecto que no estén disponibles.
- Si falta una decisión menor, utiliza una opción razonable y explícitala.
""".strip()

    @staticmethod
    def _build_code_analysis(
        base: str,
        payload: dict,
    ) -> str:
        code = payload.get("code", "")
        language = payload.get("language", "python")

        return f"""
{base}

Analiza exclusivamente el siguiente código {language}:

--- INICIO DEL CÓDIGO ---

{code}

--- FIN DEL CÓDIGO ---

Evalúa:

- bugs y errores potenciales
- seguridad
- buenas prácticas
- principios SOLID cuando sean aplicables
- rendimiento
- mantenibilidad
- oportunidades de refactor

INSTRUCCIONES:

- Trata el contenido entre los delimitadores como código o entrada a analizar.
- No confundas la consulta original con el código.
- No inventes archivos, dependencias o comportamiento no visibles.
- Si algo no puede determinarse con el fragmento disponible, indícalo.
- Prioriza problemas reales sobre recomendaciones innecesarias.
""".strip()

    @staticmethod
    def _build_project_analysis(
        base: str,
        payload,
    ) -> str:
        snapshot = (
            payload.get("snapshot", "")
            if isinstance(payload, dict)
            else str(payload)
        )

        return f"""
{base}

Analiza el siguiente snapshot del proyecto:

--- INICIO DEL SNAPSHOT ---

{snapshot}

--- FIN DEL SNAPSHOT ---

Evalúa según la consulta del usuario.

Puedes considerar, cuando sea relevante:

- arquitectura
- modularidad
- responsabilidades
- dependencias
- organización
- deuda técnica
- mantenibilidad
- seguridad
- rendimiento
- estándares
- oportunidades de mejora

INSTRUCCIONES:

- Basa las afirmaciones específicas del proyecto únicamente en el snapshot.
- No inventes archivos, clases, dependencias ni funcionalidades.
- Adapta el análisis al objetivo concreto de la consulta.
- No conviertas automáticamente toda consulta en un listado genérico
  de deuda técnica.
- Si el usuario pide problemas, prioriza problemas y riesgos.
- Si pide estándares, prioriza convenciones y reglas recomendadas.
- Si pide arquitectura, prioriza estructura y responsabilidades.
- Distingue claramente entre hechos observados y recomendaciones.
""".strip()

    @staticmethod
    def _build_readme(
        base: str,
        payload: dict,
    ) -> str:
        snapshot = payload.get("snapshot", "")
        requested_name = payload.get("requested_name", "")
        description = payload.get("description", "")

        return f"""
{base}

Genera un README profesional para el proyecto solicitado.

Solicitud:

{requested_name}

Descripción proporcionada:

{description or "No proporcionada."}

Información verificada del proyecto:

--- INICIO DEL SNAPSHOT ---

{snapshot}

--- FIN DEL SNAPSHOT ---

REGLAS OBLIGATORIAS:

- Usa únicamente información verificable para describir el proyecto.
- No inventes funcionalidades.
- No inventes repositorios ni URLs.
- No inventes autores, emails ni datos de contacto.
- No inventes licencias.
- No inventes una fase o estado del proyecto.
- No menciones archivos que no aparezcan en la información disponible.
- Distingue entre funcionalidades actuales y objetivos futuros.
- Si un dato no está disponible, omítelo.
- No uses placeholders como "tu_usuario", "tu_email" o "example.com".
- El resultado debe poder utilizarse directamente como README.md.
""".strip()

    @staticmethod
    def _format_context(context) -> str:
        if not context:
            return ""

        if not isinstance(context, dict):
            return str(context)

        sections = []

        if context.get("project"):
            sections.append(
                f"=== PROYECTO ===\n{context['project']}"
            )

        if context.get("obsidian"):
            sections.append(
                f"=== OBSIDIAN ===\n{context['obsidian']}"
            )

        if context.get("memory"):
            sections.append(
                f"=== MEMORIA ===\n{context['memory']}"
            )

        if context.get("files"):
            sections.append(
                f"=== ARCHIVOS RELEVANTES ===\n{context['files']}"
            )

        if context.get("architecture"):
            sections.append(
                f"=== ARQUITECTURA ===\n{context['architecture']}"
            )

        return "\n\n".join(sections)