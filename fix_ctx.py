import re

with open('core/execution/handlers/base.py', 'r') as f:
    content = f.read()

# Modify constructor
old_def = "def __init__(self, tx_id, session_id, wf_hash, policy_hash, app_hash, boundary_hash, skill_hash, cap_hash, sb_hash, target_root):"
new_def = "def __init__(self, tx_id, session_id, wf_hash, policy_hash, app_hash, boundary_hash, skill_hash, cap_hash, sb_hash, target_root, proposal_hash=\"\", specification_hash=\"\", graph_hash=\"\"):"

old_assign = "self.sandbox_hash = sb_hash"
new_assign = "self.sandbox_hash = sb_hash\n        self.proposal_hash = proposal_hash\n        self.specification_hash = specification_hash\n        self.graph_hash = graph_hash"

content = content.replace(old_def, new_def).replace(old_assign, new_assign)

with open('core/execution/handlers/base.py', 'w') as f:
    f.write(content)
