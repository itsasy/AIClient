# 📘 Guía de Instalación y Configuración de AIClient (v1.0)

**AIClient** es un asistente personal de desarrollo con **memoria persistente**, **selección inteligente de LLMs**, **planificación autónoma (SDD)**, **auto‑evaluación (Self‑Critic)**, **ingesta de documentos e imágenes**, y una **interfaz TUI** interactiva. Esta guía cubre la instalación completa, configuración y verificación del sistema.

---

## 🧩 Requisitos previos

- **Sistema operativo:** Windows 10/11 con WSL2, Linux, o macOS.
- **Python:** 3.11 o superior.
- **Git:** Para clonar el repositorio (opcional si usas `pip`).
- **Conexión a Internet:** Para descargar dependencias y acceder a las APIs de LLM.
- **Claves de API:** 
  - Gemini API Key (obligatoria)
  - DeepSeek API Key (recomendada para código barato)
  - NVIDIA NIM API Key (opcional, para fallback)
- **Docker:** (opcional) para el sandbox aislado y proyectos con Sail.
- **Composer:** (opcional) para proyectos Laravel.

---

## 🚀 Instalación rápida (recomendada)

```bash
# Instalar desde PyPI (cuando esté publicado)
pip install aiclient

# O desde el código fuente
git clone https://github.com/tu_usuario/aiclient
cd aiclient
pip install -e .
```

---

## 📦 1. Clonar el proyecto (si no usas pip)

```bash
cd ~
mkdir -p Workspace
cd Workspace
git clone <url-del-repositorio> AIClient
cd AIClient
```

---

## 🐍 2. Crear y configurar el entorno virtual

```bash
python3 -m venv venv
source venv/bin/activate   # Linux/macOS
# o venv\Scripts\activate  # Windows
```

---

## 📚 3. Instalar dependencias base

Con el entorno activado:

```bash
pip install --upgrade pip
pip install python-dotenv google-genai requests openai flask beautifulsoup4
pip install pypdf python-docx pillow   # Para ingesta de documentos
pip install textual rich               # Para TUI y salida visual
```

> **Nota:** `textual` y `rich` son opcionales pero muy recomendados para la TUI y la salida en tablas.

---

## ⚙️ 4. Configurar variables de entorno (`.env`)

Crea un archivo `.env` en la raíz del proyecto con el siguiente contenido (ajusta las claves y rutas):

```bash
# ============================================================
# AIClient - Variables de entorno (v1.0)
# ============================================================

# --- Claves API ---
GEMINI_API_KEY=tu_api_key_aqui
DEEPSEEK_API_KEY=tu_api_key_deepseek_aqui
NVIDIA_API_KEY=tu_api_key_nvidia_aqui   # Opcional

# --- Modelos por defecto ---
GEMINI_MODEL=gemini-2.5-flash
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_CODER_MODEL=deepseek-coder
NVIDIA_MODEL=meta/llama-3.1-70b-instruct

# --- Proveedores primarios por categoría ---
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

# --- Obsidian (segundo cerebro) ---
OBSIDIAN_VAULT_PATH=~/Workspace/AIClient/obsidian_vault

# --- Engram (memoria persistente) ---
ENGRAM_DB_PATH=./engram_memory.db
ENGRAM_BINARY=engram
ENGRAM_ASYNC_SAVE=true
ENGRAM_AUTO_CONTEXT=true

# --- Self-Critic (auto-evaluación) ---
ENABLE_SELF_CRITIC=true

# --- Modo seguro / potente ---
POWER_MODE=safe   # "safe" o "powerful"

# --- Dashboard ---
DASHBOARD_API_KEY=tu_clave_dashboard_aqui  # Se genera automáticamente si se deja vacía
DASHBOARD_DEBUG=false
DASHBOARD_HOST=127.0.0.1
DASHBOARD_PORT=5000

# --- Sandbox (Docker) ---
SANDBOX_TIMEOUT=30
SANDBOX_MEMORY=128m
SANDBOX_CPU=0.5
SANDBOX_IMAGE=python:3.11-slim

# --- Gemini Vision (para imágenes) ---
GEMINI_VISION_MODEL=gemini-2.0-flash-exp

# --- Aprendizaje continuo ---
LEARNER_BACKEND=both   # "engram", "legacy", "both"
```

---

## 🛠️ 5. Instalar Engram (memoria persistente)

Engram es un binario externo que proporciona la memoria persistente. Instálalo según tu sistema:

### Con Homebrew (macOS/Linux)
```bash
brew tap gentleman-programming/tap
brew install engram
```

### Con Go (si tienes Go 1.24+)
```bash
go install github.com/Gentleman-Programming/engram/cmd/engram@latest
export PATH=$PATH:~/go/bin
```

