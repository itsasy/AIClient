import logging
from typing import Any
from pathlib import Path
import subprocess
import time

from core.execution_plan import ExecutionPlan
from core.config import Config
from core.discovery.engine import DiscoveryEngine

logger = logging.getLogger(__name__)


class ValidationRunner:
    """
    Hook de validación post-generación.
    Se encarga de inspeccionar qué archivos fueron escritos/modificados
    por el LLM y correr linters/tests sobre ellos si el proyecto los tiene.
    """

    def __init__(self) -> None:
        self.root = Path(Config.TARGET_PROJECT_ROOT).expanduser().resolve()
        self.discovery = DiscoveryEngine(self.root)

    def run_post_step_validation(self, plan: ExecutionPlan) -> dict[str, Any]:
        """
        Revisa los tools ejecutados, si hubo escrituras, corre validaciones.
        """
        tools = plan.metadata.get("executed_tools", [])
        modified_files = []

        for t in tools:
            if t["name"] == "file" and t["arguments"].get("operation") == "write":
                res = t.get("result", {})
                if res.get("ok") and "result" in res:
                    rel_path = res["result"].get("path")
                    if rel_path and rel_path not in modified_files:
                        modified_files.append(rel_path)

        if not modified_files:
            return {"ok": True, "reason": "No files modified."}

        logger.info("ValidationRunner: Archivos modificados detectados: %s", modified_files)

        # Descubrir entorno
        env = self.discovery.discover()
        
        # Buscar comandos lint o format (en modo check si fuera posible)
        # Idealmente corremos el linter general o tests si lint no está
        lint_cmds = env.commands.get("lint", [])
        if not lint_cmds:
            # Fallback a ver si es un script local de lint
            return {"ok": True, "reason": "No lint command found in project."}

        cmd_to_run = lint_cmds[0].value
        logger.info("ValidationRunner: Ejecutando linter: %s", cmd_to_run)

        try:
            start = time.time()
            process = subprocess.run(
                cmd_to_run,
                shell=True,
                capture_output=True,
                text=True,
                cwd=self.root,
                timeout=60
            )
            duration = round(time.time() - start, 3)
            
            output = process.stdout.strip() or process.stderr.strip()
            
            if process.returncode == 0:
                logger.info("ValidationRunner: Linter exitoso (%ss).", duration)
                return {"ok": True, "result": "Linter passed.", "duration": duration}
            else:
                logger.warning("ValidationRunner: Linter falló. \n%s", output[:1000])
                # Guardar el error de lint para que RetryPolicy o SelfCritic lo vea
                plan.metadata["lint_error"] = output[:1500]
                return {"ok": False, "error": "Linter failed.", "output": output[:1000]}
                
        except Exception as exc:
            logger.exception("ValidationRunner falló al ejecutar linter.")
            return {"ok": False, "error": str(exc)}
