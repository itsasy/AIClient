#!/bin/bash
# AIClient - Script de instalación automatizada (con Engram + DeepSeek + Self-Critic)
# Ejecutar: chmod +x install.sh && ./install.sh

set -e  # Detenerse si hay error

echo "🚀 Iniciando instalación de AIClient (con Engram + DeepSeek)..."

# ============================================================
# 1. PYTHON + ENTORNO VIRTUAL
# ============================================================
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

# ============================================================
# 2. RAG SEMÁNTICO (OPCIONAL)
# ============================================================
echo ""
read -p "¿Instalar soporte para RAG semántico (sentence-transformers)? (s/N): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Ss]$ ]]; then
    pip install sentence-transformers numpy
    echo "✅ RAG semántico instalado."
else
    echo "ℹ️  Puedes instalarlo después con: pip install sentence-transformers numpy"
fi

# ============================================================
# 3. ENGRAM (MEMORIA PERSISTENTE)
# ============================================================
echo ""
echo "🧠 Instalando Engram (memoria persistente)..."

# 3a. Verificar si Engram ya está instalado
if command -v engram &> /dev/null; then
    echo "✅ Engram ya está instalado: $(which engram)"
else
    # 3b. Intentar con Homebrew (recomendado)
    if command -v brew &> /dev/null; then
        echo "🍺 Instalando Engram con Homebrew..."
        brew tap gentleman-programming/tap
        brew install engram
        echo "✅ Engram instalado con Homebrew."
    else
        # 3c. Intentar con Go (requiere Go 1.24+)
        if command -v go &> /dev/null; then
            GO_VERSION=$(go version | grep -oP 'go\K[0-9.]+' | cut -d. -f1,2)
            if [[ $(echo "$GO_VERSION >= 1.24" | bc) -eq 1 ]]; then
                echo "🐹 Instalando Engram desde código fuente (Go $GO_VERSION)..."
                go install github.com/Gentleman-Programming/engram/cmd/engram@latest
                # Asegurar que ~/go/bin esté en el PATH
                export PATH=$PATH:~/go/bin
                echo 'export PATH=$PATH:~/go/bin' >> ~/.bashrc
                echo "✅ Engram instalado desde código fuente."
            else
                echo "⚠️  Versión de Go ($GO_VERSION) es antigua. Se necesita Go 1.24+."
                echo "   Instala Go desde: https://go.dev/dl/"
                echo "   Luego ejecuta: go install github.com/Gentleman-Programming/engram/cmd/engram@latest"
            fi
        else
            # 3d. Fallback: instrucciones manuales
            echo "⚠️  No se encontró Homebrew ni Go."
            echo "   Instala Engram manualmente desde:"
            echo "   https://github.com/Gentleman-Programming/engram/releases"
            echo "   Descarga el binario para Linux y colócalo en /usr/local/bin/"
        fi
    fi
fi

# ============================================================
# 4. CONFIGURACIÓN DE ENTORNO (.env)
# ============================================================
if [ ! -f .env ]; then
    echo "⚙️  Creando archivo .env desde plantilla..."
    cat > .env << 'EOF'
# ============================================================
# AIClient - Variables de entorno
# ============================================================

# --- Gemini ---
GEMINI_API_KEY=tu_api_key_aqui
GEMINI_MODEL=gemini-2.5-flash

# --- NVIDIA NIM ---
NVIDIA_API_KEY=tu_api_key_nvidia_aqui
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
NVIDIA_MODEL=meta/llama-3.1-70b-instruct

# --- DeepSeek (NUEVO) ---
DEEPSEEK_API_KEY=tu_api_key_deepseek_aqui
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_CODER_MODEL=deepseek-coder

# --- Proveedores por categoría ---
DEFAULT_PROVIDER=gemini
CODE_PROVIDER=deepseek
ARCHITECTURE_PROVIDER=gemini
FAST_PROVIDER=gemini_flash

# --- Fallbacks por categoría (orden de prioridad) ---
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

# --- Engram (NUEVO) ---
ENGRAM_DB_PATH=./engram_memory.db
ENGRAM_BINARY=engram
ENGRAM_ASYNC_SAVE=true
ENGRAM_AUTO_CONTEXT=true

# --- Self-Critic (NUEVO) ---
ENABLE_SELF_CRITIC=true

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
    echo "   - GEMINI_API_KEY"
    echo "   - DEEPSEEK_API_KEY"
    echo "   - NVIDIA_API_KEY (opcional)"
else
    echo "✅ .env ya existe, omitiendo."
fi

# ============================================================
# 5. ALIAS EN WSL
# ============================================================
ALIAS_CMD="alias ai=\"$PWD/venv/bin/python $PWD/cli/ai.py\""
if grep -q "alias ai=" ~/.bashrc; then
    echo "🔄 Actualizando alias existente en ~/.bashrc..."
    sed -i "/^alias ai=/d" ~/.bashrc
fi
echo "$ALIAS_CMD" >> ~/.bashrc
echo "✅ Alias añadido a ~/.bashrc"

# ============================================================
# 6. PERMISOS DE EJECUCIÓN
# ============================================================
chmod +x cli/ai.py

# ============================================================
# 7. MENSAJE FINAL
# ============================================================
echo ""
echo "🎉 Instalación completada correctamente."
echo ""
echo "📋 Pasos siguientes:"
echo ""
echo "1. Edita el archivo .env y añade tus claves API:"
echo "   - GEMINI_API_KEY (obligatoria)"
echo "   - DEEPSEEK_API_KEY (recomendada para código barato)"
echo "   - NVIDIA_API_KEY (opcional, fallback)"
echo "   - DASHBOARD_API_KEY (genera una aleatoria si la dejas vacía)"
echo ""
echo "2. Recarga tu terminal: source ~/.bashrc"
echo ""
echo "3. Prueba el asistente: ai --help"
echo ""
echo "4. Prueba Engram:"
echo "   engram remember 'Hola mundo'"
echo "   engram recall 'hola'"
echo ""
echo "5. Prueba DeepSeek (si tienes API key):"
echo "   ai 'Genera una función en Python' --provider deepseek"
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
echo "🧠 Engram está instalado. Consulta la documentación en:"
echo "   https://github.com/Gentleman-Programming/engram"