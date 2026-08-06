from __future__ import annotations

from core.tools.registry import ToolRegistry

from core.tools.shell import ShellTool
from core.tools.docker import DockerTool
from core.tools.file import FileTool


class ToolManager:

    def __init__(
        self,
        registry: ToolRegistry | None = None,
        auto_load: bool = True,
    ):

        self.registry = registry or ToolRegistry()

        if auto_load:
            self.load_defaults()

    def load_defaults(
        self,
    ):

        for tool in (
            ShellTool,
            DockerTool,
            FileTool,
        ):

            self.registry.register(
                tool.name,
                tool,
            )

    def get(
        self,
        tool_name: str,
    ):

        return self.registry.get(tool_name)

    def execute(
        self,
        tool_name: str,
        *args,
        **kwargs,
    ):

        tool = self.get(tool_name)

        if tool is None:

            return {
                "ok": False,
                "result": None,
                "error": (f"Tool no encontrada: {tool_name}"),
            }

        return tool.execute(
            *args,
            **kwargs,
        )

    def has(
        self,
        tool_name: str,
    ) -> bool:

        return self.registry.has(tool_name)

    def list(
        self,
    ) -> list[str]:

        return self.registry.list()

    def metadata(
        self,
    ) -> list[dict]:

        return self.registry.metadata()
