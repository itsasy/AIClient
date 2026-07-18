#!/usr/bin/env python3

import argparse
import logging
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    force=True,
)

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from core.config import Config
from core.orchestrator import Orchestrator

Config.TARGET_PROJECT_ROOT = Path.cwd()

logger.info("🚀 AIClient iniciado")

orchestrator = Orchestrator()


def main():
    Config.validate()

    parser = argparse.ArgumentParser(description="AIClient - Asistente Personal")
    parser.add_argument("query", nargs="*", help="Tu instrucción")
    parser.add_argument("--chat", action="store_true", help="Modo chat")
    args = parser.parse_args()

    query = " ".join(args.query)

    if not query and not args.chat:
        print('🤖 Uso: ai "tu instrucción"')
        print("    ai --chat")
        return

    if args.chat:
        logger.info("Entrando en modo chat interactivo")
        print("🤖 Modo Chat (escribe 'exit' para salir)\n")

        while True:
            try:
                q = input("Tú: ")
                if q.lower() in ["exit", "salir", "quit"]:
                    logger.info("Saliendo del modo chat")
                    break

                logger.info("Consulta: %s", q[:100])
                print(f"\nAI: {orchestrator.process(q)}\n")

            except KeyboardInterrupt:
                logger.info("Modo chat interrumpido")
                break
    else:
        logger.info("Consulta: %s", query[:150])
        print(f"\n🤖 {orchestrator.process(query)}\n")


if __name__ == "__main__":
    main()
