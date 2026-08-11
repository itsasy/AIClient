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

# ================================================================
# Rich
# ================================================================

try:
    from rich.console import Console
    from rich.table import Table

    RICH_AVAILABLE = True

except ImportError:
    RICH_AVAILABLE = False


console = Console() if RICH_AVAILABLE else None


# ================================================================
# Logging
# ================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


# ================================================================
# Comandos conocidos
# ================================================================

KNOWN_COMMANDS = {
    "memory",
    "status",
    "specs",
    "list-specs",
    "ingest",
    "forget",
    "consolidate",
    "review",
    "rollback",
    "snapshots",
    "analyze",
    "optimize",
    "export-memory",
    "skill",
}


# ================================================================
# Consulta directa
# ================================================================


def handle_direct_query(
    query: str,
    auto_mode: bool = False,
) -> None:
    if not query.strip():
        return

    router = CommandRouter()
    engine = ExecutionEngine(command_router=router)

    result = engine.execute_from_input(query)

    if result.is_success:
        response = result.result
    else:
        response = f"❌ Error: {result.error}"

    if RICH_AVAILABLE:
        console.print(f"\n[bold cyan]🤖[/bold cyan] {response}\n")
    else:
        print(f"\n🤖 {response}\n")


# ================================================================
# MAIN
# ================================================================


