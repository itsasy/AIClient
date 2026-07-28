# 🧠 AIClient – Asistente Personal de Desarrollo

**AIClient** es un asistente de software con **memoria persistente, planificación autónoma y auto‑evaluación**. Está diseñado para acompañarte en todo el ciclo de desarrollo: desde entender el proyecto, planificar, ejecutar, hasta aprender de tus correcciones.

---

## ✨ Características principales

- 🧠 **Memoria persistente** (Engram) – guarda decisiones, preferencias, errores y contexto entre sesiones.
- 🤖 **Multi‑LLM con fallbacks** – Gemini, NVIDIA NIM, DeepSeek, con selección inteligente por tarea.
- 📄 **Ingesta de documentos** – PDF, DOCX, TXT, imágenes (con descripción por Gemini Vision).
- 📋 **SDD (Spec‑Driven Development)** – crea especificaciones formales y ejecuta planes paso a paso.
- 🔍 **Self‑Critic y auto‑corrección** – el sistema evalúa sus respuestas, detecta desviaciones y se reajusta solo.
- 🖥️ **CLI avanzado + TUI** – usa desde la terminal con comandos o en modo interactivo visual.
- 🔒 **Seguridad robusta** – modo seguro / potente, autenticación en dashboard, sandbox Docker.
- 🧪 **Pruebas de integración** – garantiza que todo funcione sin regresiones.

---

## 🚀 Instalación rápida

### Con pip (recomendado)

```bash
pip install aiclient
ai --help
```

### Desde el código fuente

```bash
git clone https://github.com/tu_usuario/aiclient
cd aiclient
pip install -e .
ai --help
```

---

## 📖 Uso básico

```bash
# Consulta directa
ai "Genera una función en Python para leer un CSV"

# Modo chat interactivo
ai --chat

# Buscar en la memoria persistente
ai --memory "proyecto laravel"

# Ver estadísticas del sistema
ai --status

# Listar especificaciones guardadas
ai --specs

# Ingerir un documento
ai --ingest manual.pdf

# Iniciar la interfaz TUI (visual)
ai --tui
```

---

## 🧩 Comandos dentro de la TUI

| Comando | Descripción |
| :--- | :--- |
| `/help` | Muestra la ayuda |
| `/memory <texto>` | Busca en la memoria |
| `/specs` | Lista especificaciones |
| `/status` | Estadísticas del sistema |
| `/ingest <archivo>` | Ingiere un documento |
| `/clear` | Limpia el historial |
| `/exit` | Sale de la TUI |

---

## 🏗️ Arquitectura

```
AIClient
├── cli/          → CLI avanzado (subcomandos + TUI)
├── core/         → Config, orquestador, memoria, ingesta, especificaciones
├── llm/          → Proveedores (Gemini, NIM, DeepSeek) y selector
├── skills/       → Capacidades (shell, docker, código, proyectos, ingesta)
├── agents/       → Agentes (Architect, Coder, Executor, Planner, SelfCritic)
├── obsidian/     → RAG híbrido (FTS5 + semántico)
├── dashboard/    → API REST con autenticación
└── tests/        → Pruebas unitarias y de integración
```

---

## 🔧 Configuración

Crea un archivo `.env` en el directorio de trabajo con:

```bash
GEMINI_API_KEY=tu_clave
DEEPSEEK_API_KEY=tu_clave
# (Opcional) NVIDIA_API_KEY=tu_clave
```

Todos los proveedores y fallbacks son configurables. Consulta `INSTALLATION.md`.

---

## 📚 Documentación completa

- [Guía de instalación detallada](INSTALLATION.md)
- [Guía de usuario](docs/USER_GUIDE.md)
- [API Reference](docs/API.md)

---

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Abre un issue o envía un pull request.

---

## 📄 Licencia

MIT
