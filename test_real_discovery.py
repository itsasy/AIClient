import sys
from unittest.mock import MagicMock
sys.modules['dotenv'] = MagicMock()

from pathlib import Path
from core.discovery.engine import DiscoveryEngine

print("Testing Discovery on AIClient:")
root = Path("C:/Users/alema/Desktop/Workspace/AIClient")
env = DiscoveryEngine(root).discover()
print("Root:", env.root)
print("Languages:", list(env.languages.keys()))
print("Frameworks:", list(env.frameworks.keys()))
print("Test Runner:", [r.value for r in env.test_runner] if env.test_runner else "Unknown")
print("Commands:", {k: [cmd.value for cmd in v] for k, v in env.commands.items() if v})
print("Important Directories:", [d['path'] for d in env.important_directories])
