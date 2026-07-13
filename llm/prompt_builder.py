class PromptBuilder:
    @staticmethod
    def build(
        task,
        context,
        skill_name=None,
        skill_result=None,
    ):
        context_text = PromptBuilder._format_context(context)

        base = f"""
Eres un asistente senior de desarrollo de software.

Consulta del usuario:

{task}

Contexto disponible:

{context_text}

REGLAS GENERALES:

- Usa únicamente información disponible en la consulta, contexto y resultados de skills.
- No inventes archivos, funcionalidades, dependencias, configuraciones ni capacidades.
- Distingue entre hechos observados, inferencias y recomendaciones.
- La ausencia de un archivo en el contexto o snapshot no demuestra que el archivo no exista.
- No afirmes que algo "no existe" si simplemente no fue inspeccionado.
- Si la evidencia es insuficiente, indícalo explícitamente.
"""

        if not skill_name or not skill_result:
            return base

        skill_type = skill_result.get("type")
        payload = skill_result.get("payload", {})

        if skill_type == "code_generation":
            task_text = payload.get("task", task)
            language = payload.get("language", "python")

            return f"""
{base}

Genera código para:

{task_text}

Lenguaje:

{language}

REGLAS:

- Entrega una solución concreta y lista para usar.
- No inventes dependencias innecesarias.
- Incluye manejo de errores cuando sea pertinente.
- Mantén una estructura simple y coherente con la solicitud.
"""

        if skill_type == "code_analysis":
            code = payload.get("code", "")
            language = payload.get("language", "python")

            return f"""
{base}

Analiza exclusivamente el siguiente código {language}:

=== CÓDIGO A ANALIZAR ===

{code}

Evalúa:

- bugs y errores potenciales;
- seguridad;
- buenas prácticas;
- principios SOLID cuando sean aplicables;
- rendimiento;
- mantenibilidad;
- oportunidades de refactorización.

REGLAS:

- No confundas la consulta del usuario con el código.
- No analices archivos o componentes que no hayan sido proporcionados.
- Si el fragmento es demasiado pequeño para evaluar algún aspecto, indícalo.
"""

        if skill_type == "project_analysis":
            snapshot = payload

            return f"""
{base}

Analiza el proyecto utilizando exclusivamente la evidencia del siguiente snapshot:

=== SNAPSHOT DEL PROYECTO ===

{snapshot}

Evalúa:

- arquitectura;
- modularidad;
- responsabilidades;
- dependencias;
- organización;
- calidad del código observado;
- deuda técnica observable;
- riesgos;
- oportunidades de mejora.

REGLAS OBLIGATORIAS:

- Basa cada conclusión en información realmente observada.
- No inventes archivos ni componentes.
- No declares que un archivo, clase, módulo o funcionalidad no existe
  únicamente porque no aparece en el snapshot.
- Revisa la sección "ARCHIVOS NO INSPECCIONADOS POR LÍMITE"
  antes de señalar una ausencia.
- Ten en cuenta las marcas de "CONTENIDO TRUNCADO".
- Si algo no pudo verificarse, utiliza expresiones como:
  "no se pudo verificar con el snapshot disponible".
- Distingue claramente entre:
  1. hallazgos confirmados;
  2. limitaciones de la inspección;
  3. recomendaciones.
- No presentes inferencias como hechos.
"""

        if skill_type == "readme":
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

=== INFORMACIÓN VERIFICADA DEL PROYECTO ===

{snapshot}

REGLAS OBLIGATORIAS:

- Usa únicamente información verificable en el contexto y snapshot.
- No inventes funcionalidades.
- No inventes repositorios ni URLs.
- No inventes autores, emails ni datos de contacto.
- No inventes licencias.
- No inventes versiones.
- No inventes una fase o estado del proyecto.
- No afirmes soporte para un proveedor o tecnología
  únicamente porque exista un archivo con su nombre.
- No menciones como funcional una característica cuya implementación
  no pueda verificarse.
- No declares que un archivo no existe simplemente porque no fue inspeccionado.
- No uses placeholders como:
  "tu_usuario",
  "tu_email",
  "example.com"
  o equivalentes.
- Si un dato no está disponible, omítelo.
- Distingue claramente entre funcionalidades actuales verificadas
  y objetivos futuros documentados.
- El resultado debe poder utilizarse directamente como README.md.
"""

        return base

    @staticmethod
    def _format_context(context):
        if context is None:
            return ""

        if not isinstance(context, dict):
            return str(context)

        sections = []

        project = context.get("project")
        obsidian = context.get("obsidian")
        query = context.get("query")
        memory = context.get("memory")

        if project:
            sections.append(
                f"=== PROYECTO ===\n{project}"
            )

        if obsidian:
            sections.append(
                f"=== OBSIDIAN ===\n{obsidian}"
            )

        if query:
            sections.append(
                f"=== CONSULTA ===\n{query}"
            )

        if memory:
            sections.append(
                f"=== MEMORIA ===\n{memory}"
            )

        return "\n\n".join(sections)