#!/usr/bin/env python3
import sys
import argparse
from pathlib import Path

# Añadir el directorio raíz al PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import Config
from core.context_builder import ContextBuilder
from llm.gemini import GeminiProvider
from llm.nim import NIMProvider

def main():
    Config.validate()
    
    parser = argparse.ArgumentParser(description="AIClient - Fase 1")
    parser.add_argument("query", nargs="*", help="Pregunta o prompt")
    parser.add_argument("--model", choices=["gemini", "nim"], default="gemini",
                       help="Modelo a usar (gemini o nim)")
    parser.add_argument("--chat", action="store_true", help="Modo chat interactivo")
    args = parser.parse_args()
    
    query = " ".join(args.query)
    
    if not query and not args.chat:
        print("🤖 AIClient Fase 1")
        print("Uso:")
        print('  uv run cli/main.py "tu pregunta aquí"')
        print("  uv run cli/main.py --chat")
        return
    
    context_builder = ContextBuilder()
    
    if args.chat:
        print("🤖 Modo Chat Interactivo (escribe 'exit' para salir)\n")
        while True:
            try:
                user_input = input("Tú: ")
                if user_input.lower() in ["exit", "salir", "quit"]:
                    break
                context = context_builder.build(user_input)
                response = get_llm_response(args.model, context)
                print(f"\nAI: {response}\n")
            except KeyboardInterrupt:
                break
    else:
        print(f"🔍 Procesando: {query}\n")
        context = context_builder.build(query)
        response = get_llm_response(args.model, context)
        print(f"\n🤖 Respuesta:\n{response}\n")

def get_llm_response(model_choice: str, prompt: str):
    try:
        if model_choice == "gemini":
            llm = GeminiProvider()
        else:
            llm = NIMProvider()
        return llm.generate(prompt)
    except Exception as e:
        return f"❌ Error al llamar al LLM: {str(e)}"

if __name__ == "__main__":
    main()
