from skills.base import Skill


class ProposalGeneratorSkill(Skill):
    name = "generate_proposal"
    description = "Genera propuestas para freelance o LinkedIn"

    def execute(self, job_description: str, mode: str = "freelance", **kwargs):
        return {
            "type": "proposal",
            "payload": {
                "job_description": job_description,
                "mode": mode,  # "freelance" o "job"
            },
        }
