# 📘 Guía de Instalación y Configuración de AIClient

**AIClient** es un asistente personal de desarrollo que integra múltiples LLMs (Gemini, NVIDIA NIM), un segundo cerebro basado en Obsidian, memoria persistente, skills y agentes, todo accesible desde la terminal. Esta guía documenta la instalación completa, requisitos y configuración utilizada para lograr su funcionamiento en **WSL (Ubuntu)** y desde **Windows (PowerShell/CMD/VS Code)**.

---

## 🧩 Requisitos previos

- **Sistema operativo:** Windows 10/11 con WSL2 habilitado.
- **Distribución WSL:** Ubuntu 22.04 o superior.
- **Python:** 3.11 o superior instalado en WSL.
- **Git:** Para clonar el repositorio.
- **Conexión a Internet:** Para descargar dependencias y acceder a las APIs de LLM.
- **Claves de API:** 
  - Gemini API Key (obligatoria)
  - NVIDIA NIM API Key (opcional, para fallback)

---

## 📦 1. Clonar el proyecto

Dentro de WSL:

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
source venv/bin/activate
```

---

## 📚 3. Instalar dependencias

Con el entorno activado (`(venv)` aparece en el prompt):

```bash
pip install --upgrade pip
pip install python-dotenv google-genai requests openai flask beautifulsoup4
```

> **Nota:** Estas son las dependencias mínimas. Si usas el dashboard o scraping, instala también `flask` y `beautifulsoup4`. Si solo usas el CLI, `flask` no es estrictamente necesario, pero se incluye para evitar errores de importación.

---

## ⚙️ 4. Configurar variables de entorno

Crea un archivo `.env` en la raíz del proyecto con el siguiente contenido (ajusta las claves y rutas):

```bash
cat > .env << EOF
GEMINI_API_KEY=tu_api_key_aqui
NVIDIA_API_KEY=tu_api_key_nvidia_aqui
DEFAULT_PROVIDER=nim
CODE_PROVIDER=nim
ARCHITECTURE_PROVIDER=nim
DOCUMENTATION_PROVIDER=nim
FALLBACK_PROVIDERS=gemini
SHELL_TIMEOUT=300
DOCKER_TIMEOUT=120
OBSIDIAN_VAULT_PATH=~/Workspace/AIClient/obsidian_vault
EOF
```

**Explicación de variables:**
- `GEMINI_API_KEY` → Clave de Google Gemini (obligatoria si usas este proveedor).
- `NVIDIA_API_KEY` → Clave de NVIDIA NIM (opcional, recomendada como fallback).
- `DEFAULT_PROVIDER` → Proveedor principal (gemini o nim).
- `CODE_PROVIDER`, `ARCHITECTURE_PROVIDER`, `DOCUMENTATION_PROVIDER` → Proveedores específicos por skill.
- `FALLBACK_PROVIDERS` → Lista de proveedores de respaldo en orden de prioridad.
- `SHELL_TIMEOUT` → Tiempo máximo (segundos) para comandos shell (recomendado: 180-300).
- `DOCKER_TIMEOUT` → Tiempo máximo (segundos) para comandos Docker (recomendado: 120).
- `OBSIDIAN_VAULT_PATH` → Ruta al vault de Obsidian (opcional).

---

## 🛠️ 5. Aplicar los parches necesarios

### A. Modificar `pyproject.toml`

Para evitar el error de "múltiples paquetes top-level", reemplaza el contenido con:

```toml
[project]
name = "aiclient"
version = "0.1.0"
description = "Cliente IA Personal - Fase 1"
requires-python = ">=3.11"
dependencies = [
    "requests",
    "python-dotenv",
    "google-genai>=2.10.0",
]

[dependency-groups]
dev = [
    "black",
    "ruff",
    "ipykernel",
]

