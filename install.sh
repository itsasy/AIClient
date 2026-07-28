#!/bin/bash
# ================================================================
# AIClient - Script de instalación automatizada
# (con Engram, DeepSeek, Self-Critic, CLI avanzado, TUI e ingesta)
# ================================================================
# Ejecutar: chmod +x install.sh && ./install.sh
# ================================================================

set -e  # Detenerse si hay error

echo "🚀 Iniciando instalación de AIClient (versión completa)..."

# ================================================================
# 1. PYTHON + ENTORNO VIRTUAL
# ================================================================
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 no encontrado. Instalando..."
    sudo apt update && sudo apt install -y python3 python3-venv python3-pip
fi

echo "🐍 Creando entorno virtual..."
python3 -m venv venv
source venv/bin/activate

echo "📦 Instalando dependencias base..."
pip install --upgrade pip
pip install python-dotenv google-genai requests openai flask beautifulsoup4

# ================================================================
# 2. RAG SEMÁNTICO (OPCIONAL)
# ================================================================
echo ""
read -p "¿Instalar soporte para RAG semántico (sentence-transformers)? (s/N): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Ss]$ ]]; then
    pip install sentence-transformers numpy
    echo "✅ RAG semántico instalado."
else
    echo "ℹ️  Puedes instalarlo después con: pip install sentence-transformers numpy"
fi

# ================================================================
# 3. CLI AVANZADO + TUI (OPCIONAL)
# ================================================================
echo ""
read -p "¿Instalar dependencias para CLI avanzado (rich) y TUI (textual)? (s/N): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Ss]$ ]]; then
    pip install rich textual
    echo "✅ Rich y Textual instalados (CLI mejorado + TUI)."
else
    echo "ℹ️  Puedes instalarlos después con: pip install rich textual"
fi

# ================================================================
# 4. INGESTA DE DOCUMENTOS (OPCIONAL)
# ================================================================
echo ""
read -p "¿Instalar dependencias para ingesta de documentos (PDF, DOCX, imágenes)? (s/N): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Ss]$ ]]; then
    pip install pypdf python-docx pillow
    echo "✅ Dependencias de ingesta instaladas."
else
    echo "ℹ️  Puedes instalarlas después con: pip install pypdf python-docx pillow"
fi

# ================================================================
# 5. ENGRAM (MEMORIA PERSISTENTE)
# ================================================================
echo ""
echo "🧠 Instalando Engram (memoria persistente)..."

if command -v engram &> /dev/null; then
    echo "✅ Engram ya está instalado: $(which engram)"
else
    if command -v brew &> /dev/null; then
        echo "🍺 Instalando Engram con Homebrew..."
        brew tap gentleman-programming/tap
        brew install engram
        echo "✅ Engram instalado con Homebrew."
    elif command -v go &> /dev/null; then
        GO_VERSION=$(go version | grep -oP 'go\K[0-9.]+' | cut -d. -f1,2)
        if [[ $(echo "$GO_VERSION >= 1.24" | bc) -eq 1 ]]; then
            echo "🐹 Instalando Engram desde código fuente (Go $GO_VERSION)..."
            go install github.com/Gentleman-Programming/engram/cmd/engram@latest
            export PATH=$PATH:~/go/bin
            echo 'export PATH=$PATH:~/go/bin' >> ~/.bashrc
            echo "✅ Engram instalado desde código fuente."
        else
            echo "⚠️  Versión de Go ($GO_VERSION) es antigua. Se necesita Go 1.24+."
            echo "   Instala Go desde: https://go.dev/dl/"
            echo "   Luego ejecuta: go install github.com/Gentleman-Programming/engram/cmd/engram@latest"
        fi
    else
        echo "⚠️  No se encontró Homebrew ni Go."
        echo "   Instala Engram manualmente desde:"
        echo "   https://github.com/Gentleman-Programming/engram/releases"
        echo "   Descarga el binario para Linux y colócalo en /usr/local/bin/"
    fi
fi

# ================================================================
# 6. CREAR DIRECTORIOS NECESARIOS
# ================================================================
echo "📁 Creando estructura de directorios..."
mkdir -p llm/prompts
mkdir -p obsidian_vault
mkdir -p skills/knowledge

# ================================================================
# 7. CONFIGURACIÓN DE ENTORNO (.env)
# ================================================================
if [ ! -f .env ]; then
    echo "⚙️  Creando archivo .env con todas las variables..."
    cat > .env << 'EOF'
# ================================================================
# AIClient - Variables de entorno (completas)
# ================================================================

# --- Gemini ---
GEMINI_API_KEY=tu_api_key_aqui
GEMINI_MODEL=gemini-2.5-flash

# --- NVIDIA NIM ---
NVIDIA_API_KEY=tu_api_key_nvidia_aqui
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
NVIDIA_MODEL=meta/llama-3.1-70b-instruct

# --- DeepSeek ---
DEEPSEEK_API_KEY=tu_api_key_deepseek_aqui
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_CODER_MODEL=deepseek-coder

# --- Proveedores por categoría ---
DEFAULT_PROVIDER=gemini
CODE_PROVIDER=deepseek
ARCHITECTURE_PROVIDER=gemini
FAST_PROVIDER=gemini_flash
DOCUMENTATION_PROVIDER=gemini

