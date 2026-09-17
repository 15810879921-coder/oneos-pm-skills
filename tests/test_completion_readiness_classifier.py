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
    def test_product_handoff_gap_only_warns_and_allows_completion(self):
        value = snapshot()
        value["recoveryNeeded"] = ["formal_handoff"]
        result = CLASSIFIER.classify(value)
        self.assertEqual(result["nextAction"], "auto_complete")
        self.assertEqual(result["recoveryNeeded"], [])
        self.assertTrue(result["warnings"])

    def test_product_warning_never_waives_failed_validation(self):
        value = snapshot()
        value["recoveryNeeded"] = ["formal_handoff"]
        value["validation"] = "failed"
        result = CLASSIFIER.classify(value)
        self.assertEqual(result["nextAction"], "stop_after_submit")
        self.assertIn("开发验证失败", result["reasons"])

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

    def test_historical_delivery_candidates_enter_recovery_instead_of_dead_end(self):
        value = snapshot()
        value["remoteDelivery"] = "recoverable"
        value["remoteVersion"] = None
        value["recoveryNeeded"] = ["formal_handoff", "code_mapping", "managed_test_scope"]
        value["candidateCodeRefs"] = ["ln-one-os-web!555", "ln-cloud!53"]
        result = CLASSIFIER.classify(value)
        self.assertEqual(result["decision"], "recovery_required")
        self.assertEqual(result["nextAction"], "recover_then_complete")
        self.assertIn("2条历史代码候选", result["prompt"])
        self.assertIn("代码映射", "".join(result["reasons"]))

    def test_recoverable_delivery_requires_exact_candidates(self):
        value = snapshot()
        value["remoteDelivery"] = "recoverable"
        value["recoveryNeeded"] = ["code_mapping"]
        with self.assertRaisesRegex(ValueError, "candidateCodeRefs"):
            CLASSIFIER.classify(value)

    def test_recovery_never_overrides_failed_validation(self):
        value = snapshot()
        value["remoteDelivery"] = "recoverable"
        value["validation"] = "failed"
        value["recoveryNeeded"] = ["code_mapping"]
        value["candidateCodeRefs"] = ["ln-one-os-web!555"]
        result = CLASSIFIER.classify(value)
        self.assertEqual(result["decision"], "incomplete")
        self.assertEqual(result["nextAction"], "stop_after_submit")
        self.assertIsNone(result["prompt"])


if __name__ == "__main__":
    unittest.main()
