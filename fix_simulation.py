import re

with open('core/execution/simulation.py', 'r') as f:
    content = f.read()

# Add to SimulationResult
content = content.replace('skill_selection_hash: str = ""', 'skill_selection_hash: str = ""\n    specification_hash: str = ""\n    graph_hash: str = ""')

# Add to hash payload
content = content.replace('"skill_selection_hash": self.skill_selection_hash,', '"skill_selection_hash": self.skill_selection_hash,\n            "specification_hash": self.specification_hash,\n            "graph_hash": self.graph_hash,')

with open('core/execution/simulation.py', 'w') as f:
    f.write(content)
