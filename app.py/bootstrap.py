from __future__ import annotations

from container import build_container


def create_application():
    """
    Construye la aplicación completa.

    El container se encarga de crear:

    - ContextManager
    - AgentRegistry
    - SkillRegistry
    - AgentRuntime
    - SkillRuntime
    - ExecutionEngine
    - Pipeline

    Este módulo solo expone la instancia lista para usar.
    """

    container = build_container()

    return container
