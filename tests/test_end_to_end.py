import unittest
from llm.router import LLMRouter

class EndToEndTests(unittest.TestCase):
    def test_analyze_project(self):
        skill_name, params = LLMRouter.detect_skill("Analiza este proyecto y define estándares")
        self.assertEqual(skill_name, "analyze_project")

    def test_code_generation(self):
        skill_name, params = LLMRouter.detect_skill("Genera una función Python para validar email")
        self.assertEqual(skill_name, "code")

    def test_readme(self):
        skill_name, params = LLMRouter.detect_skill("Crea un README profesional")
        self.assertEqual(skill_name, "readme")

if __name__ == "__main__":
    unittest.main()