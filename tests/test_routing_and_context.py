import unittest
from unittest.mock import patch

from core.context_builder import ContextBuilder
from llm.router import LLMRouter


class RouterAndContextTests(unittest.TestCase):
    def test_detects_code_review_requests(self):
        skill_name, params = LLMRouter.detect_skill(
            "Analiza el código del módulo y dime qué cambiar"
        )
        self.assertEqual(skill_name, "analyze")
        self.assertIn("code_snippet", params)

    def test_context_builder_includes_project_snapshot(self):
        builder = ContextBuilder()
        with patch("obsidian.search.ObsidianSearch.search", return_value=[]):
            context = builder.build("analiza este proyecto")
        self.assertIn("pyproject.toml", context)
        self.assertIn("README.md", context)


if __name__ == "__main__":
    unittest.main()
