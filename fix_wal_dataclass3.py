import re

with open('core/execution/wal.py', 'r') as f:
    content = f.read()

old_class = """class WALEntry:
    transaction_id: str
    workflow_hash: str
    operation_hash: str
    operation_index: int
    operation_type: str
    status: str
    proposal_hash: str = ""
    specification_hash: str = ""
    graph_hash: str = ""
    source: str = ""
    destination: str = ""
    expected_source_hash: str = ""
    expected_destination_hash: str = ""
    timestamp: float = 0.0
    previous_event_hash: str = ""
    event_hash: str = ""
"""
new_class = """class WALEntry:
    transaction_id: str
    workflow_hash: str
    operation_hash: str
    operation_index: int
    operation_type: str
    status: str
    source: str = ""
    destination: str = ""
    expected_source_hash: str = ""
    expected_destination_hash: str = ""
    timestamp: float = 0.0
    previous_event_hash: str = ""
    event_hash: str = ""
    proposal_hash: str = ""
    specification_hash: str = ""
    graph_hash: str = ""
"""

content = content.replace(old_class, new_class)

with open('core/execution/wal.py', 'w') as f:
    f.write(content)
