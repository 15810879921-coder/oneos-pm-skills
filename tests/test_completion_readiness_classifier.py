from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "skills/yunxiao-development-delivery/scripts/classify_completion_readiness.py"
SPEC = importlib.util.spec_from_file_location("classify_completion_readiness", SCRIPT)
CLASSIFIER = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(CLASSIFIER)


def snapshot() -> dict:
    return {
        "schemaVersion": CLASSIFIER.SCHEMA,
        "developmentTask": "ONEOS-983",
        "taskResolution": "unique",
        "scopeMatch": "confirmed",
        "implementation": "complete",
        "validation": "passed",
        "remoteDelivery": "verified",
        "remoteVersion": "commit:abc123",
        "remainingTaskChanges": False,
        "knownBlockers": [],
    }


class CompletionReadinessClassifierTests(unittest.TestCase):
    def test_confirmed_completion_continues_without_second_command(self):
        value = CLASSIFIER.classify(snapshot())
        self.assertEqual(value["decision"], "confirmed")
        self.assertEqual(value["nextAction"], "auto_complete")
        self.assertIsNone(value["prompt"])

    def test_likely_completion_asks_once(self):
        value = snapshot()
        value["implementation"] = "likely"
        result = CLASSIFIER.classify(value)
        self.assertEqual(result["decision"], "likely")
        self.assertEqual(result["nextAction"], "ask_once")
        self.assertIn("是否继续执行完成开发", result["prompt"])

    def test_failed_validation_never_prompts_or_completes(self):
        value = snapshot()
        value["validation"] = "failed"
        result = CLASSIFIER.classify(value)
        self.assertEqual(result["decision"], "incomplete")
        self.assertEqual(result["nextAction"], "stop_after_submit")
        self.assertIsNone(result["prompt"])

    def test_unverified_remote_version_is_hard_block(self):
        value = snapshot()
        value["remoteDelivery"] = "pending"
        result = CLASSIFIER.classify(value)
        self.assertEqual(result["decision"], "incomplete")
        self.assertIn("远端交付版本未完成官方回读", result["reasons"])

    def test_remaining_task_changes_block_completion(self):
        value = snapshot()
        value["remainingTaskChanges"] = True
        self.assertEqual(CLASSIFIER.classify(value)["nextAction"], "stop_after_submit")


if __name__ == "__main__":
    unittest.main()
