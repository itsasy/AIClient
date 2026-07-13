import unittest
from unittest.mock import patch

from core.context_builder import ContextBuilder
from llm.prompt_builder import PromptBuilder
from llm.router import LLMRouter

class RouterAndContextTests(unittest.TestCase):
    def test_detects_code_review_requests(self):
        skill_name, params = LLMRouter.detect_skill(
            "Analiza el código del módulo y dime qué cambiar"
        )
        self.assertEqual(skill_name, "analyze")
        self.assertIn("code_snippet", params)

    def test_detects_problem_analysis_requests(self):
        skill_name, params = LLMRouter.detect_skill(
            "Analiza problemas comunes en mi código actual"
        )
        self.assertEqual(skill_name, "analyze_project")
        self.assertEqual(params, {})

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

    def test_detect_project_analysis_from_current_code():
        skill_name, params = LLMRouter.detect_skill(
            "Analiza problemas comunes en mi código actual"
        )

        assert skill_name == "analyze_project"
        assert params == {}


    def test_detect_project_analysis():
        skill_name, params = LLMRouter.detect_skill(
            "Analiza este proyecto y define los estándares"
        )

        assert skill_name == "analyze_project"
        assert params == {}


    def test_detect_explicit_code_analysis():
        query = "Analiza este código: def suma(a, b): return a + b"

        skill_name, params = LLMRouter.detect_skill(query)

        assert skill_name == "analyze"
        assert params == {
            "code_snippet": query,
        }


    def test_detect_project_generation():
        query = "Crea un nuevo proyecto Python con estructura estándar"

        skill_name, params = LLMRouter.detect_skill(query)

        assert skill_name == "code"
        assert params == {
            "task": query,
        }


    def test_detect_readme_generation():
        query = "Crea un README profesional para AIClient"

        skill_name, params = LLMRouter.detect_skill(query)

        assert skill_name == "readme"
        assert params == {
            "project_name": query,
        }


    def test_general_question_has_no_skill():
        skill_name, params = LLMRouter.detect_skill(
            "¿Qué es Domain-Driven Design?"
        )

        assert skill_name is None
        assert params is None


    def test_project_prompt_prevents_false_absence_claims():
        skill_result = {
            "type": "project_analysis",
            "payload": "Snapshot parcial del proyecto",
        }

        prompt = PromptBuilder.build(
            task="Analiza mi proyecto",
            context={},
            skill_name="analyze_project",
            skill_result=skill_result,
        )

        assert "no existe" in prompt.lower()
        assert "no fue inspeccionado" in prompt.lower()
        assert "no se pudo verificar" in prompt.lower()


    def test_readme_prompt_prevents_invented_information():
        skill_result = {
            "type": "readme",
            "payload": {
                "requested_name": "AIClient",
                "description": "",
                "snapshot": "Proyecto: AIClient",
            },
        }

        prompt = PromptBuilder.build(
            task="Crea un README profesional para AIClient",
            context={},
            skill_name="readme",
            skill_result=skill_result,
        )

        assert "no inventes repositorios ni urls" in prompt.lower()
        assert "no inventes versiones" in prompt.lower()
        assert "no inventes licencias" in prompt.lower()
        assert "placeholders" in prompt.lower()

if __name__ == "__main__":
    unittest.main()
