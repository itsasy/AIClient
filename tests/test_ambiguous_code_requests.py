import unittest

from llm.router import LLMRouter


class AmbiguousCodeRequestTests(unittest.TestCase):
    def test_ambiguous_code_request_does_not_route_to_analyze(self):
        skill_name, params = LLMRouter.detect_skill("analiza este código")
        self.assertIsNone(skill_name)
        self.assertIsNone(params)

    def test_explicit_code_request_routes_to_analyze(self):
        skill_name, params = LLMRouter.detect_skill("analiza este código: def foo(): return 1")
        self.assertEqual(skill_name, "analyze")
        self.assertIn("code_snippet", params)


if __name__ == "__main__":
    unittest.main()
