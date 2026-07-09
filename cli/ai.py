#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from core.config import Config
from core.orchestrator import Orchestrator

orchestrator = Orchestrator()


def main():
    Config.validate()
    parser = argparse.ArgumentParser(description="AIClient - Asistente Personal")
    parser.add_argument("query", nargs="*", help="Tu instrucción")
    parser.add_argument("--chat", action="store_true", help="Modo chat")
    args = parser.parse_args()

    query = " ".join(args.query)
    if not query and not args.chat:
        print("🤖 Uso: ai \"tu instrucción\"")
        print("    ai --chat")
        return

    if args.chat:
        print("🤖 Modo Chat (exit para salir)\n")
        while True:
            try:
                q = input("Tú: ")
                if q.lower() in ["exit", "salir"]:
                    break
                print(f"\nAI: {orchestrator.process(q)}\n")
            except KeyboardInterrupt:
                break
    else:
        print(f"\n🤖 {orchestrator.process(query)}\n")


if __name__ == "__main__":
    main()