# --- Fallbacks por categoría ---
DEFAULT_FALLBACKS=nim,deepseek
CODE_FALLBACKS=nim,gemini
ARCHITECTURE_FALLBACKS=deepseek,nim
FAST_FALLBACKS=deepseek

# --- Timeouts ---
SHELL_TIMEOUT=300
DOCKER_TIMEOUT=120
LARAVEL_TIMEOUT=600

# --- Obsidian ---
OBSIDIAN_VAULT_PATH=~/Workspace/AIClient/obsidian_vault

# --- Engram (memoria persistente) ---
ENGRAM_DB_PATH=./engram_memory.db
ENGRAM_BINARY=engram
ENGRAM_ASYNC_SAVE=true
ENGRAM_AUTO_CONTEXT=true

# --- Self-Critic (auto-evaluación) ---
ENABLE_SELF_CRITIC=true

# --- Continuous Learner ---
LEARNER_BACKEND=both   # "engram", "legacy" o "both"

# --- Dashboard ---
DASHBOARD_API_KEY=tu_clave_dashboard_aqui
DASHBOARD_DEBUG=false
DASHBOARD_HOST=127.0.0.1
DASHBOARD_PORT=5000

# --- Sandbox (Docker) ---
SANDBOX_TIMEOUT=30
SANDBOX_MEMORY=128m
SANDBOX_CPU=0.5
SANDBOX_IMAGE=python:3.11-slim
EOF
    echo "✅ .env creado."
    echo "⚠️  ¡ATENCIÓN! Edita el archivo .env y añade tus claves API:"
    echo "   - GEMINI_API_KEY (obligatoria)"
    echo "   - DEEPSEEK_API_KEY (recomendada para código barato)"
    echo "   - NVIDIA_API_KEY (opcional, fallback)"
    echo "   - DASHBOARD_API_KEY (genera una aleatoria si la dejas vacía)"
else
    echo "✅ .env ya existe, omitiendo."
fi

# ================================================================
# 8. ALIAS EN WSL
# ================================================================
ALIAS_CMD="alias ai=\"$PWD/venv/bin/python $PWD/cli/ai.py\""
if grep -q "alias ai=" ~/.bashrc; then
    echo "🔄 Actualizando alias existente en ~/.bashrc..."
    sed -i "/^alias ai=/d" ~/.bashrc
fi
echo "$ALIAS_CMD" >> ~/.bashrc
echo "✅ Alias añadido a ~/.bashrc"

# ================================================================
# 9. PERMISOS DE EJECUCIÓN
# ================================================================
chmod +x cli/ai.py

# ================================================================
# 10. MENSAJE FINAL
# ================================================================
echo ""
echo "🎉 Instalación completada correctamente."
echo ""
echo "📋 Pasos siguientes:"
echo ""
echo "1. Edita el archivo .env y añade tus claves API:"
echo "   - GEMINI_API_KEY (obligatoria)"
echo "   - DEEPSEEK_API_KEY (recomendada)"
echo "   - NVIDIA_API_KEY (opcional)"
echo "   - DASHBOARD_API_KEY (genera una aleatoria si la dejas vacía)"
echo ""
echo "2. Recarga tu terminal: source ~/.bashrc"
echo ""
echo "3. Prueba el asistente: ai --help"
echo "   Verás todos los subcomandos disponibles."
echo ""
echo "4. Prueba la TUI (interfaz en terminal):"
echo "   ai --tui"
echo ""
echo "5. Prueba Engram:"
echo "   engram remember 'Hola mundo'"
echo "   engram recall 'hola'"
echo ""
echo "6. Prueba DeepSeek (si tienes API key):"
echo "   ai 'Genera una función en Python'"
echo ""
echo "7. Prueba el CLI avanzado:"
echo "   ai --status"
echo "   ai --memory 'término'"
echo "   ai --specs"
echo ""
echo "8. (Opcional) Prueba la ingesta de documentos:"
echo "   ai --ingest documento.pdf --tags 'manual'"
echo ""
echo "🪟 Para usar desde Windows, crea C:\\Windows\\System32\\ai.cmd con:"
echo "   @echo off"
echo "   setlocal enabledelayedexpansion"
echo "   set CWD=%CD%"
echo "   set CWD=%CWD:\=/%"
echo "   set CWD=%CWD:C:=/mnt/c%"
echo "   set ARGS="
echo "   :loop"
echo "   if \"%~1\"==\"\" goto :endloop"
echo "   set ARG=%~1"
echo "   set ARG=%ARG:\"=%"
echo "   set ARGS=%ARGS% \"%ARG%\""
echo "   shift"
echo "   goto loop"
echo "   :endloop"
echo "   wsl bash -ic \"cd '%CWD%' && $PWD/venv/bin/python $PWD/cli/ai.py%ARGS%\""
echo ""
echo "🧠 Engram está instalado. Documentación:"
echo "   https://github.com/Gentleman-Programming/engram"
echo ""
echo "📚 Documentación de AIClient:"
echo "   - INSTALLATION.md"
echo "   - README.md"
echo ""