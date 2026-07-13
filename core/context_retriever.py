from __future__ import annotations

from core.project_snapshot import ProjectSnapshot


class ContextRetriever:
    """
    Selecciona únicamente el contexto necesario para el PromptBuilder.

    Actualmente trabaja sobre ProjectSnapshot.
    En futuras iteraciones utilizará ProjectIndex y búsqueda semántica.
    """

    DEFAULT_FILES = 5

    @classmethod
    def retrieve(
        cls,
        context: dict | None,
    ) -> dict:

        if not context:
            return {}

        result = dict(context)

        project = context.get("project")

        if isinstance(project, ProjectSnapshot):
            result["project"] = cls._build_project_context(
                project,
                query=context.get("query", ""),
            )

        return result

    @classmethod
    def _build_project_context(
        cls,
        snapshot: ProjectSnapshot,
        query: str,
    ) -> str:

        query = (query or "").lower()

        files = cls._select_files(
            snapshot=snapshot,
            query=query,
        )

        lines = [
            f"Proyecto: {snapshot.root}",
            "",
            f"Archivos analizados: {len(files)} de {snapshot.file_count}",
            "",
        ]

        for file in files:

            lines.append(f"===== {file.path} =====")
            lines.append(file.content)
            lines.append("")

        return "\n".join(lines)

    @classmethod
    def _select_files(
        cls,
        snapshot: ProjectSnapshot,
        query: str,
    ):
        """
        Primera estrategia de selección.

        1) Buscar coincidencias por nombre.
        2) Si no hay coincidencias, devolver
           los primeros archivos.
        """

        words = [
            word
            for word in query.split()
            if len(word) >= 3
        ]

        selected = []

        for word in words:

            selected.extend(
                snapshot.find_by_name(word)
            )

        unique = []

        seen = set()

        for file in selected:

            if file.path in seen:
                continue

            unique.append(file)

            seen.add(file.path)

        if unique:
            return unique[: cls.DEFAULT_FILES]

        return snapshot.files[: cls.DEFAULT_FILES]