#!/usr/bin/env python3
"""
Punto de entrada alternativo para AIClient.
Ejecuta desde la raíz: python main.py "tu consulta"
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from runtime.execution_engine import ExecutionEngine


def main():
    engine = ExecutionEngine()

    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = "Hola, ¿cómo estás?"

    result = engine.execute_from_input(query)

    if result.is_success:
        print(result.result)
    else:
        print(f"❌ Error: {result.error}")


if __name__ == "__main__":
    main()
