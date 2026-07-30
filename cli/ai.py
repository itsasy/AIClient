#!/usr/bin/env python3
# cli/ai.py – Punto de entrada principal (opciones estilo --memory, --status)

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from core.config import Config
from core.orchestrator import Orchestrator
from core.engram_memory import EngramMemory
from core.spec_manager import SpecManager
from core.document_ingestor import DocumentIngestor

# Intentar importar rich para salida mejorada
try:
    from rich.console import Console
    from rich.table import Table

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

console = Console() if RICH_AVAILABLE else None


def main():
    Config.validate()

    parser = argparse.ArgumentParser(
        description="AIClient – Asistente de Desarrollo Inteligente",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  ai "crea una función en Python"   # Consulta directa
  ai --chat                         # Modo chat interactivo
  ai --tui                          # Interfaz TUI
  ai --memory "color favorito"      # Buscar en memoria
  ai --status                       # Estadísticas del sistema
  ai --specs                        # Listar especificaciones
  ai --ingest documento.pdf         # Ingerir documento
  ai --forget <id>                  # Eliminar memoria
        """,
    )

    # Opciones de control
    parser.add_argument("--chat", action="store_true", help="Modo chat interactivo")
    parser.add_argument("--tui", action="store_true", help="Modo TUI (interfaz en terminal)")

    # Opciones de comandos
    parser.add_argument(
        "--memory", nargs="+", metavar="texto", help="Buscar en memoria persistente"
    )
    parser.add_argument("--limit", type=int, default=5, help="Máx. resultados para --memory")
    parser.add_argument("--status", action="store_true", help="Mostrar estadísticas del sistema")
    parser.add_argument("--specs", action="store_true", help="Listar especificaciones guardadas")
    parser.add_argument("--list-specs", action="store_true", help="Alias de --specs")
    parser.add_argument("--ingest", metavar="archivo", help="Ingerir un documento")
    parser.add_argument("--tags", default="", help="Etiquetas para --ingest (separadas por coma)")
    parser.add_argument("--forget", metavar="id", help="Eliminar una memoria por ID")

    # Consulta directa (todo lo que no sea opción)
    parser.add_argument("query", nargs="*", help="Tu instrucción")

    args = parser.parse_args()

    # ================================================================
    # 0. TUI
    # ================================================================
    if args.tui:
        try:
            from tui.app import main as tui_main

            tui_main()
        except ImportError as e:
            print(
                f"❌ Error: no se pudo cargar la TUI. Instala textual: pip install textual\nError: {e}"
            )
        return

    # ================================================================
    # 1. COMANDOS CON OPCIONES
    # ================================================================

    # --memory
    if args.memory is not None:
        eng = EngramMemory()
        query = " ".join(args.memory)
        results = eng.recall(query, limit=args.limit)

        if not results:
            if RICH_AVAILABLE:
                console.print("[yellow]No se encontraron memorias.[/yellow]")
            else:
                print("No se encontraron memorias.")
            return

        if RICH_AVAILABLE:
            table = Table(title="🧠 Memoria recuperada")
            table.add_column("ID", style="dim")
            table.add_column("Contenido", style="white")
            table.add_column("Score", justify="right")
            for r in results:
                content = r.get("content", "")[:100]
                if len(r.get("content", "")) > 100:
                    content += "..."
                table.add_row(str(r.get("id", "N/A")), content, str(r.get("score", 0)))
            console.print(table)
        else:
            for r in results:
                content = r.get("content", "")[:100]
                if len(r.get("content", "")) > 100:
                    content += "..."
                print(f"ID: {r.get('id', 'N/A')} | {content} | Score: {r.get('score', 0)}")
        return

    # --status
    if args.status:
        eng = EngramMemory()
        stats = eng.stats()

        if RICH_AVAILABLE:
            console.print("[bold]📊 Estadísticas del sistema[/bold]")
            if stats:
                console.print(f"• Memorias totales: {stats.get('total_memories', 0)}")
                console.print(f"• Última memoria: {stats.get('last_created', 'N/A')}")
                console.print(f"• Tamaño de la base de datos: {stats.get('db_size_mb', 0):.2f} MB")
            else:
                console.print("[yellow]No se pudieron obtener estadísticas.[/yellow]")

            console.print("\n[bold]⚙️ Configuración activa:[/bold]")
            console.print(f"• Proveedor de código: {Config.CODE_PROVIDER}")
            console.print(f"• Proveedor de arquitectura: {Config.ARCHITECTURE_PROVIDER}")
            console.print(
                f"• Proveedor rápido: {getattr(Config, 'FAST_PROVIDER', 'No configurado')}"
            )
        else:
            print("📊 Estadísticas del sistema")
            if stats:
                print(f"• Memorias totales: {stats.get('total_memories', 0)}")
                print(f"• Última memoria: {stats.get('last_created', 'N/A')}")
                print(f"• Tamaño DB: {stats.get('db_size_mb', 0):.2f} MB")
            else:
                print("No se pudieron obtener estadísticas.")
            print("\n⚙️ Configuración activa:")
            print(f"• Proveedor de código: {Config.CODE_PROVIDER}")
            print(f"• Proveedor de arquitectura: {Config.ARCHITECTURE_PROVIDER}")
            print(f"• Proveedor rápido: {getattr(Config, 'FAST_PROVIDER', 'No configurado')}")
        return

    # --specs / --list-specs
    if args.specs or args.list_specs:
        spec_mgr = SpecManager()
        specs = spec_mgr.list_specs()

        if not specs:
            if RICH_AVAILABLE:
                console.print("[yellow]No hay especificaciones guardadas.[/yellow]")
            else:
                print("No hay especificaciones guardadas.")
            return

        if RICH_AVAILABLE:
            table = Table(title="📋 Especificaciones (Specs)")
            table.add_column("Nombre", style="cyan")
            table.add_column("Descripción", style="white")
            table.add_column("Estado", style="green")
            table.add_column("Creada", style="dim")
            for s in specs:
                desc = s.get("description", "")[:50]
                if len(s.get("description", "")) > 50:
                    desc += "..."
                table.add_row(
                    s.get("name", "N/A"),
                    desc,
                    s.get("status", "draft"),
                    s.get("created_at", "")[:16],
                )
            console.print(table)
        else:
            for s in specs:
                print(f"📋 {s.get('name')} – {s.get('status')} ({s.get('created_at', '')[:16]})")
        return

    # --ingest
    if args.ingest:
        filepath = Path(args.ingest).expanduser()
        if not filepath.exists():
            if RICH_AVAILABLE:
                console.print(f"[red]❌ Archivo no encontrado: {filepath}[/red]")
            else:
                print(f"❌ Archivo no encontrado: {filepath}")
            return

        ingestor = DocumentIngestor()
        tags = [t.strip() for t in args.tags.split(",") if t.strip()] if args.tags else []
        success = ingestor.ingest_file(filepath, tags=tags)

        if success:
            if RICH_AVAILABLE:
                console.print(f"[green]✅ Documento ingerido: {filepath.name}[/green]")
            else:
                print(f"✅ Documento ingerido: {filepath.name}")
        else:
            if RICH_AVAILABLE:
                console.print(f"[red]❌ Error al ingerir: {filepath.name}[/red]")
            else:
                print(f"❌ Error al ingerir: {filepath.name}")
        return

    # --forget
    if args.forget:
        eng = EngramMemory()
        success = eng.forget(args.forget)
        if success:
            if RICH_AVAILABLE:
                console.print(f"[green]✅ Memoria {args.forget} eliminada.[/green]")
            else:
                print(f"✅ Memoria {args.forget} eliminada.")
        else:
            if RICH_AVAILABLE:
                console.print(f"[red]❌ No se pudo eliminar la memoria {args.forget}.[/red]")
            else:
                print(f"❌ No se pudo eliminar la memoria {args.forget}.")
        return

    # ================================================================
    # 2. CONSULTA DIRECTA (si no se usó ninguna opción)
    # ================================================================
    query = " ".join(args.query).strip()

    if not query and not args.chat:
        print("🤖 Uso: ai 'tu instrucción'")
        print("    ai --chat")
        print("    ai --tui")
        print("    ai --memory 'término'")
        print("    ai --status")
        print("    ai --specs")
        print("    ai --ingest archivo.pdf")
        print("    ai --forget <id>")
        return

    orchestrator = Orchestrator()

    if args.chat:
        print("🤖 Modo Chat (escribe 'exit' para salir)\n")
        while True:
            try:
                q = input("Tú: ")
                if q.lower() in ["exit", "salir", "quit"]:
                    break
                print(f"\nAI: {orchestrator.process(q)}\n")
            except KeyboardInterrupt:
                break
    else:
        response = orchestrator.process(query)
        if RICH_AVAILABLE:
            console.print(f"\n[bold cyan]🤖[/bold cyan] {response}\n")
        else:
            print(f"\n🤖 {response}\n")


if __name__ == "__main__":
    main()
