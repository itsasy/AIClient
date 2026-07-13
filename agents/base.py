from abc import ABC, abstractmethod


class Agent(ABC):
    name: str
    role: str
    skills: tuple[str, ...] = ()

    def supports_skill(self, skill_name: str | None) -> bool:
        if skill_name is None:
            return True

        return skill_name in self.skills

    @abstractmethod
    def process(
        self,
        task: str,
        context: dict | None = None,
    ) -> str:
        raise NotImplementedError