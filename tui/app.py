#!/usr/bin/env python3

"""
AIClient TUI – Interfaz en terminal con Textual.

Ejecutar:

    python -m tui.app
"""

from pathlib import Path
import sys

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal
from textual.widgets import (
    Header,
    Footer,
    Input,
    RichLog,
    Static,
)
from textual.reactive import reactive
from textual.worker import work

from rich.text import Text

sys.path.insert(
    0,
    str(Path(__file__).resolve().parent.parent),
)


from container import build_container
from core.config import Config
from core.engram_memory import EngramMemory
from core.spec_manager import SpecManager
from core.document_ingestor import DocumentIngestor

# ================================================================
# Chat log
# ================================================================


class ChatLog(RichLog):
    """Widget para mostrar el historial de la conversación."""

    pass


# ================================================================
# Context panel
# ================================================================


class ContextPanel(Static):
    """Panel lateral que muestra el contexto actual."""

    context_content = reactive(
        "",
        recompose=True,
    )

    def render(self) -> str:
        return "[bold]📊 Contexto[/bold]\n\n" f"{self.context_content or 'Esperando contexto...'}"


# ================================================================
# TUI
# ================================================================


class TUIApp(App):
    """Aplicación principal de la TUI."""

    CSS = """
    Screen {
        background: $surface;
    }

    #main-container {
        height: 100%;
    }

    #chat-panel {
        width: 60%;
        height: 100%;
        border-right: solid $primary;
    }

    #context-panel {
        width: 40%;
        height: 100%;
        padding: 1;
    }

    #input-area {
        height: 3;
        dock: bottom;
        padding: 0 1;
    }

    #chat-log {
        height: 100%;
        padding: 1;
    }

    #context-content {
        height: 100%;
        padding: 1;
        overflow-y: scroll;
    }

    .input-field {
        width: 100%;
        margin: 0;
    }
    """

    def __init__(self):
        super().__init__()

        # ========================================================
        # Composition root
        # ========================================================

        self.container = build_container()

        self.engine = self.container.get_engine()

        self.engram = EngramMemory()
        self.spec_manager = SpecManager()
        self.context_cache = ""

    # ============================================================
    # Compose
    # ============================================================

    def compose(self) -> ComposeResult:
        yield Header()

        with Container(id="main-container"):
            with Horizontal():

                # Panel izquierdo
                with Container(id="chat-panel"):
                    yield ChatLog(
                        id="chat-log",
                        markup=True,
                        wrap=True,
                        highlight=True,
                    )

                # Panel derecho
                with Container(id="context-panel"):
                    yield ContextPanel(
                        id="context-content",
                    )

            with Container(id="input-area"):
                yield Input(
                    placeholder=("Escribe tu mensaje... " "(comandos: /help)"),
                    id="input-field",
                )

        yield Footer()

    # ============================================================
    # Mount
    # ============================================================

    def on_mount(self) -> None:
        self.query_one("#input-field").focus()

        self.log_system("🚀 AIClient TUI iniciado")

        self.log_system("💡 Escribe /help para ver " "los comandos disponibles")

        panel = self.query_one(
            "#context-content",
            ContextPanel,
        )

        panel.context_content = "Esperando contexto..."

        self.update_context()

    # ============================================================
    # Input
    # ============================================================

    async def on_input_submitted(
        self,
        event: Input.Submitted,
    ) -> None:

        input_widget = self.query_one("#input-field")

        message = input_widget.value.strip()

        input_widget.value = ""

        if not message:
            return

        local_cmds = {
            "/help",
            "/memory",
            "/specs",
            "/status",
            "/ingest",
            "/clear",
            "/exit",
        }

        first = message.split(maxsplit=1)[0].lower()

        if first in local_cmds:
            await self.handle_command(message)
            return

        self.log_user(message)

        self.log_system("⏳ Procesando...")

        input_widget.disabled = True

        self.process_query(message)

    # ============================================================
    # Query
    # ============================================================

    @work
    async def process_query(
        self,
        message: str,
    ) -> None:

        try:
            result = self.engine.execute_from_input(message)

            if result.is_success:
                self.log_ai(str(result.result) if result.result is not None else "OK")

            else:
                self.log_error(f"Error: {result.error}")

        except Exception as e:
            self.log_error(f"Error: {str(e)}")

        finally:
            input_widget = self.query_one("#input-field")

            input_widget.disabled = False
            input_widget.focus()

            self.update_context()

    # ============================================================
    # Local commands
    # ============================================================

    async def handle_command(
        self,
        command: str,
    ) -> None:

        parts = command.split(maxsplit=1)

        cmd = parts[0].lower()

        args = parts[1] if len(parts) > 1 else ""

        # --------------------------------------------------------
        # Help
        # --------------------------------------------------------

        if cmd == "/help":
            self.log_system("""
📚 Comandos disponibles:

/help          - Muestra esta ayuda
/memory <text> - Busca en la memoria persistente
/specs         - Lista todas las especificaciones
/status        - Muestra estadísticas del sistema
/ingest <file> - Ingiere un documento
/clear         - Limpia el historial de chat
/exit          - Sale de la TUI
""")

        # --------------------------------------------------------
        # Memory
        # --------------------------------------------------------

        elif cmd == "/memory":

            if not args:
                self.log_system("⚠️ Uso: /memory <texto a buscar>")
                return

            results = self.engram.recall(
                args,
                limit=5,
            )

            if results:
                for result in results:
                    content = result.get(
                        "content",
                        "",
                    )[:200]

                    self.log_system(f"🧠 {content}...")

            else:
                self.log_system("No se encontraron memorias.")

        # --------------------------------------------------------
        # Specs
        # --------------------------------------------------------

        elif cmd == "/specs":

            specs = self.spec_manager.list_specs()

            if specs:
                for spec in specs:
                    self.log_system(
                        f"📋 {spec.get('name')} – "
                        f"{spec.get('status')} "
                        f"({spec.get('created_at', '')[:16]})"
                    )

            else:
                self.log_system("No hay especificaciones guardadas.")

        # --------------------------------------------------------
        # Status
        # --------------------------------------------------------

        elif cmd == "/status":

            stats = self.engram.stats()

            if stats:
                self.log_system(f"📊 Memorias: " f"{stats.get('total_memories', 0)}")

                self.log_system(f"📦 Tamaño DB: " f"{stats.get('db_size_mb', 0):.2f} MB")

                self.log_system(f"⚙️ Proveedor código: " f"{Config.CODE_PROVIDER}")

                self.log_system(f"⚙️ Proveedor arquitectura: " f"{Config.ARCHITECTURE_PROVIDER}")

            else:
                self.log_system("No se pudieron obtener estadísticas.")

        # --------------------------------------------------------
        # Ingest
        # --------------------------------------------------------

        elif cmd == "/ingest":

            if not args:
                self.log_system("⚠️ Uso: /ingest <ruta_del_archivo>")
                return

            filepath = Path(args).expanduser()

            if not filepath.exists():
                self.log_system(f"❌ Archivo no encontrado: {filepath}")
                return

            ingestor = DocumentIngestor()

            success = ingestor.ingest_file(filepath)

            if success:
                self.log_system(f"✅ Documento ingerido: " f"{filepath.name}")

            else:
                self.log_system(f"❌ Error al ingerir: " f"{filepath.name}")

        # --------------------------------------------------------
        # Clear
        # --------------------------------------------------------

        elif cmd == "/clear":

            chat_log = self.query_one("#chat-log")

            chat_log.clear()

            self.log_system("🧹 Historial limpiado")

        # --------------------------------------------------------
        # Exit
        # --------------------------------------------------------

        elif cmd == "/exit":
            self.exit()

        else:
            self.log_system(f"⚠️ Comando desconocido: {cmd}. " "Escribe /help para ayuda.")

    # ============================================================
    # Logging helpers
    # ============================================================

    def log_user(
        self,
        message: str,
    ) -> None:

        chat_log = self.query_one("#chat-log")

        chat_log.write(
            Text(
                f"🧑 Tú: {message}",
                style="bold cyan",
            )
        )

    def log_ai(
        self,
        message: str,
    ) -> None:

        chat_log = self.query_one("#chat-log")

        chat_log.write(
            Text(
                "🤖 AI:",
                style="bold green",
            )
        )

        chat_log.write(
            Text(
                message,
                style="white",
            )
        )

    def log_system(
        self,
        message: str,
    ) -> None:

        chat_log = self.query_one("#chat-log")

        chat_log.write(
            Text(
                f"⚙️ {message}",
                style="dim italic",
            )
        )

    def log_error(
        self,
        message: str,
    ) -> None:

        chat_log = self.query_one("#chat-log")

        chat_log.write(
            Text(
                f"❌ {message}",
                style="bold red",
            )
        )

    # ============================================================
    # Context
    # ============================================================

    def update_context(self) -> None:

        context_panel = self.query_one(
            "#context-content",
            ContextPanel,
        )

        try:
            memories = self.engram.recall(
                "proyecto contexto",
                limit=3,
            )

            context_lines = []

            if memories:
                context_lines.append("[bold]🧠 Memorias recientes:[/bold]")

                for memory in memories[:3]:
                    content = memory.get(
                        "content",
                        "",
                    )[:100]

                    if content:
                        context_lines.append(f"  • {content}...")

            else:
                context_lines.append("[dim]No hay memorias recientes[/dim]")

            stats = self.engram.stats()

            if stats:
                context_lines.append("\n[bold]📊 Estadísticas:[/bold]")

                context_lines.append("  • Total memorias: " f"{stats.get('total_memories', 0)}")

            context_lines.append("\n[bold]⚙️ Configuración:[/bold]")

            context_lines.append("  • Proveedor código: " f"{Config.CODE_PROVIDER}")

            context_lines.append("  • Proveedor arquitectura: " f"{Config.ARCHITECTURE_PROVIDER}")

            context_panel.context_content = "\n".join(context_lines)

        except Exception as e:
            context_panel.context_content = f"Error cargando contexto: {e}"

    # ============================================================
    # Keyboard shortcuts
    # ============================================================

    def on_key(self, event) -> None:

        if event.key == "ctrl+c":
            self.exit()

        elif event.key == "ctrl+l":

            chat_log = self.query_one("#chat-log")

            chat_log.clear()

            self.log_system("🧹 Historial limpiado")

        elif event.key == "tab":

            input_widget = self.query_one("#input-field")

            input_widget.focus()


# ================================================================
# Entry point
# ================================================================


def main():
    Config.validate()

    app = TUIApp()
    app.run()


if __name__ == "__main__":
    main()
