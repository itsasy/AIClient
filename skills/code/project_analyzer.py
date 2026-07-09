from skills.base import Skill
from pathlib import Path
import os

class ProjectAnalyzerSkill(Skill):
    name = "analyze_project"
    description = "Análisis profundo de proyectos"
    
    def execute(self, project_path: str = ".", **kwargs) -> str:
        path = Path(project_path)
        if not path.exists():
            return "Ruta no encontrada."
        
        files_content = []
        important_files = ['README.md', 'pyproject.toml', 'composer.json', 'package.json', '*.py', '*.php', 'Dockerfile']
        
        for root, _, files in os.walk(path):
            for file in files:
                if any(file.endswith(ext.replace('*', '')) for ext in important_files if '*' in ext) or file in important_files:
                    filepath = Path(root) / file
                    try:
                        if filepath.stat().st_size < 50000:  # evitar archivos grandes
                            content = filepath.read_text(encoding='utf-8', errors='ignore')[:800]
                            rel_path = filepath.relative_to(path)
                            files_content.append(f"--- {rel_path} ---\n{content}\n")
                    except:
                        continue
                    if len(files_content) > 8:
                        break
            if len(files_content) > 8:
                break
        
        prompt = f"""Analiza este proyecto completo y extrae:

Estructura principal:
{os.popen(f'tree -L 2 {project_path} 2>/dev/null || echo "No tree command"').read()}

Archivos clave:
{"".join(files_content[:6])}

Tareas:
1. Identificar arquitectura y patrones usados.
2. Convenciones de código y nomenclatura.
3. Tecnologías y herramientas.
4. Estándares recomendados para reutilizar en nuevos proyectos.
5. Sugerencias de mejora.

Sé concreto y accionable."""
        return prompt
