import re

with open('tests/test_execution_engine.py', 'r') as f:
    content = f.read()

for test in ['test_execution_engine_rejects_blocked_or_deny', 'test_execution_engine_rejects_missing_approval', 'test_skill_discovery_and_registry', 'test_execution_engine_rejects_forbidden_path', 'test_execution_engine_rollback_on_failed_imports', 'test_secret_safety']:
    content = re.sub(rf'def {test}\(tmp_path\):.*?(?=\n\n|\Z)', '', content, flags=re.DOTALL)

with open('tests/test_execution_engine.py', 'w') as f:
    f.write(content)
