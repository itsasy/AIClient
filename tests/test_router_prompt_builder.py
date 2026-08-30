import unittest
from llm.prompt_builder import PromptBuilder
from core.execution_plan import ExecutionPlan

class RouterPromptBuilderTests(unittest.TestCase):
    def test_code_generation_prompt_is_built_from_structured_payload(self):
        plan = ExecutionPlan(intent="genera una clase Repository", intent_category="code_generation", execution_unit="code", execution_unit_type="skill", steps=[])
        context = {"query": "genera una clase Repository"}
        pb = PromptBuilder()
        prompt = pb.build(plan=plan, context=context)
        # Assuming the new builder just puts the intent and context in the prompt
        self.assertIn("genera una clase Repository", prompt)

if __name__ == "__main__":
    unittest.main()
