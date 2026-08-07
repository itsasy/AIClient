from __future__ import annotations

from collections import defaultdict

from core.project_file import ProjectFile
from core.project_snapshot import ProjectSnapshot


class ProjectIndex:
    """
    Índice rápido sobre ProjectSnapshot.

    Permite consultas sin recorrer
    todos los archivos constantemente.
    """

    def __init__(
        self,
        snapshot: ProjectSnapshot,
    ):

        self.snapshot = snapshot

        self._by_name: dict[str, list[ProjectFile]] = defaultdict(list)

        self._by_extension: dict[str, list[ProjectFile]] = defaultdict(list)

        self._by_directory: dict[str, list[ProjectFile]] = defaultdict(list)

        self._build()

    def _build(self):

        for file in self.snapshot.files:

            self._by_name[file.filename.lower()].append(file)

            self._by_extension[file.extension.lower()].append(file)

            self._by_directory[file.directory.lower()].append(file)

    def search_name(
        self,
        token: str,
    ) -> list[ProjectFile]:

        token = token.lower()

        result = []

        for name, files in self._by_name.items():

            if token in name:

                result.extend(files)

        return result

    def search_extension(
        self,
        extension: str,
    ) -> list[ProjectFile]:

        extension = extension.lower()

        if not extension.startswith("."):
            extension = "." + extension

        return list(
            self._by_extension.get(
                extension,
                [],
            )
        )

    def search_directory(
        self,
        directory: str,
    ) -> list[ProjectFile]:

        directory = directory.lower()

        result = []

        for path, files in self._by_directory.items():

            if directory in path:

                result.extend(files)

        return result
