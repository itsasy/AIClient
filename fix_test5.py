import re

with open('tests/test_execution_engine.py', 'r') as f:
    lines = f.readlines()

new_lines = []
for i, line in enumerate(lines):
    # missing_capability -> REJECTED
    if 'assert result.status == "ROLLED_BACK"' in line and 'missing_capability' in ''.join(lines[max(0,i-10):i]):
        line = '    assert result.status == "REJECTED"\n'
        
    # blocked_or_deny -> add file
    if 'result = engine.execute("db"' in line and 'blocked_or_deny' in ''.join(lines[max(0,i-10):i]):
        new_lines.insert(-1, '    (tmp_path / "modules" / "db").mkdir(parents=True, exist_ok=True)\n')
        new_lines.insert(-1, '    (tmp_path / "modules" / "db" / "service.py").write_text("code")\n')
        
    # missing_approval -> add file
    if 'result = engine.execute("auth"' in line and 'missing_approval' in ''.join(lines[max(0,i-10):i]):
        new_lines.insert(-1, '    (tmp_path / "modules" / "auth").mkdir(parents=True, exist_ok=True)\n')
        new_lines.insert(-1, '    (tmp_path / "modules" / "auth" / "service.py").write_text("code")\n')

    new_lines.append(line)

with open('tests/test_execution_engine.py', 'w') as f:
    f.writelines(new_lines)
