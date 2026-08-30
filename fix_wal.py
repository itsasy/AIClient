import re

with open('core/execution/wal.py', 'r') as f:
    content = f.read()

content = content.replace('workflow_hash: str', 'workflow_hash: str\n    proposal_hash: str = ""\n    specification_hash: str = ""\n    graph_hash: str = ""')
content = content.replace('f"{self.transaction_id}:{self.workflow_hash}:', 'f"{self.transaction_id}:{self.proposal_hash}:{self.specification_hash}:{self.graph_hash}:{self.workflow_hash}:')

with open('core/execution/wal.py', 'w') as f:
    f.write(content)
