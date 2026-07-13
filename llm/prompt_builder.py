from textwrap import dedent


class PromptBuilder:
    @staticmethod
    def build(
        task: str,
        context,
        skill_name=None,
        skill_result=None,
    ) -> str:
        context_text = PromptBuilder._format_context(context)

        base = dedent(
            f"""
            Eres un asistente senior de desarrollo de software.

            CONSULTA DEL USUARIO:
            {task}

            CONTEXTO DISPONIBLE:
            {context_text}
            """
        ).strip()

        if not skill_name or not skill_result:
            return base

        skill_type = skill_result.get("type")
        payload = skill_result.get("payload", {})

        if skill_type == "code_generation":
            return dedent(
                f"""
                {base}

                TAREA:
                Genera una solución para:

                {payload.get("task", task)}

                Lenguaje preferido:
                {payload.get("language", "python")}

                Entrega una solución concreta, moderna y lista para usar.
                No inventes requisitos que no hayan sido proporcionados.
                """
            ).strip()

        if skill_type == "code_analysis":
            return dedent(
                f"""
                {base}

                TAREA:
                Analiza exclusivamente el siguiente código:

                {payload.get("code", "")}

                Evalúa:

                - bugs
                - seguridad
                - buenas prácticas
                - SOLID
                - rendimiento
                - oportunidades de refactorización

                No confundas la consulta del usuario con código fuente.
                """
            ).strip()

        if skill_type == "project_analysis":
            return dedent(
                f"""
                {base}

                TAREA:
                Analiza el proyecto actual usando el siguiente snapshot:

                {payload}

                Evalúa:

                - arquitectura
                - estructura
                - modularidad
                - responsabilidades
                - dependencias
                - deuda técnica
                - problemas potenciales
                - oportunidades de mejora

                No solicites al usuario que copie archivos que ya aparecen en el snapshot.
                No inventes contenido de archivos que no haya sido inspeccionado.
                Distingue claramente entre hechos observados y recomendaciones.
                """
            ).strip()

        if skill_type == "readme":
            snapshot = payload.get("snapshot", "")
            requested_name = payload.get("request", "")
            description = payload.get("description", "")

            return dedent(
                f"""
                {base}

                Genera un README profesional para el proyecto solicitado.

                Solicitud:
                {requested_name}

                Descripción proporcionada:
                {description or "No proporcionada."}

                Información verificada del proyecto:
                {snapshot}

                REGLAS OBLIGATORIAS:

                - Usa únicamente información verificable en el contexto y snapshot.
                - No inventes funcionalidades.
                - No inventes repositorios ni URLs.
                - No inventes autores, emails ni datos de contacto.
                - No inventes licencias.
                - No inventes una fase o estado del proyecto.
                - No menciones archivos que no aparezcan en la información disponible.
                - Distingue claramente entre funcionalidades actuales y objetivos futuros.
                - Si un dato no está disponible, simplemente omítelo.
                - No uses placeholders como "tu_usuario", "tu_email" o "example.com".
                - El resultado debe poder utilizarse directamente como README.md.
                """
            ).strip()