### Descarga manual
Descarga el binario para tu sistema desde:  
[https://github.com/Gentleman-Programming/engram/releases](https://github.com/Gentleman-Programming/engram/releases)  
y colócalo en una carpeta del PATH (ej. `/usr/local/bin/`).

Verifica que esté instalado:
```bash
engram --version
```

---

## 🔗 6. Crear alias en WSL (opcional)

Para ejecutar `ai` desde cualquier lugar sin activar el entorno virtual:

```bash
echo 'alias ai="/home/tu_usuario/Workspace/AIClient/venv/bin/python /home/tu_usuario/Workspace/AIClient/cli/ai.py"' >> ~/.bashrc
source ~/.bashrc
```

---

## 🪟 7. Script puente para Windows

Crea `C:\Windows\System32\ai.cmd` con:

```cmd
@echo off
setlocal enabledelayedexpansion
set CWD=%CD%
set CWD=%CWD:\=/%
set CWD=%CWD:C:=/mnt/c%
set ARGS=
:loop
if "%~1"=="" goto :endloop
set ARG=%~1
set ARG=%ARG:"=%
set ARGS=%ARGS% "%ARG%"
shift
goto loop
:endloop
wsl bash -ic "cd '%CWD%' && /home/tu_usuario/Workspace/AIClient/venv/bin/python /home/tu_usuario/Workspace/AIClient/cli/ai.py%ARGS%"
```

---

## ✅ 8. Verificar instalación

```bash
ai --help
```

Deberías ver la ayuda con todos los subcomandos:

```
usage: ai [-h] [--chat] [--tui] [--memory ...] [--status] [--specs] [--ingest ...] [--forget ...] [query ...]
```

---

## 🧪 9. Prueba de funcionamiento

### Consulta básica
```bash
ai "Hola, ¿cómo estás?"
```

### Búsqueda en memoria
```bash
ai --memory "proyecto"
```

### Estado del sistema
```bash
ai --status
```

### Listar especificaciones
```bash
ai --specs
```

### Ingerir un documento
```bash
ai --ingest manual.pdf
ai --ingest imagen.png   # Usa Gemini Vision para describirla
```

### Modo TUI (interfaz interactiva)
```bash
ai --tui
```

### Modo chat interactivo
```bash
ai --chat
```

### Crear y ejecutar una especificación (SDD)
```bash
ai "crea una spec para un sistema de tickets con autenticación JWT"
ai "ejecuta spec tickets_jwt"
```

---

## 🗂️ Estructura final del proyecto

```
~/Workspace/AIClient/
├── cli/
│   └── ai.py                   # CLI con subcomandos
├── core/
│   ├── config.py               # Configuración central
│   ├── orchestrator.py         # Orquestador principal
│   ├── engram_memory.py        # Cliente Engram
│   ├── document_ingestor.py    # Ingesta de documentos
│   ├── spec_manager.py         # Gestión de especificaciones
│   ├── learner.py              # Aprendizaje continuo
│   └── ...
├── llm/
│   ├── gemini.py
│   ├── nim.py
│   ├── deepseek.py
│   ├── provider_selector.py
│   ├── provider_manager.py
│   ├── router.py
│   └── prompt_builder.py
├── skills/
│   ├── manager.py
│   ├── knowledge/ingest.py
│   ├── projects/laravel.py
│   ├── tools/{shell,docker}.py
│   └── ...
├── agents/
│   ├── manager.py
│   ├── planner.py
│   ├── self_critic.py
│   └── ...
├── obsidian/
│   ├── index.py
│   ├── search.py
│   ├── semantic.py
│   └── rag.py
├── tui/
│   └── app.py                  # TUI con Textual
├── dashboard/
│   └── app.py                  # API REST con autenticación
├── tests/
│   └── test_integration.py
├── venv/
├── .env
├── pyproject.toml
├── README.md
└── INSTALLATION.md
```

---

## 🔧 Solución de problemas comunes

| Error | Solución |
|-------|----------|
| `ModuleNotFoundError: No module named 'textual'` | `pip install textual` |
| `Engram no disponible` | Instala Engram (paso 5) o desactiva `ENGRAM_AUTO_CONTEXT` |
| `DEEPSEEK_API_KEY no configurada` | Añade tu clave en `.env` o usa otro proveedor |
| `Docker no encontrado en sandbox` | Instala Docker o desactiva el sandbox |
| `No se puede describir imagen` | Verifica `GEMINI_API_KEY` y `GEMINI_VISION_MODEL` |
| `La TUI no arranca` | `pip install textual` y ejecuta `ai --tui` en una terminal con soporte de colores |

---

## 📦 Dependencias completas (versiones recomendadas)

- Python 3.11+
- pip 24.0+
- python-dotenv 1.0.1
- google-genai 2.10.0
- openai 1.12.0
- requests 2.31.0
- flask 3.0.2
- beautifulsoup4 4.12.3
- pypdf 5.0.0 (para PDFs)
- python-docx 1.0.0 (para DOCX)
- pillow 10.0.0 (para imágenes)
- textual 0.50+ (para TUI)
- rich 13.0+ (para salida visual)

---

## 📝 Notas finales

- **Engram** es el corazón de la memoria persistente. Sin él, AIClient funciona con memoria de sesión limitada, pero recomendamos instalarlo.
- **DeepSeek** es el proveedor más económico para código. Si no tienes clave, el sistema usará Gemini o NIM como fallback.
- **Self‑Critic** se activa automáticamente en tareas complejas. Puedes desactivarlo con `ENABLE_SELF_CRITIC=false`.
- **Modo seguro** bloquea comandos peligrosos (`sudo`, `rm -rf`). Cambia a `POWER_MODE=powerful` para desbloquearlos (bajo tu responsabilidad).
- La **TUI** es la interfaz más completa. Úsala para sesiones largas de trabajo.

---

## 📬 Contacto y contribuciones

Si encuentras algún problema o deseas contribuir, abre un issue en el repositorio. ¡Disfruta de tu asistente personal! 🚀