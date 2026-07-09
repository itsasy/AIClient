import unittest

from llm.prompt_builder import PromptBuilder
from llm.router import LLMRouter


class RouterPromptBuilderTests(unittest.TestCase):
    def test_code_analysis_is_not_misclassified_as_project_analysis(self):
        skill_name, params = LLMRouter.detect_skill("analiza este código")
        self.assertIsNone(skill_name)
        self.assertIsNone(params)

    def test_code_generation_prompt_is_built_from_structured_payload(self):
        skill_result = {
            "type": "code_generation",
            "payload": {"task": "genera una clase Repository", "language": "python"},
        }

        prompt = PromptBuilder.build(
            task="genera una clase Repository",
            context={"query": "genera una clase Repository"},
            skill_name="code",
            skill_result=skill_result,
        )

        self.assertIn("Genera código para:", prompt)
        self.assertIn("genera una clase Repository", prompt)
        self.assertIn("python", prompt)


if __name__ == "__main__":
    unittest.main()
