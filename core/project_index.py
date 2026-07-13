from __future__ import annotations

from collections import defaultdict

from core.project_file import ProjectFile
from core.project_snapshot import ProjectSnapshot


class ProjectIndex:
    """
    Índice ligero del snapshot.

    Evita recorrer todos los archivos en cada consulta.
    """

    def __init__(
        self,
        snapshot: ProjectSnapshot,
    ):
        self.snapshot = snapshot

        self._by_name = defaultdict(list)
        self._by_extension = defaultdict(list)
        self._by_directory = defaultdict(list)

        self._build()

    def _build(self):

        for file in self.snapshot.files:

            self._by_name[file.filename.lower()].append(file)

            self._by_extension[file.extension].append(file)

            self._by_directory[file.directory.lower()].append(file)

    def search_name(
        self,
        token: str,
    ):

        token = token.lower()

        result = []

        for name, files in self._by_name.items():

            if token in name:
                result.extend(files)

        return result

    def search_extension(
        self,
        extension: str,
    ):
        return list(
            self._by_extension.get(
                extension.lower(),
                [],
            )
        )

    def search_directory(
        self,
        directory: str,
    ):
        return list(
            self._by_directory.get(
                directory.lower(),
                [],
            )
        )