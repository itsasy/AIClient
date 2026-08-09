#!/usr/bin/env python3
# cli/ai.py – Punto de entrada principal con subcomandos y TUI

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from core.config import Config
from runtime.execution_engine import ExecutionEngine
from core.commands.router import CommandRouter

# Intentar importar rich para salida mejorada
try:
    from rich.console import Console
    from rich.table import Table

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

console = Console() if RICH_AVAILABLE else None

# Configurar logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    Config.validate()

    parser = argparse.ArgumentParser(
        description="AIClient – Asistente de Desarrollo Inteligente",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Comandos principales:
  ai "consulta"              Consulta directa al asistente
  ai --chat                  Modo chat interactivo
  ai --tui                   Interfaz gráfica en terminal (TUI)
  ai --auto                  Modo autónomo (sin confirmaciones)
  ai --memory "texto"        Buscar en memoria persistente
  ai --status                Mostrar estadísticas del sistema
  ai --specs                 Listar especificaciones guardadas
  ai --ingest archivo.pdf    Ingerir documento para la memoria
  ai --forget <id>           Eliminar una memoria por ID
  ai --consolidate           Generar informe de consolidación diaria
  ai --review                Revisar propuestas de consolidación pendientes
  ai --rollback [id]         Restaurar un snapshot de memoria
  ai --snapshots             Listar snapshots disponibles
  ai --analyze               Analizar rendimiento y generar recomendaciones
  ai --optimize              Sugerir optimizaciones basadas en métricas
  ai skill search <query>    Buscar skills en GitHub
  ai skill install <repo>    Instalar una skill desde GitHub
  ai export-memory [--output nombre] [--format zip|tar]
        """,
    )

    parser.add_argument("query", nargs="*", help="Tu instrucción")
    parser.add_argument("--chat", action="store_true", help="Modo chat interactivo")
    parser.add_argument("--tui", action="store_true", help="Modo TUI (interfaz en terminal)")
    parser.add_argument(
        "--auto", action="store_true", help="Ejecutar en modo autónomo (sin confirmaciones)"
    )

    # Subcomandos
    subparsers = parser.add_subparsers(dest="command", help="Subcomandos")

    # Memoria
    memory_parser = subparsers.add_parser("memory", help="Buscar en memoria persistente")
    memory_parser.add_argument("query", nargs="+", help="Texto a buscar")
    memory_parser.add_argument("--limit", type=int, default=5, help="Máximo de resultados")

    status_parser = subparsers.add_parser("status", help="Mostrar estadísticas del sistema")
    specs_parser = subparsers.add_parser("specs", help="Listar especificaciones guardadas")
    list_specs_parser = subparsers.add_parser("list-specs", help="Alias de specs")
    ingest_parser = subparsers.add_parser("ingest", help="Ingerir un documento")
    ingest_parser.add_argument("filepath", help="Ruta al archivo")
    ingest_parser.add_argument("--tags", help="Etiquetas separadas por coma", default="")
    forget_parser = subparsers.add_parser("forget", help="Eliminar una memoria por ID")
    forget_parser.add_argument("memory_id", help="ID de la memoria a eliminar")

    # Consolidación
    consolidate_parser = subparsers.add_parser(
        "consolidate", help="Generar informe de consolidación diaria"
    )
    consolidate_parser.add_argument(
        "--days", type=int, default=1, help="Número de días a consolidar"
    )
    review_parser = subparsers.add_parser(
        "review", help="Revisar propuestas de consolidación pendientes"
    )
    rollback_parser = subparsers.add_parser(
        "rollback", help="Revertir cambios a un snapshot anterior"
    )
    rollback_parser.add_argument(
        "snapshot_id", nargs="?", help="ID del snapshot a restaurar (default: último)"
    )
    snapshots_parser = subparsers.add_parser("snapshots", help="Listar snapshots disponibles")

    # Análisis
    analyze_parser = subparsers.add_parser(
        "analyze", help="Analizar rendimiento y generar recomendaciones"
    )
    optimize_parser = subparsers.add_parser(
        "optimize", help="Sugerir optimizaciones basadas en métricas"
    )

    # Exportación
    export_parser = subparsers.add_parser(
        "export-memory", help="Exportar memoria a archivo portable"
    )
    export_parser.add_argument(
        "--output", type=str, default="aiclient_memory_export", help="Nombre base del archivo"
    )
    export_parser.add_argument(
        "--format", choices=["zip", "tar"], default="zip", help="Formato de exportación"
    )

    # Skills
    skill_parser = subparsers.add_parser("skill", help="Gestión de skills")
    skill_subparsers = skill_parser.add_subparsers(dest="skill_command")
    search_parser = skill_subparsers.add_parser("search", help="Buscar skills en GitHub")
    search_parser.add_argument("query", help="Término de búsqueda")
    install_parser = skill_subparsers.add_parser("install", help="Instalar una skill desde GitHub")
    install_parser.add_argument("repo", help="Repositorio GitHub (ej. usuario/repo)")

    args = parser.parse_args()

    # ================================================================
    # 0. TUI (interfaz gráfica en terminal)
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
    # 1. Subcomandos
    # ================================================================
    if args.command == "memory":
        from core.engram_memory import EngramMemory

        eng = EngramMemory()
        query = " ".join(args.query)
        results = eng.recall(query, limit=args.limit)
        if not results:
            print("No se encontraron memorias.")
            return
        if RICH_AVAILABLE:
            table = Table(title="🧠 Memoria recuperada")
            table.add_column("ID", style="dim")
            table.add_column("Contenido", style="white")
            for r in results:
                content = r.get("content", "")[:100]
                if len(r.get("content", "")) > 100:
                    content += "..."
                table.add_row(str(r.get("id", "N/A")), content)
            console.print(table)
        else:
            for r in results:
                print(f"ID: {r.get('id', 'N/A')} | {r.get('content', '')[:100]}...")
        return

    if args.command == "status":
        from core.engram_memory import EngramMemory

        eng = EngramMemory()
        stats = eng.stats()
        if RICH_AVAILABLE:
            console.print("[bold]📊 Estadísticas del sistema[/bold]")
            if stats:
                console.print(f"• Memorias totales: {stats.get('total_memories', 0)}")
                console.print(f"• Última memoria: {stats.get('last_created', 'N/A')}")
                console.print(f"• Tamaño DB: {stats.get('db_size_mb', 0):.2f} MB")
            else:
                console.print("[yellow]No se pudieron obtener estadísticas.[/yellow]")
            console.print("\n[bold]⚙️ Configuración activa:[/bold]")
            console.print(f"• Proveedor código: {Config.CODE_PROVIDER}")
            console.print(f"• Proveedor arquitectura: {Config.ARCHITECTURE_PROVIDER}")
        else:
            print("📊 Estadísticas del sistema")
            if stats:
                print(f"• Memorias totales: {stats.get('total_memories', 0)}")
                print(f"• Última memoria: {stats.get('last_created', 'N/A')}")
                print(f"• Tamaño DB: {stats.get('db_size_mb', 0):.2f} MB")
            else:
                print("No se pudieron obtener estadísticas.")
            print("\n⚙️ Configuración activa:")
            print(f"• Proveedor código: {Config.CODE_PROVIDER}")
            print(f"• Proveedor arquitectura: {Config.ARCHITECTURE_PROVIDER}")
        return

    if args.command in ("specs", "list-specs"):
        from core.spec_manager import SpecManager

        spec_mgr = SpecManager()
        specs = spec_mgr.list_specs()
        if not specs:
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

    if args.command == "ingest":
        from core.document_ingestor import DocumentIngestor

        filepath = Path(args.filepath).expanduser()
        if not filepath.exists():
            print(f"❌ Archivo no encontrado: {filepath}")
            return
        ingestor = DocumentIngestor()
        tags = [t.strip() for t in args.tags.split(",") if t.strip()] if args.tags else []
        success = ingestor.ingest_file(filepath, tags=tags)
        if success:
            print(f"✅ Documento ingerido: {filepath.name}")
        else:
            print(f"❌ Error al ingerir: {filepath.name}")
        return

    if args.command == "forget":
        from core.engram_memory import EngramMemory

        eng = EngramMemory()
        success = eng.forget(args.memory_id)
        if success:
            print(f"✅ Memoria {args.memory_id} eliminada.")
        else:
            print(f"❌ No se pudo eliminar la memoria {args.memory_id}.")
        return

    # Consolidación
    if args.command == "consolidate":
        from core.consolidation.daily_consolidator import DailyConsolidator

        consolidator = DailyConsolidator()
        report = consolidator.generate_report(days=args.days)
        print(
            f"✅ Informe de consolidación generado en .memory/consolidation/pending-{report.date}.md"
        )
        print(report.summary)
        return

    if args.command == "review":
        from core.consolidation.daily_consolidator import DailyConsolidator

        consolidator = DailyConsolidator()
        pending = consolidator.list_pending()
        if not pending:
            print("No hay informes pendientes de revisión.")
            return
        print(f"📋 Revisando {len(pending)} informe(s) pendiente(s)...\n")
        for report_path in pending:
            content = report_path.read_text(encoding="utf-8")
            print(f"=== {report_path.name} ===")
            print(content)
            print("\n" + "=" * 60 + "\n")
            response = input("¿Aplicar propuestas de este informe? (s/n): ").strip().lower()
            if response == "s":
                print("✅ Propuestas aprobadas. Aplicando cambios...")
                consolidator.mark_done(report_path)
            else:
                print("⏭️ Propuestas rechazadas. El informe se mantiene pendiente.")
        return

    if args.command == "rollback":
        from core.consolidation.snapshot_manager import SnapshotManager

        snap_mgr = SnapshotManager()
        snapshot_id = args.snapshot_id or snap_mgr.latest()
        if not snapshot_id:
            print("No hay snapshots disponibles.")
            return
        confirm = input(f"⚠️  ¿Restaurar snapshot '{snapshot_id}'? (s/n): ").strip().lower()
        if confirm == "s":
            if snap_mgr.rollback(snapshot_id):
                print(f"✅ Snapshot '{snapshot_id}' restaurado correctamente.")
            else:
                print(f"❌ Error restaurando snapshot '{snapshot_id}'.")
        else:
            print("❌ Operación cancelada.")
        return

    if args.command == "snapshots":
        from core.consolidation.snapshot_manager import SnapshotManager

        snap_mgr = SnapshotManager()
        snapshots = snap_mgr.list_snapshots()
        if not snapshots:
            print("No hay snapshots.")
            return
        print("📸 Snapshots disponibles:")
        for s in snapshots:
            label = f" ({s.get('label', '')})" if s.get("label") else ""
            print(f"- {s['id']}{label} - {s['created_at']}")
        return

    # Análisis
    if args.command == "analyze":
        from core.analytics.analyzer import Analyzer

        analyzer = Analyzer()
        report = analyzer.analyze()
        print("📊 **Informe de análisis**\n")
        agg = report["summary"]
        print(f"Total ejecuciones: {agg['total']}")
        print(f"Tasa de éxito: {agg['success_rate']:.1f}%")
        print(f"Tiempo promedio: {agg['avg_duration']:.2f}s")
        print("\n🏆 **Mejores proveedores:**")
        for provider, stats in agg.get("provider_stats", {}).items():
            rate = (stats["success"] / stats["total"] * 100) if stats["total"] > 0 else 0
            print(f"  - {provider}: {rate:.1f}% ({stats['success']}/{stats['total']})")
        print("\n💡 **Recomendaciones:**")
        for rec in report.get("recommendations", []):
            print(f"  {rec}")
        if report.get("top_issues"):
            print("\n⚠️ **Problemas comunes:**")
            for issue in report["top_issues"]:
                print(f"  {issue}")
        return

    if args.command == "optimize":
        from core.analytics.analyzer import Analyzer

        analyzer = Analyzer()
        report = analyzer.analyze()
        recommendations = report.get("recommendations", [])
        if not recommendations:
            print("✅ No se encontraron recomendaciones de optimización.")
            return
        print("🔧 **Sugerencias de optimización:**\n")
        for i, rec in enumerate(recommendations, 1):
            print(f"{i}. {rec}")
        response = (
            input("\n¿Deseas aplicar alguna sugerencia automáticamente? (s/n): ").strip().lower()
        )
        if response == "s":
            print(
                "✅ Las sugerencias se han aplicado (en un sistema real, se modificaría .env o configuraciones)."
            )
        else:
            print("ℹ️  Puedes aplicar manualmente las sugerencias editando .env.")
        return

    # Exportación de memoria
    if args.command == "export-memory":
        from core.export_memory import MemoryExporter

        exporter = MemoryExporter()
        output = exporter.export(output_name=args.output, format=args.format)
        print(f"✅ Memoria exportada correctamente: {output}")
        return

    # Skills
    if args.command == "skill":
        if args.skill_command == "search":
            import requests

            url = f"https://api.github.com/search/repositories?q={args.query}+SKILL.md"
            response = requests.get(url)
            data = response.json()
            items = data.get("items", [])[:5]
            if not items:
                print("No se encontraron skills.")
                return
            print("🔍 Skills encontradas en GitHub:")
            for repo in items:
                print(f"- {repo['full_name']}: {repo.get('description', 'Sin descripción')}")
        elif args.skill_command == "install":
            import subprocess

            target = Path.home() / ".engram" / "skills" / args.repo.split("/")[-1]
            if target.exists():
                print(f"⚠️  La skill ya existe en {target}")
                return
            print(f"📦 Instalando {args.repo}...")
            subprocess.run(["git", "clone", f"https://github.com/{args.repo}", str(target)])
            print(f"✅ Skill instalada en {target}")
        return

    # ================================================================
    # 2. COMANDO PRINCIPAL (CONSULTA DIRECTA) o --chat
    # ================================================================
    if args.command is None:
        query = " ".join(args.query)
        if not query and not args.chat:
            print("🤖 Uso: ai 'tu instrucción'")
            print("    ai --chat")
            print("    ai --tui")
            print("    ai --memory 'término'")
            print("    ai --status")
            return

        router = CommandRouter()
        engine = ExecutionEngine()

        if args.chat:
            print("🤖 Modo Chat (escribe 'exit' para salir)\n")
            while True:
                try:
                    q = input("Tú: ")
                    if q.lower() in ["exit", "salir", "quit"]:
                        break
                    plan = router.process(q)
                    if plan is not None:
                        if args.auto:
                            plan.execution_policy["autonomous"] = True
                            plan.execution_policy["requires_approval"] = False
                        result = engine.execute(plan)
                    else:
                        result = engine.execute_from_input(q)
                    if result.is_success:
                        print(f"\nAI: {result.result}\n")
                    else:
                        print(f"\n❌ Error: {result.error}\n")
                except KeyboardInterrupt:
                    break
        else:
            plan = router.process(query)
            if plan is not None:
                if args.auto:
                    plan.execution_policy["autonomous"] = True
                    plan.execution_policy["requires_approval"] = False
                result = engine.execute(plan)
            else:
                result = engine.execute_from_input(query)

            if result.is_success:
                response = result.result
            else:
                response = f"❌ Error: {result.error}"
            if RICH_AVAILABLE:
                console.print(f"\n[bold cyan]🤖[/bold cyan] {response}\n")
            else:
                print(f"\n🤖 {response}\n")
        return


if __name__ == "__main__":
    main()
