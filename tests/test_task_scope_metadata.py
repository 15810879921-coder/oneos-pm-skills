from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
SCRIPTS = ROOT / "skills" / "yunxiao-development-delivery" / "scripts"
sys.path.insert(0, str(SCRIPTS))
from task_scope_metadata import build_task_scope  # noqa: E402


class TaskScopeMetadataTests(unittest.TestCase):
    def test_ready_scope_keeps_explicit_values(self):
        result = build_task_scope(
            task_type="development", task_id="DEV-1", created_at="2026-09-19T01:00:00Z",
            gate_effective_at="2026-09-19T01:01:00Z", parent_task_id="DEL-1",
            parent_task_type="delivery", parent_created_at="2026-09-18T01:00:00Z",
        )
        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["task_scope"]["parent_task_id"], "DEL-1")

    def test_missing_metadata_is_explicit_and_does_not_infer(self):
        result = build_task_scope(
            task_type="development", task_id="DEV-1", created_at=None,
            gate_effective_at=None, parent_task_id="DEL-1",
            parent_task_type="delivery", parent_created_at=None,
        )
        self.assertEqual(result["status"], "metadata_missing")
        self.assertEqual(result["missing"], ["created_at", "gate_effective_at", "parent_created_at"])

    def test_test_scope_requires_parent_metadata(self):
        result = build_task_scope(
            task_type="test", task_id="TEST-1", created_at="2026-09-19T01:00:00Z",
            gate_effective_at="2026-09-19T01:01:00Z",
        )
        self.assertEqual(result["status"], "metadata_missing")
        self.assertEqual(result["missing"], ["parent_task_id", "parent_task_type", "parent_created_at"])


if __name__ == "__main__":
    unittest.main()
