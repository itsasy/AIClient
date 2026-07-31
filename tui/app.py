#!/usr/bin/env python3
"""
AIClient TUI – Interfaz en terminal con Textual.
Ejecutar: python -m tui.app
"""

import asyncio
import json
from pathlib import Path
from typing import Optional

from textual import on, work
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import (
    Header,
    Footer,
    TextArea,
    Static,
    Label,
    RichLog,
    Input,
    Button,
)
from textual.reactive import reactive
from textual.message import Message
from textual.worker import Worker, WorkerState
from rich.text import Text
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import Config
from core.orchestrator import Orchestrator
from core.engram_memory import EngramMemory
from core.spec_manager import SpecManager
from core.document_ingestor import DocumentIngestor


class ChatLog(RichLog):
    """Widget para mostrar el historial de la conversación."""

    pass


class ContextPanel(Static):
    """Panel lateral que muestra el contexto actual (memoria, proyecto, etc.)."""

    context_content = reactive("", recompose=True)

    def render(self) -> str:
        return f"[bold]📊 Contexto[/bold]\n\n{self.context_content or 'Esperando contexto...'}"


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
    .status-bar {
        dock: bottom;
        height: 1;
        background: $panel;
        color: $text-muted;
        padding: 0 1;
    }
    """

    def __init__(self):
        super().__init__()
        self.orchestrator = Orchestrator()
        self.engram = EngramMemory()
        self.spec_manager = SpecManager()
        self.context_cache = ""

    def compose(self) -> ComposeResult:
        """Construye la interfaz."""
        yield Header()
        with Container(id="main-container"):
            with Horizontal():
                # Panel izquierdo: chat
                with Container(id="chat-panel"):
                    yield ChatLog(id="chat-log", markup=True, wrap=True, highlight=True)
                # Panel derecho: contexto
                with Container(id="context-panel"):
                    yield ContextPanel(id="context-content")
            # Área de entrada
            with Container(id="input-area"):
                yield Input(
                    placeholder="Escribe tu mensaje... (comandos: /help)",
                    id="input-field",
                )
        yield Footer()

    def on_mount(self) -> None:
        """Al iniciar la TUI."""
        self.query_one("#input-field").focus()
        self.log_system("🚀 AIClient TUI iniciado")
        self.log_system("💡 Escribe /help para ver los comandos disponibles")

        # Inicializar el panel de contexto
        panel = self.query_one("#context-content", ContextPanel)
        panel.context_content = "Esperando contexto..."
        self.update_context()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Procesa el mensaje del usuario."""
        input_widget = self.query_one("#input-field")
        message = input_widget.value.strip()
        input_widget.value = ""

        if not message:
            return

        if message.startswith("/"):
            await self.handle_command(message)
            return

        self.log_user(message)
        self.log_system("⏳ Procesando...")

        input_widget.disabled = True
        self.process_query(message)

    @work
    async def process_query(self, message: str) -> None:
        """Procesa la consulta y muestra la respuesta."""
        try:
            response = self.orchestrator.process(message)
            self.log_ai(response)
        except Exception as e:
            self.log_error(f"Error: {str(e)}")
        finally:
            # Reactivar input
            input_widget = self.query_one("#input-field")
            input_widget.disabled = False
            input_widget.focus()
            # Actualizar contexto después de la respuesta
            self.update_context()

    async def handle_command(self, command: str) -> None:
        """Maneja comandos especiales /..."""
        parts = command.split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        if cmd == "/help":
            self.log_system("""
            📚 Comandos disponibles:
            /help          - Muestra esta ayuda
            /memory <text> - Busca en la memoria persistente
            /specs         - Lista todas las especificaciones
            /status        - Muestra estadísticas del sistema
            /ingest <file> - Ingiere un documento (ej. /ingest documento.pdf)
            /clear         - Limpia el historial de chat
            /exit          - Sale de la TUI
            """)
        elif cmd == "/memory":
            if not args:
                self.log_system("⚠️ Uso: /memory <texto a buscar>")
                return
            results = self.engram.recall(args, limit=5)
            if results:
                for r in results:
                    content = r.get("content", "")[:200]
                    self.log_system(f"🧠 {content}...")
            else:
                self.log_system("No se encontraron memorias.")
        elif cmd == "/specs":
            specs = self.spec_manager.list_specs()
            if specs:
                for s in specs:
                    self.log_system(
                        f"📋 {s.get('name')} – {s.get('status')} ({s.get('created_at', '')[:16]})"
                    )
            else:
                self.log_system("No hay especificaciones guardadas.")
        elif cmd == "/status":
            stats = self.engram.stats()
            if stats:
                self.log_system(f"📊 Memorias: {stats.get('total_memories', 0)}")
                self.log_system(f"📦 Tamaño DB: {stats.get('db_size_mb', 0):.2f} MB")
                self.log_system(f"⚙️ Proveedor código: {Config.CODE_PROVIDER}")
                self.log_system(f"⚙️ Proveedor arquitectura: {Config.ARCHITECTURE_PROVIDER}")
            else:
                self.log_system("No se pudieron obtener estadísticas.")
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
                self.log_system(f"✅ Documento ingerido: {filepath.name}")
            else:
                self.log_system(f"❌ Error al ingerir: {filepath.name}")
        elif cmd == "/clear":
            chat_log = self.query_one("#chat-log")
            chat_log.clear()
            self.log_system("🧹 Historial limpiado")
        elif cmd == "/exit":
            self.exit()
        else:
            self.log_system(f"⚠️ Comando desconocido: {cmd}. Escribe /help para ayuda.")

    def log_user(self, message: str) -> None:
        """Añade un mensaje del usuario al chat."""
        chat_log = self.query_one("#chat-log")
        chat_log.write(Text(f"🧑 Tú: {message}", style="bold cyan"))

    def log_ai(self, message: str) -> None:
        """Añade una respuesta del AI al chat."""
        chat_log = self.query_one("#chat-log")
        chat_log.write(Text(f"🤖 AI:", style="bold green"))
        chat_log.write(Text(message, style="white"))

    def log_system(self, message: str) -> None:
        """Añade un mensaje del sistema al chat."""
        chat_log = self.query_one("#chat-log")
        chat_log.write(Text(f"⚙️ {message}", style="dim italic"))

    def log_error(self, message: str) -> None:
        """Añade un mensaje de error al chat."""
        chat_log = self.query_one("#chat-log")
        chat_log.write(Text(f"❌ {message}", style="bold red"))

    def update_context(self) -> None:
        """Actualiza el panel de contexto con información relevante."""
        context_panel = self.query_one("#context-content", ContextPanel)
        try:
            # Obtener contexto actual (memoria reciente, proyecto, etc.)
            # Usamos una consulta genérica para obtener algunas memorias
            memories = self.engram.recall("proyecto contexto", limit=3)
            context_lines = []
            if memories:
                context_lines.append("[bold]🧠 Memorias recientes:[/bold]")
                for m in memories[:3]:
                    content = m.get("content", "")[:100]
                    if content:
                        context_lines.append(f"  • {content}...")
            else:
                context_lines.append("[dim]No hay memorias recientes[/dim]")

            # Añadir estadísticas básicas
            stats = self.engram.stats()
            if stats:
                context_lines.append(f"\n[bold]📊 Estadísticas:[/bold]")
                context_lines.append(f"  • Total memorias: {stats.get('total_memories', 0)}")

            # Añadir configuración activa
            context_lines.append(f"\n[bold]⚙️ Configuración:[/bold]")
            context_lines.append(f"  • Proveedor código: {Config.CODE_PROVIDER}")
            context_lines.append(f"  • Proveedor arquitectura: {Config.ARCHITECTURE_PROVIDER}")

            context_panel.context_content = "\n".join(context_lines)

        except Exception as e:
            context_panel.context_content = f"Error cargando contexto: {e}"

    # ============================================================
    # ATALAJOS DE TECLADO
    # ============================================================

    def on_key(self, event) -> None:
        """Maneja atajos de teclado globales."""
        if event.key == "ctrl+c":
            self.exit()
        elif event.key == "ctrl+l":
            # Limpiar chat
            chat_log = self.query_one("#chat-log")
            chat_log.clear()
            self.log_system("🧹 Historial limpiado")
        elif event.key == "tab":
            # Cambiar foco entre input y contexto (o simplemente mantener input)
            input_widget = self.query_one("#input-field")
            input_widget.focus()


def main():
    """Punto de entrada para la TUI."""
    # Validar configuración
    Config.validate()
    # Ejecutar la app
    app = TUIApp()
    app.run()


if __name__ == "__main__":
    main()
