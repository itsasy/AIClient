#!/usr/bin/env python3
# cli/ai.py – Punto de entrada principal con subcomandos

import argparse
import sys
import json
from pathlib import Path
from core.config import Config
from core.orchestrator import Orchestrator
from core.engram_memory import EngramMemory
from core.spec_manager import SpecManager
from core.document_ingestor import DocumentIngestor
from rich.console import Console
from rich.table import Table
from rich import print as rprint

console = Console()


def main():
    Config.validate()

    parser = argparse.ArgumentParser(
        description="AIClient – Asistente de Desarrollo Inteligente"
    )
    subparsers = parser.add_subparsers(dest="command", help="Comandos disponibles")

    # Comando para consulta directa (por defecto, si no se usa subcomando)
    parser.add_argument("query", nargs="*", help="Tu instrucción")

    # Comando --chat (modo interactivo)
    parser.add_argument("--chat", action="store_true", help="Modo chat interactivo")

    # Subcomando --memory
    memory_parser = subparsers.add_parser(
        "memory", help="Buscar en la memoria persistente (Engram)"
    )
    memory_parser.add_argument("query", nargs="+", help="Texto a buscar")
    memory_parser.add_argument(
        "--limit", type=int, default=5, help="Máximo de resultados"
    )

    # Subcomando --status
    status_parser = subparsers.add_parser(
        "status", help="Mostrar estado del sistema y estadísticas"
    )

    # Subcomando --specs (listar specs disponibles)
    specs_parser = subparsers.add_parser(
        "specs", help="Listar especificaciones guardadas"
    )

    # Subcomando --list-specs (alias de specs)
    list_specs_parser = subparsers.add_parser("list-specs", help="Alias de specs")

    # Subcomando --ingest
    ingest_parser = subparsers.add_parser(
        "ingest", help="Ingerir un documento para la memoria"
    )
    ingest_parser.add_argument("filepath", help="Ruta al archivo a ingerir")
    ingest_parser.add_argument(
        "--tags", help="Etiquetas separadas por coma", default=""
    )

    # Subcomando --forget
    forget_parser = subparsers.add_parser("forget", help="Eliminar una memoria por ID")
    forget_parser.add_argument("memory_id", help="ID de la memoria a eliminar")

    args = parser.parse_args()

    # =============================================================
    # 1. COMANDO PRINCIPAL (CONSULTA DIRECTA)
    # =============================================================
    if args.command is None:
        query = " ".join(args.query)
        if not query and not args.chat:
            print("🤖 Uso: ai 'tu instrucción'")
            print("    ai --chat")
            print("    ai --memory 'término'")
            print("    ai --status")
            return

        orchestrator = Orchestrator()

        if args.chat:
            console.print(
                "[bold green]🤖 Modo Chat[/bold green] (escribe 'exit' para salir)"
            )
            while True:
                try:
                    q = input("Tú: ")
                    if q.lower() in ["exit", "salir", "quit"]:
                        break
                    response = orchestrator.process(q)
                    console.print(f"\n[bold cyan]AI:[/bold cyan] {response}\n")
                except KeyboardInterrupt:
                    break
        else:
            response = orchestrator.process(query)
            console.print(f"\n[bold cyan]🤖[/bold cyan] {response}\n")
        return

    # =============================================================
    # 2. SUBCOMANDO --memory
    # =============================================================
    if args.command == "memory":
        eng = EngramMemory()
        query = " ".join(args.query)
        results = eng.recall(query, limit=args.limit)
        if not results:
            console.print("[yellow]No se encontraron memorias.[/yellow]")
            return

        table = Table(title="🧠 Memoria recuperada")
        table.add_column("ID", style="dim")
        table.add_column("Contenido", style="white")
        table.add_column("Score", justify="right")
        for r in results:
            content = r.get("content", "")[:100] + (
                "..." if len(r.get("content", "")) > 100 else ""
            )
            table.add_row(str(r.get("id", "N/A")), content, str(r.get("score", 0)))
        console.print(table)
        return

    # =============================================================
    # 3. SUBCOMANDO --status
    # =============================================================
    if args.command == "status":
        eng = EngramMemory()
        stats = eng.stats()
        if stats:
            console.print("[bold]📊 Estadísticas del sistema[/bold]")
            console.print(f"• Memorias totales: {stats.get('total_memories', 0)}")
            console.print(f"• Última memoria: {stats.get('last_created', 'N/A')}")
            console.print(
                f"• Tamaño de la base de datos: {stats.get('db_size_mb', 0):.2f} MB"
            )
        else:
            console.print("[yellow]No se pudieron obtener estadísticas.[/yellow]")

        # Mostrar proveedores configurados
        console.print("\n[bold]⚙️ Configuración activa:[/bold]")
        console.print(f"• Proveedor de código: {Config.CODE_PROVIDER}")
        console.print(f"• Proveedor de arquitectura: {Config.ARCHITECTURE_PROVIDER}")
        console.print(
            f"• Proveedor rápido: {getattr(Config, 'FAST_PROVIDER', 'No configurado')}"
        )
        return

    # =============================================================
    # 4. SUBCOMANDO --specs / --list-specs
    # =============================================================
    if args.command in ("specs", "list-specs"):
        spec_mgr = SpecManager()
        specs = spec_mgr.list_specs()
        if not specs:
            console.print("[yellow]No hay especificaciones guardadas.[/yellow]")
            return

        table = Table(title="📋 Especificaciones (Specs)")
        table.add_column("Nombre", style="cyan")
        table.add_column("Descripción", style="white")
        table.add_column("Estado", style="green")
        table.add_column("Creada", style="dim")
        for s in specs:
            table.add_row(
                s.get("name", "N/A"),
                s.get("description", "")[:50]
                + ("..." if len(s.get("description", "")) > 50 else ""),
                s.get("status", "draft"),
                s.get("created_at", "")[:16],
            )
        console.print(table)
        return

    # =============================================================
    # 5. SUBCOMANDO --ingest
    # =============================================================
    if args.command == "ingest":
        filepath = Path(args.filepath).expanduser()
        if not filepath.exists():
            console.print(f"[red]❌ Archivo no encontrado: {filepath}[/red]")
            return

        ingestor = DocumentIngestor()
        tags = [t.strip() for t in args.tags.split(",") if t.strip()]
        success = ingestor.ingest_file(filepath, tags=tags)
        if success:
            console.print(f"[green]✅ Documento ingerido: {filepath.name}[/green]")
        else:
            console.print(f"[red]❌ Error al ingerir: {filepath.name}[/red]")
        return

    # =============================================================
    # 6. SUBCOMANDO --forget
    # =============================================================
    if args.command == "forget":
        eng = EngramMemory()
        success = eng.forget(args.memory_id)
        if success:
            console.print(f"[green]✅ Memoria {args.memory_id} eliminada.[/green]")
        else:
            console.print(
                f"[red]❌ No se pudo eliminar la memoria {args.memory_id}.[/red]"
            )
        return


if __name__ == "__main__":
    main()
