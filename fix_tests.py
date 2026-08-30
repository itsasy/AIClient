import re

with open('c:/Users/alema/Desktop/Workspace/AIClient/tests/test_transformation_candidates.py', 'r') as f:
    content = f.read()

content = content.replace(
    'prop = TransformationProposal(project_id="test", requirements=reqs, proposal_hash="phash")',
    'prop = TransformationProposal(proposal_id="p1", intent="test", objective="test", requirements=reqs)\n    prop.proposal_hash = "phash"'
)

with open('c:/Users/alema/Desktop/Workspace/AIClient/tests/test_transformation_candidates.py', 'w') as f:
    f.write(content)
