"""Black-box CLI checks using synthetic receipts, never real model invocations."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "skills/team-task-router/scripts/router.py"


def card(phase="execution"):
    return {
        "task_id": "synthetic-cli-task", "phase_id": phase, "input_revision": "1",
        "rules_revision": "2.0.0", "scope": "synthetic", "pattern": "batch-labels",
        "domain": "general", "kind": "mechanical", "clarity": "clear",
        "judgment": "low", "impact": "local", "risk": "low",
        "verifiability": "deterministic", "execution_size": "normal",
        "constraints_ready": True, "authorized": True, "independent": True,
        "parent_has_work": True, "current": {"model": "gpt-5.6-sol", "effort": "medium"},
        "available": [{"model": "gpt-5.6-sol", "efforts": ["medium", "high"]},
                      {"model": "gpt-5.6-luna", "efforts": ["low", "medium"]}],
    }


class CliIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.state = Path(self.temp.name) / "state"

    def call(self, command, payload, *, ok=True, dry=False):
        args = [sys.executable, str(SCRIPT), "--state-dir", str(self.state),
                "--profile", "synthetic", command, "--input", "-"]
        if dry:
            args.append("--dry-run")
        result = subprocess.run(args, input=json.dumps(payload), text=True,
                                capture_output=True, timeout=15)
        if not ok:
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn("Traceback", result.stderr)
            return result.stderr
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def run_phase(self, decision_card, run_id, role):
        decision = self.call("route", decision_card)
        key = {name: decision_card[name] for name in
               ("scope", "task_id", "phase_id", "input_revision", "rules_revision")}
        self.call("start", {**key, "run_id": run_id,
                            "execution_kind": decision["execution_kind"],
                            "evidence_ref": "synthetic:intent"})
        pair = decision["selected"]
        self.call("bind", {"run_id": run_id, "actual_agent_id": "synthetic-" + run_id,
                           "actual_session_id": "synthetic-session-" + run_id,
                           **pair, "role": role, "sandbox": None,
                           "evidence_ref": "synthetic:receipt"})
        self.call("verify", {"run_id": run_id, "evidence_ref": "synthetic:check"})
        self.call("finish", {"run_id": run_id, "status": "completed",
                             "evidence_ref": "synthetic:completed"})
        return key

    def usage(self, run_id, input_tokens, cached, output_tokens, complete=True):
        return {"run_id": run_id, "sample_id": "source-event-" + run_id,
                "input_tokens": input_tokens, "cached_input_tokens": cached,
                "output_tokens": output_tokens, "reasoning_tokens": None,
                "includes_child_usage": False, "rate_version": "codex-standard-2026-09-10",
                "speed_mode": "standard", "elapsed_ms": None,
                "coverage_complete": complete}

    def test_dry_run_does_not_create_state(self):
        decision_card = card()
        decision_card["execution_size"] = "tiny"
        result = self.call("route", decision_card, dry=True)
        self.assertEqual(result["execution_kind"], "self")
        self.assertEqual(result["selected"], decision_card["current"])
        self.assertFalse(self.state.exists())

    def test_runtime_limit_blocks_astra_self_fallback_for_normal_implementation(self):
        decision_card = card()
        decision_card["kind"] = "implementation"
        decision_card["verifiability"] = "testable"
        decision_card["current"] = {"model": "gpt-6-astra", "effort": "max"}
        decision_card["available"] = [
            {"model": "gpt-6-astra", "efforts": ["max"]},
            {"model": "gpt-5.6-luna", "efforts": ["medium"]},
        ]
        decision_card["parent_has_work"] = False
        result = self.call("route", decision_card)
        self.assertEqual("blocked", result["status"])
        self.assertEqual("delegation_required_runtime_limit", result["reason"])
        self.assertEqual({"model": "gpt-5.6-luna", "effort": "medium"}, result["desired"])
        self.assertIsNone(result["selected"])
        self.assertIsNone(result["execution_kind"])

    def test_complete_path_cost_and_replay(self):
        coordinator = card("coordination")
        coordinator["kind"] = "coordination"
        self.run_phase(coordinator, "parent", "coordinator")
        self.call("usage", self.usage("parent", 1000, 0, 100))
        key = self.run_phase(card(), "child", "executor")
        payload = self.usage("child", 2000, 1000, 100)
        self.call("usage", payload)
        self.assertTrue(self.call("usage", payload)["replayed"])
        result = self.call("summary", {"scope": "synthetic", "task_id": "synthetic-cli-task"})
        self.assertEqual(result["total_task_credits"], "0.158500")
        self.assertEqual(result["coverage"], "complete")
        self.assertIsNone(result["savings_percentage"])
        self.call("start", {**key, "run_id": "duplicate", "execution_kind": "delegate",
                            "retry_authorized": True, "evidence_ref": "synthetic:duplicate"}, ok=False)
        second = dict(payload, sample_id="changed-id")
        self.call("usage", second, ok=False)

    def test_unsealed_usage_keeps_total_unknown(self):
        coordinator = card("coordination")
        coordinator["kind"] = "coordination"
        self.run_phase(coordinator, "parent", "coordinator")
        self.call("usage", self.usage("parent", 1000, 0, 100, complete=False))
        result = self.call("summary", {"scope": "synthetic", "task_id": "synthetic-cli-task"})
        self.assertIsNone(result["total_task_credits"])
        self.assertEqual(result["known_credits_subtotal"], "0.150000")

    def test_unavailable_recovers_without_fake_business_revision(self):
        original = card()
        original["available"] = [{"model": "gpt-6-astra", "efforts": ["high"]}]
        self.assertEqual(self.call("route", original)["status"], "unavailable")
        updated = card()
        key = {name: original[name] for name in
               ("scope", "task_id", "phase_id", "input_revision", "rules_revision")}
        payload = {**key, "card": updated, "evidence_ref": "synthetic:availability-restored"}
        result = self.call("replan", payload)
        self.assertEqual(result["selected"], {"model": "gpt-5.6-luna", "effort": "low"})
        self.assertEqual(result["input_revision"], "1")
        self.assertTrue(self.call("replan", payload)["replayed"])
        replay = self.call("route", updated)
        self.assertEqual(replay["decision_id"], result["decision_id"])
        changed = copy.deepcopy(payload)
        changed["card"]["risk"] = "high"
        changed["evidence_ref"] = "synthetic:forbidden-business-mutation"
        self.call("replan", changed, ok=False)


if __name__ == "__main__":
    unittest.main()
