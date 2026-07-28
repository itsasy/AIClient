# AIClient - Asistente Personal de Desarrollo

## Estado Actual (Fase 10)
- ✅ CLI con subcomandos (`--memory`, `--status`, `--specs`, `--ingest`, `--forget`)
- ✅ Segundo Cerebro (Obsidian + RAG híbrido)
- ✅ Memoria persistente (Engram con SQLite + FTS5)
- ✅ Skills + Agentes + Orquestador
- ✅ Multi-LLM con fallbacks inteligentes (Gemini, NIM, DeepSeek)
- ✅ SDD (Spec-Driven Development) con planificación autónoma
- ✅ Self-Critic (auto-evaluación y corrección de rumbo)
- ✅ Ingesta de documentos (PDF, DOCX, TXT, imágenes)
- ✅ Dashboard con autenticación por API Key
- ✅ Modo seguro / potente

## Uso Básico
```bash
ai "tu instrucción"                # Consulta directa
ai --chat                          # Modo chat interactivo
ai --memory "búsqueda"            # Buscar en memoria persistente
ai --status                        # Ver estadísticas del sistema
ai --specs                         # Listar especificaciones guardadas
ai --ingest documento.pdf          # Ingerir documento para la memoria
ai --forget <id>                   # Eliminar una memoria