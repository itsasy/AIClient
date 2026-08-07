#!/usr/bin/env python3
# cli/ai.py – Punto de entrada principal (opciones estilo --memory, --status)

import argparse
import sys
from pathlib import Path
import logging

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from core.config import Config
from core.engram_memory import EngramMemory
from core.spec_manager import SpecManager
from core.document_ingestor import DocumentIngestor
from runtime.execution_engine import ExecutionEngine

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


try:
    from rich.console import Console
    from rich.table import Table

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

console = Console() if RICH_AVAILABLE else None


def format_output(result_data):
    """
    Convierte el resultado de una ejecución exitosa en texto legible.
    """
    if result_data is None:
        return "✅ Ejecución completada (sin salida)."

    if isinstance(result_data, str):
        return result_data

    if isinstance(result_data, dict):
        # Si tiene "snapshot" (ProjectAnalyzerSkill)
        if "snapshot" in result_data:
            return result_data["snapshot"]
        # Si tiene "result" con snapshot dentro
        if "result" in result_data and isinstance(result_data["result"], dict):
            if "snapshot" in result_data["result"]:
                return result_data["result"]["snapshot"]
        # Si tiene un mensaje simple
        if "message" in result_data:
            return result_data["message"]
        if "output" in result_data:
            return str(result_data["output"])
        if "result" in result_data:
            return format_output(result_data["result"])
        return str(result_data)

    if isinstance(result_data, list):
        if len(result_data) == 1:
            return format_output(result_data[0])
        parts = []
        for i, item in enumerate(result_data, 1):
            formatted = format_output(item)
            if formatted:
                parts.append(f"📌 Paso {i}:\n{formatted}")
        if parts:
            return "\n\n".join(parts)
        return str(result_data)

    return str(result_data)


def extract_error(result):
    """
    Extrae el mensaje de error de un ExecutionResult no exitoso.
    """
    # 1. Si hay un error general en el ExecutionResult
    if result.error:
        return result.error

    # 2. Función recursiva para buscar error en cualquier estructura
    def find_error(data):
        if isinstance(data, dict):
            # Buscar "error" directamente
            if "error" in data and data["error"]:
                return data["error"]
            # Buscar "ok" False
            if "ok" in data and not data.get("ok"):
                return data.get("error", "Error desconocido")
            # Buscar dentro de "result"
            if "result" in data:
                return find_error(data["result"])
        elif isinstance(data, list):
            for item in data:
                error = find_error(item)
                if error:
                    return error
        elif hasattr(data, "is_failure") and data.is_failure:
            if hasattr(data, "error") and data.error:
                return data.error
        return None

    # 3. Buscar en result.result
    error_msg = find_error(result.result)
    if error_msg:
        return error_msg

    # 4. Si no se pudo extraer, mostrar el resultado para depuración
    logger.debug(f"No se pudo extraer error. result.result: {result.result}")
    return "Error desconocido en la ejecución."


def main():
    Config.validate()

    logger.info("🚀 AIClient iniciado con logs INFO activados")

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

    parser.add_argument("--chat", action="store_true", help="Modo chat interactivo")
    parser.add_argument("--tui", action="store_true", help="Modo TUI (interfaz en terminal)")

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

    parser.add_argument("query", nargs="*", help="Tu instrucción")

    args = parser.parse_args()

    # =============================================================
    # 0. TUI
    # =============================================================
    if args.tui:
        try:
            from tui.app import main as tui_main

            tui_main()
        except ImportError as e:
            print(
                f"❌ Error: no se pudo cargar la TUI. Instala textual: pip install textual\nError: {e}"
            )
        return

    # =============================================================
    # 1. COMANDOS CON OPCIONES (se ejecutan ANTES de la consulta directa)
    # =============================================================

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

    # =============================================================
    # 2. CONSULTA DIRECTA (usando ExecutionEngine)
    # =============================================================
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

    # ✅ Usar ExecutionEngine
    engine = ExecutionEngine()

    if args.chat:
        print("🤖 Modo Chat (escribe 'exit' para salir)\n")
        while True:
            try:
                q = input("Tú: ")
                if q.lower() in ["exit", "salir", "quit"]:
                    break

                result = engine.execute_from_input(q)
                if result.is_success:
                    output = format_output(result.result)
                    print(f"\nAI: {output}\n")
                else:
                    error = extract_error(result)
                    print(f"\n❌ Error: {error}\n")
            except KeyboardInterrupt:
                break
    else:
        result = engine.execute_from_input(query)

        if result.is_success:
            output = format_output(result.result)
            if RICH_AVAILABLE:
                console.print(f"\n[bold cyan]🤖[/bold cyan] {output}\n")
            else:
                print(f"\n🤖 {output}\n")
        else:
            error = extract_error(result)
            if RICH_AVAILABLE:
                console.print(f"\n[bold red]❌[/bold red] {error}\n")
            else:
                print(f"\n❌ {error}\n")


if __name__ == "__main__":
    main()
