import re

with open('core/execution/mutation_engine.py', 'r') as f:
    content = f.read()

# Modify _write_wal
content = content.replace(
    'transaction_id=context.transaction_id,\n            workflow_hash=context.workflow_hash,',
    'transaction_id=context.transaction_id,\n            workflow_hash=context.workflow_hash,\n            proposal_hash=getattr(context, "proposal_hash", ""),\n            specification_hash=getattr(context, "specification_hash", ""),\n            graph_hash=getattr(context, "graph_hash", ""),')

with open('core/execution/mutation_engine.py', 'w') as f:
    f.write(content)
