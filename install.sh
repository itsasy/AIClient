#!/bin/bash
# AIClient - Script de instalación automatizada
# Ejecutar: chmod +x install.sh && ./install.sh

set -e  # Detenerse si hay error

echo "🚀 Iniciando instalación de AIClient..."

# 1. Verificar Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 no encontrado. Instalando..."
    sudo apt update && sudo apt install -y python3 python3-venv python3-pip
fi

# 2. Crear entorno virtual
echo "🐍 Creando entorno virtual..."
python3 -m venv venv
source venv/bin/activate

# 3. Instalar dependencias
echo "📦 Instalando dependencias..."
pip install --upgrade pip
pip install python-dotenv google-genai requests openai flask beautifulsoup4

# 4. Crear .env desde .env.example (si no existe)
if [ ! -f .env ]; then
    echo "⚙️  Creando archivo .env desde .env.example..."
    cp .env.example .env
    echo "⚠️  ¡ATENCIÓN! Edita el archivo .env y añade tus claves API."
else
    echo "✅ .env ya existe, omitiendo."
fi

# 5. Crear alias en ~/.bashrc
ALIAS_CMD="alias ai=\"$PWD/venv/bin/python $PWD/cli/ai.py\""
if grep -q "alias ai=" ~/.bashrc; then
    echo "🔄 Actualizando alias existente en ~/.bashrc..."
    sed -i "/^alias ai=/d" ~/.bashrc
fi
echo "$ALIAS_CMD" >> ~/.bashrc
echo "✅ Alias añadido a ~/.bashrc"

# 6. Dar permisos de ejecución al script principal
chmod +x cli/ai.py

# 7. Crear script puente para Windows (opcional, se indica al final)
echo ""
echo "🎉 Instalación completada correctamente."
echo ""
echo "📋 Pasos siguientes:"
echo "1. Edita el archivo .env y añade tus claves: GEMINI_API_KEY, NVIDIA_API_KEY"
echo "2. Recarga tu terminal: source ~/.bashrc"
echo "3. Prueba el asistente: ai --help"
echo ""
echo "🪟 Para usar desde Windows, crea C:\\Windows\\System32\\ai.cmd con:"
echo "   @echo off"
echo "   set CWD=%CD%"
echo "   set ARGS=%*"
echo "   set ARGS=%ARGS:\"=%"
echo "   wsl bash -ic \"cd \\\"\$(wslpath -u '%CWD%')\\\" && $PWD/venv/bin/python $PWD/cli/ai.py \\\"%ARGS%\\\"\""
echo ""

read -p "¿Instalar soporte para RAG semántico (sentence-transformers)? (s/N): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Ss]$ ]]; then
    pip install sentence-transformers numpy
    echo "✅ RAG semántico instalado."
else
    echo "ℹ️  Puedes instalarlo después con: pip install sentence-transformers numpy"
fi