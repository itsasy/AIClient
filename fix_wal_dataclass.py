import re

with open('core/execution/wal.py', 'r') as f:
    content = f.read()

old = 'workflow_hash: str\n    proposal_hash: str = ""\n    specification_hash: str = ""\n    graph_hash: str = ""\n    operation_hash: str'
new = 'workflow_hash: str\n    operation_hash: str\n    proposal_hash: str = ""\n    specification_hash: str = ""\n    graph_hash: str = ""'

content = content.replace(old, new)

with open('core/execution/wal.py', 'w') as f:
    f.write(content)