def main():
    Config.validate()

    # ============================================================
    # Detectar consulta directa ANTES de argparse
    # ============================================================
    #
    # Esto permite:
    #
    #   ai "hola"
    #   ai "crea un proyecto Python"
    #
    # sin que argparse intente interpretar "hola" como un
    # subcomando.
    #
    # Los comandos conocidos siguen pasando por argparse:
    #
    #   ai status
    #   ai memory "python"
    #   ai skill search github
    #
    # ============================================================

    argv = sys.argv[1:]

    has_command = any(arg in KNOWN_COMMANDS for arg in argv)

    has_query = any(not arg.startswith("-") for arg in argv)

    # ------------------------------------------------------------
    # Consulta directa
    # ------------------------------------------------------------

    if has_query and not has_command:
        query_args = list(argv)

        auto_mode = "--auto" in query_args
        chat_mode = "--chat" in query_args
        tui_mode = "--tui" in query_args

        query_args = [
            arg
            for arg in query_args
            if arg
            not in {
                "--auto",
                "--chat",
                "--tui",
            }
        ]

        # TUI y chat deben seguir el flujo normal de argparse.
        if not chat_mode and not tui_mode:
            query = " ".join(query_args).strip()

            if query:
                handle_direct_query(
                    query=query,
                    auto_mode=auto_mode,
                )
                return

    # ============================================================
    # Argument parser
    # ============================================================

    parser = argparse.ArgumentParser(
        description="AIClient – Asistente de Desarrollo Inteligente",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Comandos principales:

  ai "consulta"              Consulta directa al asistente
  ai --chat                  Modo chat interactivo
  ai --tui                   Interfaz gráfica en terminal (TUI)
  ai --auto "consulta"       Modo autónomo (sin confirmaciones)

  ai memory "texto"          Buscar en memoria persistente
  ai status                  Mostrar estadísticas del sistema
  ai specs                   Listar especificaciones guardadas
  ai list-specs              Alias de specs
  ai ingest archivo.pdf      Ingerir documento para la memoria
  ai forget ID               Eliminar una memoria por ID

  ai consolidate             Generar informe de consolidación diaria
  ai review                  Revisar propuestas de consolidación
  ai rollback [id]           Restaurar un snapshot de memoria
  ai snapshots               Listar snapshots disponibles

  ai analyze                 Analizar rendimiento y generar recomendaciones
  ai optimize                Sugerir optimizaciones basadas en métricas

  ai export-memory           Exportar memoria a archivo portable

  ai skill search <query>    Buscar skills en GitHub
  ai skill install <repo>   Instalar una skill desde GitHub
""",
    )

    # ============================================================
    # Opciones globales
    # ============================================================

    parser.add_argument(
        "--chat",
        action="store_true",
        help="Modo chat interactivo",
    )

    parser.add_argument(
        "--tui",
        action="store_true",
        help="Modo TUI (interfaz en terminal)",
    )

    parser.add_argument(
        "--auto",
        action="store_true",
        help="Ejecutar en modo autónomo (sin confirmaciones)",
    )

    # ============================================================
    # Subcomandos
    # ============================================================

    subparsers = parser.add_subparsers(
        dest="command",
        help="Subcomandos",
    )

    # ============================================================
    # Memoria
    # ============================================================

    memory_parser = subparsers.add_parser(
        "memory",
        help="Buscar en memoria persistente",
    )

    memory_parser.add_argument(
        "query",
        nargs="+",
        help="Texto a buscar",
    )

    memory_parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Máximo de resultados",
    )

    # ============================================================
    # Status
    # ============================================================

    subparsers.add_parser(
        "status",
        help="Mostrar estadísticas del sistema",
    )

    # ============================================================
    # Specs
    # ============================================================

    subparsers.add_parser(
        "specs",
        help="Listar especificaciones guardadas",
    )

    subparsers.add_parser(
        "list-specs",
        help="Alias de specs",
    )

    # ============================================================
    # Ingest
    # ============================================================

    ingest_parser = subparsers.add_parser(
        "ingest",
        help="Ingerir un documento",
    )

    ingest_parser.add_argument(
        "filepath",
        help="Ruta al archivo",
    )

    ingest_parser.add_argument(
        "--tags",
        help="Etiquetas separadas por coma",
        default="",
    )

    # ============================================================
    # Forget
    # ============================================================

    forget_parser = subparsers.add_parser(
        "forget",
        help="Eliminar una memoria por ID",
    )

    forget_parser.add_argument(
        "memory_id",
        help="ID de la memoria a eliminar",
    )

    # ============================================================
    # Consolidación
    # ============================================================

    consolidate_parser = subparsers.add_parser(
        "consolidate",
        help="Generar informe de consolidación diaria",
    )

    consolidate_parser.add_argument(
        "--days",
        type=int,
        default=1,
        help="Número de días a consolidar",
    )

    subparsers.add_parser(
        "review",
        help="Revisar propuestas de consolidación pendientes",
    )

    # ============================================================
    # Rollback
    # ============================================================

    rollback_parser = subparsers.add_parser(
        "rollback",
        help="Revertir cambios a un snapshot anterior",
    )

    rollback_parser.add_argument(
        "snapshot_id",
        nargs="?",
        help="ID del snapshot a restaurar (default: último)",
    )

    # ============================================================
    # Snapshots
    # ============================================================

    subparsers.add_parser(
        "snapshots",
        help="Listar snapshots disponibles",
    )

    # ============================================================
    # Análisis
    # ============================================================

    subparsers.add_parser(
        "analyze",
        help="Analizar rendimiento y generar recomendaciones",
    )

    subparsers.add_parser(
        "optimize",
        help="Sugerir optimizaciones basadas en métricas",
    )

    # ============================================================
    # Exportación
    # ============================================================

    export_parser = subparsers.add_parser(
        "export-memory",
        help="Exportar memoria a archivo portable",
    )

    export_parser.add_argument(
        "--output",
        type=str,
        default="aiclient_memory_export",
        help="Nombre base del archivo",
    )

    export_parser.add_argument(
        "--format",
        choices=["zip", "tar"],
        default="zip",
        help="Formato de exportación",
    )

    # ============================================================
    # Skills
    # ============================================================

    skill_parser = subparsers.add_parser(
        "skill",
        help="Gestión de skills",
    )

    skill_subparsers = skill_parser.add_subparsers(
        dest="skill_command",
    )

    search_parser = skill_subparsers.add_parser(
        "search",
        help="Buscar skills en GitHub",
    )

    search_parser.add_argument(
        "query",
        help="Término de búsqueda",
    )

    install_parser = skill_subparsers.add_parser(
        "install",
        help="Instalar una skill desde GitHub",
    )

    install_parser.add_argument(
        "repo",
        help="Repositorio GitHub (ej. usuario/repo)",
    )

    # ============================================================
    # Parse
    # ============================================================

    args = parser.parse_args()

    # ============================================================
    # 0. TUI
    # ============================================================

    if args.tui:
        try:
            from tui.app import main as tui_main

            tui_main()

        except ImportError as e:
            print(
                "❌ Error: no se pudo cargar la TUI. "
                f"Instala textual: pip install textual\nError: {e}"
            )

        return

    # ============================================================
    # 1. Subcomando memory
    # ============================================================

    if args.command == "memory":
        from core.engram_memory import EngramMemory

        eng = EngramMemory()

        query = " ".join(args.query)

        results = eng.recall(
            query,
            limit=args.limit,
        )

        if not results:
            print("No se encontraron memorias.")
            return

        if RICH_AVAILABLE:
            table = Table(title="🧠 Memoria recuperada")

            table.add_column(
                "ID",
                style="dim",
            )

            table.add_column(
                "Contenido",
                style="white",
            )

            for r in results:
                content = r.get(
                    "content",
                    "",
                )[:100]

                if (
                    len(
                        r.get(
                            "content",
                            "",
                        )
                    )
                    > 100
                ):
                    content += "..."

                table.add_row(
                    str(
                        r.get(
                            "id",
                            "N/A",
                        )
                    ),
                    content,
                )

            console.print(table)

        else:
            for r in results:
                print(f"ID: {r.get('id', 'N/A')} | " f"{r.get('content', '')[:100]}...")

        return

    # ============================================================
    # 2. Status
    # ============================================================

    if args.command == "status":
        from core.engram_memory import EngramMemory

        eng = EngramMemory()

        stats = eng.stats()

        if RICH_AVAILABLE:
            console.print("[bold]📊 Estadísticas del sistema[/bold]")

            if stats:
                console.print(f"• Memorias totales: " f"{stats.get('total_memories', 0)}")

                console.print(f"• Última memoria: " f"{stats.get('last_created', 'N/A')}")

                console.print(f"• Tamaño DB: " f"{stats.get('db_size_mb', 0):.2f} MB")

            else:
                console.print("[yellow]No se pudieron obtener estadísticas.[/yellow]")

            console.print("\n[bold]⚙️ Configuración activa:[/bold]")

            console.print(f"• Proveedor código: " f"{Config.CODE_PROVIDER}")

            console.print(f"• Proveedor arquitectura: " f"{Config.ARCHITECTURE_PROVIDER}")

        else:
            print("📊 Estadísticas del sistema")

            if stats:
                print(f"• Memorias totales: " f"{stats.get('total_memories', 0)}")

                print(f"• Última memoria: " f"{stats.get('last_created', 'N/A')}")

                print(f"• Tamaño DB: " f"{stats.get('db_size_mb', 0):.2f} MB")

            else:
                print("No se pudieron obtener estadísticas.")

            print("\n⚙️ Configuración activa:")

            print(f"• Proveedor código: " f"{Config.CODE_PROVIDER}")

            print(f"• Proveedor arquitectura: " f"{Config.ARCHITECTURE_PROVIDER}")

        return

    # ============================================================
    # 3. Specs
    # ============================================================

    if args.command in (
        "specs",
        "list-specs",
    ):
        from core.spec_manager import SpecManager

        spec_mgr = SpecManager()

        specs = spec_mgr.list_specs()

        if not specs:
            print("No hay especificaciones guardadas.")
            return

        if RICH_AVAILABLE:
            table = Table(title="📋 Especificaciones (Specs)")

            table.add_column(
                "Nombre",
                style="cyan",
            )

            table.add_column(
                "Descripción",
                style="white",
            )

            table.add_column(
                "Estado",
                style="green",
            )

            table.add_column(
                "Creada",
                style="dim",
            )

            for s in specs:
                desc = s.get(
                    "description",
                    "",
                )[:50]

                if (
                    len(
                        s.get(
                            "description",
                            "",
                        )
                    )
                    > 50
                ):
                    desc += "..."

                table.add_row(
                    s.get(
                        "name",
                        "N/A",
                    ),
                    desc,
                    s.get(
                        "status",
                        "draft",
                    ),
                    s.get(
                        "created_at",
                        "",
                    )[:16],
                )

            console.print(table)

        else:
            for s in specs:
                print(
                    f"📋 {s.get('name')} – "
                    f"{s.get('status')} "
                    f"({s.get('created_at', '')[:16]})"
                )

        return

    # ============================================================
    # 4. Ingest
    # ============================================================

    if args.command == "ingest":
        from core.document_ingestor import DocumentIngestor

        filepath = Path(args.filepath).expanduser()

        if not filepath.exists():
            print(f"❌ Archivo no encontrado: {filepath}")
            return

        ingestor = DocumentIngestor()

        tags = [t.strip() for t in args.tags.split(",") if t.strip()] if args.tags else []

        success = ingestor.ingest_file(
            filepath,
            tags=tags,
        )

        if success:
            print(f"✅ Documento ingerido: " f"{filepath.name}")
        else:
            print(f"❌ Error al ingerir: " f"{filepath.name}")

        return

    # ============================================================
    # 5. Forget
    # ============================================================

    if args.command == "forget":
        from core.engram_memory import EngramMemory

        eng = EngramMemory()

        success = eng.forget(args.memory_id)

        if success:
            print(f"✅ Memoria {args.memory_id} eliminada.")
        else:
            print(f"❌ No se pudo eliminar " f"la memoria {args.memory_id}.")

        return

    # ============================================================
    # 6. Consolidate
    # ============================================================

    if args.command == "consolidate":
        from core.consolidation.daily_consolidator import (
            DailyConsolidator,
        )

        consolidator = DailyConsolidator()

        report = consolidator.generate_report(days=args.days)

        print(
            "✅ Informe de consolidación generado en "
            f".memory/consolidation/pending-{report.date}.md"
        )

        print(report.summary)

        return

    # ============================================================
    # 7. Review
    # ============================================================

    if args.command == "review":
        from core.consolidation.daily_consolidator import (
            DailyConsolidator,
        )

        consolidator = DailyConsolidator()

        pending = consolidator.list_pending()

        if not pending:
            print("No hay informes pendientes de revisión.")
            return

        print(f"📋 Revisando {len(pending)} " "informe(s) pendiente(s)...\n")

        for report_path in pending:
            content = report_path.read_text(encoding="utf-8")

            print(f"=== {report_path.name} ===")

            print(content)

            print("\n" + "=" * 60 + "\n")

            response = input("¿Aplicar propuestas de este informe? (s/n): ").strip().lower()

            if response == "s":
                print("✅ Propuestas aprobadas. " "Aplicando cambios...")

                consolidator.mark_done(report_path)

            else:
                print("⏭️ Propuestas rechazadas. " "El informe se mantiene pendiente.")

        return

    # ============================================================
    # 8. Rollback
    # ============================================================

    if args.command == "rollback":
        from core.consolidation.snapshot_manager import (
            SnapshotManager,
        )

        snap_mgr = SnapshotManager()

        snapshot_id = args.snapshot_id or snap_mgr.latest()

        if not snapshot_id:
            print("No hay snapshots disponibles.")
            return

        confirm = input(f"⚠️  ¿Restaurar snapshot " f"'{snapshot_id}'? (s/n): ").strip().lower()

        if confirm == "s":
            if snap_mgr.rollback(snapshot_id):
                print(f"✅ Snapshot '{snapshot_id}' " "restaurado correctamente.")
            else:
                print(f"❌ Error restaurando snapshot " f"'{snapshot_id}'.")

        else:
            print("❌ Operación cancelada.")

        return

    # ============================================================
    # 9. Snapshots
    # ============================================================

    if args.command == "snapshots":
        from core.consolidation.snapshot_manager import (
            SnapshotManager,
        )

        snap_mgr = SnapshotManager()

        snapshots = snap_mgr.list_snapshots()

        if not snapshots:
            print("No hay snapshots.")
            return

        print("📸 Snapshots disponibles:")

        for s in snapshots:
            label = f" ({s.get('label', '')})" if s.get("label") else ""

            print(f"- {s['id']}{label} - " f"{s['created_at']}")

        return

    # ============================================================
    # 10. Analyze
    # ============================================================

    if args.command == "analyze":
        from core.analytics.analyzer import Analyzer

        analyzer = Analyzer()

        report = analyzer.analyze()

        print("📊 **Informe de análisis**\n")

        agg = report["summary"]

        print(f"Total ejecuciones: " f"{agg['total']}")

        print(f"Tasa de éxito: " f"{agg['success_rate']:.1f}%")

        print(f"Tiempo promedio: " f"{agg['avg_duration']:.2f}s")

        print("\n🏆 **Mejores proveedores:**")

        for provider, stats in agg.get(
            "provider_stats",
            {},
        ).items():
            rate = stats["success"] / stats["total"] * 100 if stats["total"] > 0 else 0

            print(f"  - {provider}: " f"{rate:.1f}% " f"({stats['success']}/{stats['total']})")

        print("\n💡 **Recomendaciones:**")

        for rec in report.get(
            "recommendations",
            [],
        ):
            print(f"  {rec}")

        if report.get("top_issues"):
            print("\n⚠️ **Problemas comunes:**")

            for issue in report["top_issues"]:
                print(f"  {issue}")

        return

    # ============================================================
    # 11. Optimize
    # ============================================================

    if args.command == "optimize":
        from core.analytics.analyzer import Analyzer

        analyzer = Analyzer()

        report = analyzer.analyze()

        recommendations = report.get(
            "recommendations",
            [],
        )

        if not recommendations:
            print("✅ No se encontraron " "recomendaciones de optimización.")
            return

        print("🔧 **Sugerencias de optimización:**\n")

        for i, rec in enumerate(
            recommendations,
            1,
        ):
            print(f"{i}. {rec}")

        response = (
            input("\n¿Deseas aplicar alguna sugerencia " "automáticamente? (s/n): ").strip().lower()
        )

        if response == "s":
            print(
                "✅ Las sugerencias se han aplicado "
                "(en un sistema real, se modificaría "
                ".env o configuraciones)."
            )

        else:
            print("ℹ️  Puedes aplicar manualmente " "las sugerencias editando .env.")

        return

    # ============================================================
    # 12. Export memory
    # ============================================================

    if args.command == "export-memory":
        from core.export_memory import MemoryExporter

        exporter = MemoryExporter()

        output = exporter.export(
            output_name=args.output,
            format=args.format,
        )

        print(f"✅ Memoria exportada correctamente: " f"{output}")

        return

    # ============================================================
    # 13. Skills
    # ============================================================

    if args.command == "skill":
        if args.skill_command == "search":
            import requests

            url = "https://api.github.com/search/repositories" f"?q={args.query}+SKILL.md"

            response = requests.get(url)

            data = response.json()

            items = data.get(
                "items",
                [],
            )[:5]

            if not items:
                print("No se encontraron skills.")
                return

            print("🔍 Skills encontradas en GitHub:")

            for repo in items:
                print(f"- {repo['full_name']}: " f"{repo.get('description', 'Sin descripción')}")

        elif args.skill_command == "install":
            import subprocess

            target = Path.home() / ".engram" / "skills" / args.repo.split("/")[-1]

            if target.exists():
                print(f"⚠️  La skill ya existe en " f"{target}")
                return

            print(f"📦 Instalando {args.repo}...")

            subprocess.run(
                [
                    "git",
                    "clone",
                    f"https://github.com/{args.repo}",
                    str(target),
                ]
            )

            print(f"✅ Skill instalada en {target}")

        return

    # ============================================================
    # 14. Chat / consulta interactiva
    # ============================================================

    if args.command is None:
        if args.chat:
            print("🤖 Modo Chat " "(escribe 'exit' para salir)\n")

            engine = ExecutionEngine()
            router = CommandRouter()

            while True:
                try:
                    q = input("Tú: ")

                    if q.lower() in [
                        "exit",
                        "salir",
                        "quit",
                    ]:
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
                        print(f"\n❌ Error: " f"{result.error}\n")

                except KeyboardInterrupt:
                    print()
                    break

            return

        # --------------------------------------------------------
        # Sin comando ni consulta
        # --------------------------------------------------------

        print("🤖 Uso: ai 'tu instrucción'")

        print("    ai --chat")

        print("    ai --tui")

        print("    ai --auto 'tu instrucción'")

        print("    ai memory 'término'")

        print("    ai status")

        return


# ================================================================
# Entry point
# ================================================================

if __name__ == "__main__":
    main()
