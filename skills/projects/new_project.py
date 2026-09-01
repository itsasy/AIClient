import shutil
from pathlib import Path

class NewProjectSkill:
    def execute(self, plan, step, context):
        project_name = step.params.get("project_name", "nuevo-pos")
        base_dir = Path("C:/Users/alema/Desktop/Workspace")
        source = base_dir / "pos-demo"
        target = base_dir / project_name

        if target.exists():
            return {"status": "error", "message": f"El directorio {target} ya existe."}

        shutil.copytree(source, target)
        return {
            "status": "success", 
            "target_path": str(target), 
            "message": f"Base canónica clonada exitosamente en {target}."
        }