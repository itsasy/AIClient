from agents.base import Agent

class TaskAgent(Agent):

    name = "task"

    role = "Ejecutor"

    def process(self, task, context):

        return {
            "task": task,
            "context": context
        }