[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[tool.setuptools]
packages = ["cli", "core", "llm", "skills", "agents", "obsidian", "dashboard"]
```

### B. Agregar `DOCUMENTATION_PROVIDER` y `TARGET_PROJECT_ROOT` en `core/config.py`

Añade estas líneas después de `ARCHITECTURE_PROVIDER`:

```python
DOCUMENTATION_PROVIDER = os.getenv("DOCUMENTATION_PROVIDER", DEFAULT_PROVIDER).strip().lower()
SHELL_TIMEOUT = int(os.getenv("SHELL_TIMEOUT", "180"))
DOCKER_TIMEOUT = int(os.getenv("DOCKER_TIMEOUT", "120"))
```

Y declara al inicio de la clase:

```python
TARGET_PROJECT_ROOT = PROJECT_ROOT
```

### C. Hacer que el asistente respete el directorio actual del usuario

**En `cli/ai.py`,** justo después de importar `Config`, añade:

```python
Config.TARGET_PROJECT_ROOT = Path.cwd()
```

**En `core/project_inspector.py`,** cambia:

```python
root = Config.PROJECT_ROOT
```
por:
```python
root = Config.TARGET_PROJECT_ROOT
```

**En `skills/tools/shell.py` y `skills/tools/docker.py`,** cambia el `cwd` de `subprocess.run` para que use `Config.TARGET_PROJECT_ROOT` y `timeout` para que use `Config.SHELL_TIMEOUT` / `Config.DOCKER_TIMEOUT`.

### D. Ampliar extensiones de proyecto en `ProjectInspector`

En `core/project_inspector.py`, reemplaza `INCLUDED_EXTENSIONS` por:

```python
INCLUDED_EXTENSIONS = {
    ".py", ".toml", ".md",
    ".php", ".json", ".js", ".css", ".html",
    ".yml", ".yaml", ".xml", ".sh", ".env",
    ".lock", ".ini", ".vue", ".ts", ".jsx", ".tsx"
}
```

### E. Registrar skills de proyectos

Si quieres usar `laravel_project`, regístrala en `skills/manager.py`:

```python
from skills.projects.laravel import LaravelProjectSkill
...
self.skills["laravel_project"] = LaravelProjectSkill()
```

### F. (Opcional) Mejorar `LaravelProjectSkill` para eliminar directorios existentes

Reemplaza `skills/projects/laravel.py` con la versión que incluye:

```python
import shutil
from pathlib import Path

# Antes de ejecutar composer, eliminar el directorio si existe
project_path = Path.cwd() / name
if project_path.exists():
    shutil.rmtree(project_path)
```

---

## 🔗 6. Crear alias en WSL

Para ejecutar `ai` desde cualquier lugar sin activar el entorno virtual, añade al final de `~/.bashrc`:

```bash
echo 'alias ai="/home/tu_usuario/Workspace/AIClient/venv/bin/python /home/tu_usuario/Workspace/AIClient/cli/ai.py"' >> ~/.bashrc
source ~/.bashrc
```

> Sustituye `/home/tu_usuario` por tu nombre de usuario real.

---

## 🪟 7. Crear script puente para Windows (CORREGIDO)

Crea el archivo `C:\Windows\System32\ai.cmd` con el siguiente contenido (esto maneja correctamente argumentos con espacios):

```cmd
@echo off
set CWD=%CD%
set ARGS=%*
set ARGS=%ARGS:"=%
wsl bash -ic "cd \"$(wslpath -u '%CWD%')\" && /home/tu_usuario/Workspace/AIClient/venv/bin/python /home/tu_usuario/Workspace/AIClient/cli/ai.py \"%ARGS%\""
```

**Si `wslpath` no funciona en tu sistema**, usa esta alternativa:

```cmd
@echo off
set CWD=%CD:\=/%
set CWD=%CWD:C:=/mnt/c%
set ARGS=%*
set ARGS=%ARGS:"=%
wsl bash -ic "cd '%CWD%' && /home/tu_usuario/Workspace/AIClient/venv/bin/python /home/tu_usuario/Workspace/AIClient/cli/ai.py \"%ARGS%\""
```

**Nota:** Sustituye `/home/tu_usuario` por tu ruta real de WSL.

---

## ✅ 8. Verificar instalación

- **Desde WSL:** `ai --help`
- **Desde PowerShell/CMD:** `ai --help`

Deberías ver la ayuda del asistente sin errores de importación.

---

## 🧪 9. Prueba de funcionamiento

```bash
# Respuesta del LLM
ai "hola"

# Ejecutar comandos en el directorio actual (WSL o Windows)
ai "ejecuta git status"

# Crear proyecto Laravel real (se crea en el directorio actual)
ai "crea un proyecto laravel llamado prueba"
```

---

## 🗂️ Estructura final del proyecto

```
~/Workspace/AIClient/
├── cli/
│   └── ai.py
├── core/
│   ├── config.py
│   ├── orchestrator.py
│   ├── project_inspector.py
│   └── ...
├── llm/
├── skills/
│   ├── manager.py
│   ├── projects/
│   │   └── laravel.py
│   └── tools/
│       ├── shell.py
│       └── docker.py
├── agents/
├── obsidian/
├── venv/                 # Entorno virtual
├── .env                  # Variables de entorno (NO subir a Git)
├── .env.example          # Plantilla de variables (subir a Git)
├── pyproject.toml        # Configuración de paquetes
└── README.md
```

---

## 🔧 Solución de problemas comunes

| Error | Solución |
|-------|----------|
| `ModuleNotFoundError: No module named 'dotenv'` | Instala las dependencias con `pip install python-dotenv google-genai requests openai flask beautifulsoup4` |
| `Multiple top-level packages discovered` | Modifica `pyproject.toml` como se indica en el paso 5.A |
| `Command 'docker' not found` | Instala Docker Desktop y habilita la integración con WSL2 |
| `Permission denied` al ejecutar `composer` | Instala Composer en WSL con `sudo apt install composer` |
| El alias no funciona en WSL | Asegúrate de que `~/.bashrc` se haya recargado con `source ~/.bashrc` |
| Desde Windows no encuentra el comando `ai` | Verifica que `ai.cmd` esté en una carpeta del PATH (ej. `C:\Windows\System32`) |
| `echo: unexpected EOF while looking for matching` | Usa la versión corregida de `ai.cmd` que maneja correctamente las comillas |
| Proyecto Laravel falla por "directory not empty" | La skill mejorada elimina automáticamente el directorio existente, o elimina manualmente con `rm -rf nombre` |
| Timeout en comandos largos | Ajusta `SHELL_TIMEOUT` en `.env` a un valor mayor (ej. 300) |
| La consulta se trunca a la primera palabra | Verifica que `ai.cmd` use `%*` y las comillas escapadas como se indica en el paso 7 |

---

## 📦 Dependencias completas (versiones usadas)

- Python 3.12.3
- pip 24.0
- python-dotenv 1.0.1
- google-genai 2.10.0
- requests 2.31.0
- openai 1.12.0
- flask 3.0.2
- beautifulsoup4 4.12.3

---

## 📝 Notas finales

- El asistente respeta el directorio actual desde donde se ejecuta, tanto en WSL como en Windows.
- Puedes extender las skills agregando nuevas clases en `skills/` y registrándolas en `SkillManager`.
- La memoria conversacional se almacena en `.history.json` en la raíz del proyecto.
- El contexto del proyecto se construye a partir del directorio actual (`TARGET_PROJECT_ROOT`).
- Los timeouts son configurables desde `.env` sin necesidad de modificar el código.

---

## 📬 Contacto y contribuciones

Si encuentras algún problema o deseas contribuir, abre un issue en el repositorio. ¡Disfruta de tu asistente personal! 🚀