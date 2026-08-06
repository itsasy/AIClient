from __future__ import annotations

from typing import Any

from core.execution_plan import (
    ExecutionPlan,
    ExecutionStep,
)

from skills.base import Skill


class ProposalGeneratorSkill(Skill):

    name = "generate_proposal"

    description = "Genera estructuras de propuestas " "para trabajos freelance o empleo."

    version = "2.0"

    capabilities = (
        "proposal_generation",
        "freelance_support",
    )

    def execute(
        self,
        plan: ExecutionPlan,
        step: ExecutionStep,
        context: dict[str, Any],
    ) -> dict[str, Any]:

        params = step.params or {}

        job_description = params.get(
            "job_description",
            "",
        )

        mode = params.get(
            "mode",
            "freelance",
        )

        if not job_description.strip():

            return {
                "ok": False,
                "result": None,
                "error": ("No se proporcionó " "descripción del trabajo."),
            }

        return {
            "ok": True,
            "result": {
                "type": "proposal",
                "job_description": job_description,
                "mode": mode,
            },
            "error": None,
        }
