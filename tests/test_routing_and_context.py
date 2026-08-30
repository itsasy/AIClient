import unittest
from core.context.manager import ContextManager

class ContextManagerTests(unittest.TestCase):
    def test_context_manager_builds_empty_context_when_no_plan(self):
        manager = ContextManager()
        context = manager.build(plan=None)
        self.assertIn("execution", context)
        self.assertIsNone(context["execution"].get("plan_id"))

if __name__ == "__main__":
    unittest.main()
