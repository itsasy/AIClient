from __future__ import annotations

from typing import Any

from core.execution_plan import ExecutionPlan
from core.execution_step import ExecutionStep

from skills.base import Skill


class ProposalGeneratorSkill(Skill):

    name = "generate_proposal"

    description = "Genera propuestas para freelance o LinkedIn."

    version = "2.0"

    capabilities = (
        "proposal_generation",
        "freelance_assistance",
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

        if not job_description:

            return {
                "ok": False,
                "result": None,
                "error": "No se proporcionó descripción del trabajo.",
            }

        return {
            "ok": True,
            "result": {
                "type": "proposal",
                "payload": {
                    "job_description": job_description,
                    "mode": mode,
                },
            },
            "error": None,
        }
