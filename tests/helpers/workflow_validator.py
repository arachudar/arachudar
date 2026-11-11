"""
tests/helpers/workflow_validator.py
Structural and contract validator for GitHub Actions YAML workflows.
"""

from pathlib import Path
import re
from typing import List, Dict, Any, Optional


class WorkflowValidator:
    def __init__(self, content: str):
        self.content = content

    def get_cron_schedule(self) -> Optional[str]:
        m = re.search(r"cron:\s*['\"]([^'\"]+)['\"]", self.content)
        return m.group(1) if m else None

    def get_workflow_dispatch_inputs(self) -> List[str]:
        inputs_block = re.search(r"workflow_dispatch:\s*\n\s*inputs:(.*?)(?=\n[a-zA-Z]|\Z)", self.content, re.DOTALL)
        if not inputs_block:
            return []
        return re.findall(r"^\s{6}(\w+):", inputs_block.group(1), re.MULTILINE)

    def get_secret_references(self) -> List[str]:
        return re.findall(r"secrets\.([A-Z0-9_]+)", self.content)

    def has_step_command(self, cmd: str) -> bool:
        return cmd in self.content
