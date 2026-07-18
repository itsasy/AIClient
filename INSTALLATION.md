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

Crea un archivo `.env` en la raíz del proyecto:

```bash
cat > .env << EOF
GEMINI_API_KEY=tu_api_key_aqui
NVIDIA_API_KEY=tu_api_key_nvidia_aqui
DEFAULT_PROVIDER=gemini
CODE_PROVIDER=nim
ARCHITECTURE_PROVIDER=nim
FALLBACK_PROVIDERS=nim,gemini
OBSIDIAN_VAULT_PATH=~/Workspace/AIClient/obsidian_vault
EOF
```

Ajusta las claves y rutas según tu configuración.

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

### B. Agregar `DOCUMENTATION_PROVIDER` en `core/config.py`

Añade esta línea después de `ARCHITECTURE_PROVIDER`:

```python
DOCUMENTATION_PROVIDER = os.getenv("DOCUMENTATION_PROVIDER", DEFAULT_PROVIDER).strip().lower()
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

**En `skills/tools/shell.py` y `skills/tools/docker.py`,** cambia el `cwd` de `subprocess.run` para que use `Config.TARGET_PROJECT_ROOT`.

### D. (Opcional) Registrar skills de proyectos

Si quieres usar `laravel_project`, regístrala en `skills/manager.py`:

```python
from skills.projects.laravel import LaravelProjectSkill
...
self.skills["laravel_project"] = LaravelProjectSkill()
```

---

## 🔗 6. Crear alias en WSL

Para ejecutar `ai` desde cualquier lugar sin activar el entorno virtual, añade al final de `~/.bashrc`:

```bash
echo 'alias ai="/home/alexis/Workspace/AIClient/venv/bin/python /home/alexis/Workspace/AIClient/cli/ai.py"' >> ~/.bashrc
source ~/.bashrc
```

> Sustituye `/home/alexis` por tu usuario real.

---

## 🪟 7. Crear script puente para Windows

Crea el archivo `C:\Windows\System32\ai.cmd` con el siguiente contenido:

```cmd
@echo off
set CWD=%CD%
wsl bash -ic "cd \"$(wslpath -u '%CWD%')\" && /home/alexis/Workspace/AIClient/venv/bin/python /home/alexis/Workspace/AIClient/cli/ai.py %*"
```

Si `wslpath` no funciona en tu sistema, usa esta alternativa:

```cmd
@echo off
set CWD=%CD:\=/%
set CWD=%CWD:C:=/mnt/c%
wsl bash -ic "cd '%CWD%' && /home/alexis/Workspace/AIClient/venv/bin/python /home/alexis/Workspace/AIClient/cli/ai.py %*"
```

---

## ✅ 8. Verificar instalación

- **Desde WSL:** `ai --help`
- **Desde PowerShell/CMD:** `ai --help`

Deberías ver la ayuda del asistente sin errores de importación.

---

## 🧪 9. Prueba de funcionamiento

```bash
ai "hola"                            # respuesta del LLM
ai "ejecuta git status"              # ejecuta git en el directorio actual
ai "crea un proyecto laravel llamado prueba"   # crea proyecto Laravel real
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
│   └── ...
├── llm/
├── skills/
├── agents/
├── obsidian/
├── venv/                 # Entorno virtual
├── .env                  # Variables de entorno
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

---

## 📬 Contacto y contribuciones

Si encuentras algún problema o deseas contribuir, abre un issue en el repositorio. ¡Disfruta de tu asistente personal! 🚀