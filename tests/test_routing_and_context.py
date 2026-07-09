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

    def test_detects_readme_and_project_requests(self):
        readme_skill, _ = LLMRouter.detect_skill("crea un README para este proyecto")
        project_skill, _ = LLMRouter.detect_skill("analiza este proyecto")
        code_skill, _ = LLMRouter.detect_skill("genera una función en Python")

        self.assertEqual(readme_skill, "readme")
        self.assertEqual(project_skill, "analyze_project")
        self.assertEqual(code_skill, "code")

    def test_does_not_trigger_readme_for_unrelated_queries(self):
        skill_name, _ = LLMRouter.detect_skill("git status")
        self.assertIsNone(skill_name)

    def test_context_builder_includes_project_snapshot(self):
        builder = ContextBuilder()
        with patch("obsidian.search.ObsidianSearch.search", return_value=[]):
            context = builder.build("analiza este proyecto")
        self.assertIn("pyproject.toml", context)
        self.assertIn("README.md", context)

    def test_context_builder_skips_project_snapshot_for_trivial_queries(self):
        builder = ContextBuilder()
        with patch.object(builder, "build_project_snapshot", return_value="snapshot") as mock_snapshot:
            with patch("obsidian.search.ObsidianSearch.search", return_value=[]):
                builder.build("git status")
        mock_snapshot.assert_not_called()

    def test_router_accepts_default_context(self):
        with patch("llm.router.LLMRouter._provider") as provider_mock:
            provider_instance = provider_mock.return_value
            provider_instance.generate.return_value = "ok"

            result = LLMRouter.generate(task="hola")

        self.assertEqual(result, "ok")


if __name__ == "__main__":
    unittest.main()
