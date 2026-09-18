import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest


ROOT = Path(__file__).resolve().parents[1]
ROUTER_PATH = ROOT / "skills/team-task-router/scripts/router.py"


def load_router():
    spec = importlib.util.spec_from_file_location("team_task_router", ROUTER_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def capability(model, *efforts):
    return {"model": model, "efforts": list(efforts)}


def base_card(**changes):
    card = {
        "task_id": "task-1",
        "phase_id": "implementation",
        "input_revision": "input-v1",
        "rules_revision": "rules-v1",
        "scope": "oneos",
        "pattern": "frozen-local-change",
        "domain": "development",
        "kind": "implementation",
        "clarity": "clear",
        "judgment": "low",
        "impact": "local",
        "risk": "low",
        "verifiability": "testable",
        "execution_size": "normal",
        "constraints_ready": True,
        "authorized": True,
        "independent": True,
        "parent_has_work": True,
        "current": {"model": "gpt-5.6-sol", "effort": "medium"},
        "available": [
            capability("gpt-5.6-luna", "low", "medium", "high", "xhigh", "max"),
            capability("gpt-5.6-terra", "low", "medium", "high", "xhigh", "max", "ultra"),
            capability("gpt-5.6-sol", "low", "medium", "high", "xhigh", "max", "ultra"),
            capability("gpt-6-astra", "low", "medium", "high", "xhigh", "max", "ultra"),
        ],
    }
    card.update(changes)
    return card


class RouterTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.router = load_router()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="team-router-test-")
        self.state = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def call(self, command, payload, profile="local", dry_run=False):
        return self.router.execute(
            command=command,
            payload=payload,
            state_dir=self.state,
            profile=profile,
            dry_run=dry_run,
        )

    def route(self, card=None, **changes):
        return self.call("route", card or base_card(**changes))

    def start_bound(self, card=None, role=None):
        decision = self.route(card)
        run_id = f"run-{decision['task_id']}-{decision['phase_id']}"
        start_payload = {
            "task_id": decision["task_id"],
            "phase_id": decision["phase_id"],
            "input_revision": decision["input_revision"],
            "rules_revision": decision["rules_revision"],
            "scope": decision["scope"],
            "run_id": run_id,
            "execution_kind": decision["execution_kind"],
            "evidence_ref": "runtime:start",
        }
        self.call("start", start_payload)
        bind_payload = {
            "run_id": run_id,
            "actual_agent_id": "agent-1",
            "actual_session_id": "session-1",
            "model": decision["selected"]["model"],
            "effort": decision["selected"]["effort"],
            "role": role or ("reviewer" if card and card["kind"] == "review" else "executor"),
            "evidence_ref": "runtime:bind",
            "sandbox": None,
        }
        started = self.call("bind", bind_payload)
        return decision, run_id, started


class TestContractValidation(RouterTestCase):
    def test_complete_card_routes(self):
        result = self.route()
        self.assertEqual("planned", result["status"])

    def test_missing_required_field_is_error(self):
        card = base_card()
        del card["authorized"]
        with self.assertRaisesRegex(self.router.RouterError, "authorized"):
            self.route(card)

    def test_unknown_field_is_error(self):
        with self.assertRaisesRegex(self.router.RouterError, "unknown field"):
            self.route(base_card(secret_authorization=True))

    def test_invalid_model_and_unsupported_effort_are_errors(self):
        with self.assertRaisesRegex(self.router.RouterError, "unsupported model"):
            self.route(base_card(current={"model": "mystery", "effort": "low"}))
        with self.assertRaisesRegex(self.router.RouterError, "unsupported effort"):
            self.route(base_card(current={"model": "gpt-5.6-luna", "effort": "ultra"}))

    def test_duplicate_availability_is_error(self):
        card = base_card()
        card["available"].append(capability("gpt-5.6-luna", "low"))
        with self.assertRaisesRegex(self.router.RouterError, "duplicate"):
            self.route(card)

    def test_missing_estimate_remains_unknown(self):
        result = self.route(base_card(estimates={"direct_credits": None, "delegated_credits": 0.1}))
        self.assertIsNone(result["estimates"]["direct_credits"])


class TestSelection(RouterTestCase):
    def test_frozen_local_implementation_uses_luna_medium(self):
        result = self.route()
        self.assertEqual({"model": "gpt-5.6-luna", "effort": "medium"}, result["selected"])
        self.assertEqual("delegate", result["execution_kind"])

    def test_routine_judgment_uses_terra_medium(self):
        result = self.route(base_card(judgment="routine"))
        self.assertEqual({"model": "gpt-5.6-terra", "effort": "medium"}, result["selected"])

    def test_astra_max_clear_implementation_delegates_to_luna_medium(self):
        result = self.route(base_card(current={"model": "gpt-6-astra", "effort": "max"}))
        self.assertEqual({"model": "gpt-5.6-luna", "effort": "medium"}, result["selected"])
        self.assertEqual("delegate", result["execution_kind"])

    def test_astra_max_routine_judgment_delegates_to_terra_medium(self):
        result = self.route(base_card(
            current={"model": "gpt-6-astra", "effort": "max"}, judgment="routine"))
        self.assertEqual({"model": "gpt-5.6-terra", "effort": "medium"}, result["selected"])
        self.assertEqual("delegate", result["execution_kind"])

    def test_astra_max_complex_judgment_delegates_to_sol_high(self):
        result = self.route(base_card(
            current={"model": "gpt-6-astra", "effort": "max"}, judgment="complex"))
        self.assertEqual({"model": "gpt-5.6-sol", "effort": "high"}, result["selected"])
        self.assertEqual("delegate", result["execution_kind"])

    def test_new_coordination_defaults_to_sol_medium(self):
        result = self.route(base_card(domain="general", kind="coordination", judgment="routine"))
        self.assertEqual({"model": "gpt-5.6-sol", "effort": "medium"}, result["selected"])

    def test_astra_coordination_keeps_current_effort(self):
        current = {"model": "gpt-6-astra", "effort": "max"}
        result = self.route(base_card(domain="general", kind="coordination", current=current))
        self.assertEqual(current, result["desired"])
        self.assertEqual(current, result["selected"])
        self.assertEqual("self", result["execution_kind"])

    def test_high_risk_tiny_change_uses_sol_high_and_requires_review(self):
        result = self.route(base_card(execution_size="tiny", judgment="low", risk="high"))
        self.assertEqual({"model": "gpt-5.6-sol", "effort": "high"}, result["selected"])
        self.assertTrue(result["independent_review_required"])

    def test_exceptional_cross_service_high_risk_can_use_astra_high(self):
        result = self.route(base_card(judgment="exceptional", impact="cross_service", risk="high"))
        self.assertEqual({"model": "gpt-6-astra", "effort": "high"}, result["selected"])

    def test_confirmed_sol_capability_failure_can_use_astra(self):
        failure = {"model": "gpt-5.6-sol", "effort": "high", "evidence_ref": "runtime:failure"}
        result = self.route(base_card(risk="high", capability_failure=failure))
        self.assertEqual("gpt-6-astra", result["selected"]["model"])

    def test_ordinary_separate_review_uses_terra_medium(self):
        result = self.route(base_card(kind="review", judgment="routine"))
        self.assertEqual({"model": "gpt-5.6-terra", "effort": "medium"}, result["selected"])

    def test_explicit_model_choice_wins(self):
        requested = {"model": "gpt-5.6-sol", "effort": "xhigh"}
        result = self.route(base_card(requested=requested))
        self.assertEqual(requested, result["selected"])
        self.assertEqual("explicit_request", result["reason"])

    def test_explicit_model_below_high_risk_capability_floor_is_blocked(self):
        requested = {"model": "gpt-5.6-luna", "effort": "low"}
        result = self.route(base_card(requested=requested, risk="high"))
        self.assertEqual("blocked", result["status"])
        self.assertEqual("capability_floor", result["reason"])

    def test_same_model_different_effort_does_not_claim_self_switch(self):
        card = base_card(
            current={"model": "gpt-5.6-sol", "effort": "medium"},
            requested={"model": "gpt-5.6-sol", "effort": "high"},
        )
        result = self.route(card)
        self.assertEqual("planned", result["status"])
        self.assertEqual("delegate", result["execution_kind"])
        self.assertIsNone(result["actual"])
        self.assertEqual(card["requested"], result["desired"])

    def test_tiny_low_risk_work_stays_on_current_actual_pair(self):
        current = {"model": "gpt-5.6-terra", "effort": "high"}
        result = self.route(base_card(current=current, execution_size="tiny", independent=False,
                                      parent_has_work=False))
        self.assertEqual(current, result["selected"])
        self.assertEqual("self", result["execution_kind"])

    def test_estimate_aware_capable_current_model_finishes_directly(self):
        current = {"model": "gpt-5.6-sol", "effort": "medium"}
        estimates = {"direct_credits": 0.2, "delegated_credits": 0.2}
        result = self.route(base_card(current=current, estimates=estimates, judgment="routine",
                                      independent=False, parent_has_work=False))
        self.assertEqual(current, result["selected"])
        self.assertEqual("self", result["execution_kind"])
        self.assertEqual("delegation_not_cheaper", result["reason"])

    def test_delegation_requires_independent_parent_work(self):
        result = self.route(base_card(independent=False))
        self.assertEqual("blocked", result["status"])
        self.assertEqual("delegation_required_runtime_limit", result["reason"])
        self.assertIsNone(result["selected"])
        self.assertIsNone(result["execution_kind"])
        self.assertEqual({"model": "gpt-5.6-luna", "effort": "medium"}, result["desired"])

    def test_delegation_requires_parent_work(self):
        result = self.route(base_card(parent_has_work=False))
        self.assertEqual("blocked", result["status"])
        self.assertEqual("delegation_required_runtime_limit", result["reason"])
        self.assertIsNone(result["selected"])
        self.assertIsNone(result["execution_kind"])

    def test_astra_max_cannot_self_execute_normal_implementation_without_delegation(self):
        result = self.route(base_card(
            current={"model": "gpt-6-astra", "effort": "max"},
            independent=False, parent_has_work=False))
        self.assertEqual("blocked", result["status"])
        self.assertEqual("delegation_required_runtime_limit", result["reason"])
        self.assertEqual({"model": "gpt-5.6-luna", "effort": "medium"}, result["desired"])
        self.assertIsNone(result["selected"])
        self.assertIsNone(result["execution_kind"])

    def test_same_current_pair_can_still_self_execute_without_delegation(self):
        current = {"model": "gpt-5.6-luna", "effort": "medium"}
        result = self.route(base_card(
            current=current, independent=False, parent_has_work=False))
        self.assertEqual("planned", result["status"])
        self.assertEqual(current, result["selected"])
        self.assertEqual("self", result["execution_kind"])

    def test_missing_authorization_or_constraints_blocks(self):
        self.assertEqual("blocked", self.route(base_card(authorized=False))["status"])
        self.assertEqual("blocked", self.route(base_card(task_id="task-2", constraints_ready=False))["status"])

    def test_unclear_requirements_block(self):
        result = self.route(base_card(clarity="unclear"))
        self.assertEqual("requirements_unclear", result["reason"])

    def test_no_automatic_expensive_fallback(self):
        card = base_card(available=[capability("gpt-6-astra", "high")])
        result = self.route(card)
        self.assertEqual("unavailable", result["status"])
        self.assertIsNone(result["selected"])

    def test_approved_budgeted_fallback_is_allowed(self):
        fallback = {"model": "gpt-5.6-terra", "effort": "medium", "estimated_credits": 0.4}
        card = base_card(
            available=[capability("gpt-5.6-terra", "medium")],
            approved_fallbacks=[fallback],
            budget_credits=0.5,
        )
        result = self.route(card)
        self.assertEqual({"model": "gpt-5.6-terra", "effort": "medium"}, result["selected"])
        self.assertEqual("approved_fallback", result["reason"])

    def test_max_and_ultra_are_only_explicit(self):
        automatic = self.route(base_card(judgment="exceptional", impact="cross_service", risk="high"))
        explicit = self.route(base_card(task_id="task-2", requested={"model": "gpt-6-astra", "effort": "ultra"}))
        self.assertNotIn(automatic["selected"]["effort"], {"max", "ultra"})
        self.assertEqual("ultra", explicit["selected"]["effort"])


class TestPhasePersistence(RouterTestCase):
    def test_route_replay_is_idempotent_and_does_not_reset_status(self):
        card = base_card()
        first = self.route(card)
        self.call("start", {
            "task_id": "task-1", "phase_id": "implementation",
            "input_revision": "input-v1", "rules_revision": "rules-v1",
            "scope": "oneos", "run_id": "run-1", "execution_kind": "delegate",
            "evidence_ref": "runtime:start",
        })
        replay = self.route(card)
        self.assertTrue(replay["replayed"])
        self.assertEqual("dispatching", replay["phase_status"])
        self.assertEqual(first["decision_id"], replay["decision_id"])

    def test_changed_card_same_phase_key_conflicts(self):
        self.route()
        with self.assertRaisesRegex(self.router.RouterError, "conflict"):
            self.route(base_card(pattern="changed"))

    def test_dry_run_does_not_write_state(self):
        result = self.call("route", base_card(), dry_run=True)
        self.assertTrue(result["dry_run"])
        self.assertFalse(any(self.state.iterdir()))

    def test_concurrent_start_has_single_winner(self):
        self.route()
        payloads = [{
            "task_id": "task-1", "phase_id": "implementation",
            "input_revision": "input-v1", "rules_revision": "rules-v1",
            "scope": "oneos", "run_id": f"run-{index}", "execution_kind": "delegate",
            "evidence_ref": f"runtime:start:{index}",
        } for index in range(2)]
        barrier = threading.Barrier(2)
        outcomes = []

        def claim(payload):
            barrier.wait()
            try:
                outcomes.append(self.call("start", payload)["status"])
            except self.router.RouterError as exc:
                outcomes.append(exc.code)

        threads = [threading.Thread(target=claim, args=(payload,)) for payload in payloads]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(1, outcomes.count("dispatching"))
        self.assertEqual(1, outcomes.count("already_claimed"))

    def test_bind_replay_is_idempotent_and_conflict_fails(self):
        decision, run_id, _ = self.start_bound()
        payload = {
            "run_id": run_id, "actual_agent_id": "agent-1", "actual_session_id": "session-1",
            "model": decision["selected"]["model"], "effort": decision["selected"]["effort"],
            "role": "executor", "evidence_ref": "runtime:bind", "sandbox": None,
        }
        replay = self.call("bind", payload)
        self.assertTrue(replay["replayed"])
        payload["actual_session_id"] = "different"
        with self.assertRaisesRegex(self.router.RouterError, "conflicting receipt"):
            self.call("bind", payload)

    def test_bind_mismatch_remains_dispatching(self):
        decision = self.route()
        self.call("start", {
            "task_id": "task-1", "phase_id": "implementation", "input_revision": "input-v1",
            "rules_revision": "rules-v1", "scope": "oneos", "run_id": "run-1",
            "execution_kind": "delegate", "evidence_ref": "runtime:start",
        })
        result = self.call("bind", {
            "run_id": "run-1", "actual_agent_id": "agent-1", "actual_session_id": "session-1",
            "model": "gpt-5.6-sol", "effort": "medium", "role": "executor",
            "evidence_ref": "runtime:bind", "sandbox": None,
        })
        self.assertEqual("reconciliation_required", result["status"])
        self.assertEqual("dispatching", result["run_status"])
        self.assertNotEqual(decision["selected"], result["observed"])
        replay = self.call("bind", {
            "run_id": "run-1", "actual_agent_id": "agent-1", "actual_session_id": "session-1",
            "model": "gpt-5.6-sol", "effort": "medium", "role": "executor",
            "evidence_ref": "runtime:bind", "sandbox": None,
        })
        self.assertTrue(replay["replayed"])
        self.assertEqual(result["mismatch_receipt_id"], replay["mismatch_receipt_id"])
        with self.assertRaisesRegex(self.router.RouterError, "conflicting mismatch receipt"):
            self.call("bind", {
                "run_id": "run-1", "actual_agent_id": "agent-2", "actual_session_id": "session-2",
                "model": "gpt-6-astra", "effort": "high", "role": "executor",
                "evidence_ref": "runtime:other", "sandbox": None,
            })

    def test_verify_and_finish_require_bound_verified_run(self):
        _, run_id, _ = self.start_bound()
        with self.assertRaisesRegex(self.router.RouterError, "verification"):
            self.call("finish", {"run_id": run_id, "status": "completed", "evidence_ref": "runtime:finish"})
        self.call("verify", {"run_id": run_id, "evidence_ref": "runtime:verified"})
        result = self.call("finish", {"run_id": run_id, "status": "completed", "evidence_ref": "runtime:finish"})
        self.assertEqual("completed", result["status"])

    def test_unbound_dispatch_cannot_verify_or_complete(self):
        self.route()
        self.call("start", {
            "task_id": "task-1", "phase_id": "implementation", "input_revision": "input-v1",
            "rules_revision": "rules-v1", "scope": "oneos", "run_id": "run-1",
            "execution_kind": "delegate", "evidence_ref": "runtime:start",
        })
        with self.assertRaisesRegex(self.router.RouterError, "bound"):
            self.call("verify", {"run_id": "run-1", "evidence_ref": "runtime:verified"})

    def test_failed_run_requires_explicit_retry_and_preserves_runs(self):
        _, run_id, _ = self.start_bound()
        self.call("finish", {"run_id": run_id, "status": "failed", "evidence_ref": "runtime:failure"})
        retry = {
            "task_id": "task-1", "phase_id": "implementation", "input_revision": "input-v1",
            "rules_revision": "rules-v1", "scope": "oneos", "run_id": "run-2",
            "execution_kind": "delegate", "evidence_ref": "runtime:retry",
        }
        with self.assertRaisesRegex(self.router.RouterError, "retry authorization"):
            self.call("start", retry)
        retry["retry_authorized"] = True
        result = self.call("start", retry)
        self.assertEqual(2, result["attempt"])


class TestReplan(RouterTestCase):
    def replan(self, card, evidence="runtime:replan"):
        return self.call("replan", {
            "task_id": card["task_id"], "phase_id": card["phase_id"],
            "input_revision": card["input_revision"], "rules_revision": card["rules_revision"],
            "scope": card["scope"], "card": card, "evidence_ref": evidence,
        })

    def test_unavailable_phase_can_replan_after_observed_availability_change(self):
        unavailable = base_card(available=[capability("gpt-6-astra", "high")])
        self.assertEqual("unavailable", self.route(unavailable)["status"])
        updated = base_card(available=[capability("gpt-5.6-luna", "medium")])
        result = self.replan(updated)
        self.assertEqual("planned", result["status"])
        self.assertEqual({"model": "gpt-5.6-luna", "effort": "medium"}, result["selected"])
        self.assertNotEqual(result["previous_decision_id"], result["decision_id"])
        db = self.router.connect(self.state, "local")
        try:
            audit = json.loads(db.execute("SELECT payload_json FROM replan_audit WHERE replan_id=?",
                                          (result["replan_id"],)).fetchone()["payload_json"])
        finally:
            db.close()
        self.assertEqual("unavailable", audit["previous_decision"]["status"])
        self.assertIsNone(audit["previous_decision"]["selected"])
        self.assertEqual("gpt-6-astra", audit["previous_card"]["available"][0]["model"])

    def test_identical_replan_replay_is_idempotent(self):
        self.route(base_card(available=[capability("gpt-6-astra", "high")]))
        card = base_card(available=[capability("gpt-5.6-luna", "medium")])
        first = self.replan(card)
        second = self.replan(card)
        self.assertFalse(first["replayed"])
        self.assertTrue(second["replayed"])
        self.assertEqual(first["replan_id"], second["replan_id"])

    def test_replan_rejects_business_field_change(self):
        self.route()
        with self.assertRaisesRegex(self.router.RouterError, "immutable business field"):
            self.replan(base_card(pattern="different-pattern"))

    def test_replan_rejects_dispatching_running_and_completed_phase(self):
        decision = self.route()
        self.call("start", {
            "task_id": "task-1", "phase_id": "implementation", "input_revision": "input-v1",
            "rules_revision": "rules-v1", "scope": "oneos", "run_id": "run-active",
            "execution_kind": decision["execution_kind"], "evidence_ref": "runtime:start",
        })
        with self.assertRaisesRegex(self.router.RouterError, "active or completed"):
            self.replan(base_card(current={"model": "gpt-5.6-sol", "effort": "high"}))

    def test_failed_phase_replan_preserves_usage_and_still_requires_retry_authorization(self):
        decision, run_id, _ = self.start_bound()
        self.call("usage", {
            "run_id": run_id, "sample_id": "before-replan", "input_tokens": 100,
            "cached_input_tokens": 0, "output_tokens": 10, "reasoning_tokens": 0,
            "includes_child_usage": False, "rate_version": "codex-standard-2026-09-10",
            "speed_mode": "standard", "elapsed_ms": 10,
        })
        self.call("finish", {"run_id": run_id, "status": "failed", "evidence_ref": "runtime:failed"})
        updated = base_card(requested={"model": "gpt-5.6-terra", "effort": "medium"})
        self.replan(updated)
        retry = {
            "task_id": "task-1", "phase_id": "implementation", "input_revision": "input-v1",
            "rules_revision": "rules-v1", "scope": "oneos", "run_id": "run-retry",
            "execution_kind": "delegate", "evidence_ref": "runtime:retry",
        }
        with self.assertRaisesRegex(self.router.RouterError, "retry authorization"):
            self.call("start", retry)
        retry["retry_authorized"] = True
        self.assertEqual(2, self.call("start", retry)["attempt"])
        duplicate = dict(retry, run_id="run-retry-duplicate")
        with self.assertRaisesRegex(self.router.RouterError, "already claimed"):
            self.call("start", duplicate)
        summary = self.call("summary", {"scope": "oneos", "task_id": "task-1"})
        self.assertEqual("0.000800", summary["known_credits_subtotal"])


class TestMetering(RouterTestCase):
    def usage(self, **changes):
        payload = {
            "run_id": self.metered_run_id, "sample_id": "sample-1", "input_tokens": 1_000_000,
            "cached_input_tokens": 200_000, "output_tokens": 100_000,
            "reasoning_tokens": 30_000, "includes_child_usage": False,
            "rate_version": "codex-standard-2026-09-10", "speed_mode": "standard",
            "elapsed_ms": 1200,
        }
        payload.update(changes)
        return self.call("usage", payload)

    def setUp(self):
        super().setUp()
        self.metered_run_id = self.start_bound()[1]

    def test_cache_is_subtracted_and_reasoning_not_added_twice(self):
        result = self.usage()
        self.assertEqual("7.100000", result["estimated_credits"])
        self.assertEqual(100_000, result["output_tokens"])

    def test_unknown_usage_remains_unknown(self):
        result = self.usage(input_tokens=None, cached_input_tokens=None)
        self.assertIsNone(result["estimated_credits"])
        self.assertEqual(["input_tokens", "cached_input_tokens"], result["missing_fields"])

    def test_omitted_counters_remain_unknown(self):
        result = self.call("usage", {
            "run_id": self.metered_run_id, "sample_id": "omitted-counters",
            "includes_child_usage": False, "rate_version": "codex-standard-2026-09-10",
            "speed_mode": "standard",
        })
        self.assertIsNone(result["estimated_credits"])
        self.assertEqual(["input_tokens", "cached_input_tokens", "output_tokens"], result["missing_fields"])

    def test_usage_replay_is_idempotent_and_conflict_fails(self):
        self.usage()
        replay = self.usage()
        self.assertTrue(replay["replayed"])
        with self.assertRaisesRegex(self.router.RouterError, "conflicting sample"):
            self.usage(output_tokens=99, reasoning_tokens=0)

    def test_invalid_counts_and_overlapping_child_counters_fail(self):
        with self.assertRaisesRegex(self.router.RouterError, "cached"):
            self.usage(cached_input_tokens=2_000_000)
        with self.assertRaisesRegex(self.router.RouterError, "child usage"):
            self.usage(includes_child_usage=True)

    def test_unsupported_speed_returns_unknown_cost(self):
        result = self.usage(speed_mode="fast")
        self.assertIsNone(result["estimated_credits"])
        self.assertEqual("unsupported_rate_or_speed", result["cost_status"])

    def test_astra_fast_is_two_point_five_times(self):
        card = base_card(
            requested={"model": "gpt-6-astra", "effort": "high"},
            current={"model": "gpt-5.6-sol", "effort": "medium"},
            task_id="astra-task",
        )
        self.temp.cleanup()
        self.temp = tempfile.TemporaryDirectory(prefix="team-router-test-")
        self.state = Path(self.temp.name)
        self.metered_run_id = self.start_bound(card)[1]
        result = self.usage(input_tokens=1_000_000, cached_input_tokens=0, output_tokens=0,
                            reasoning_tokens=0, speed_mode="fast")
        self.assertEqual("625.000000", result["estimated_credits"])

    def test_summary_marks_total_unknown_when_coverage_missing(self):
        self.usage()
        result = self.call("summary", {"scope": "oneos", "task_id": "task-1"})
        self.assertEqual("partial", result["coverage"])
        self.assertIsNone(result["total_task_credits"])
        self.assertIsNotNone(result["known_credits_subtotal"])
        self.assertIn("coordinator", result["missing_coverage"])

    def test_coverage_complete_requires_terminal_run(self):
        with self.assertRaisesRegex(self.router.RouterError, "terminal"):
            self.usage(coverage_complete=True)

    def test_complete_sample_closes_run_to_later_samples(self):
        self.call("verify", {"run_id": self.metered_run_id, "evidence_ref": "runtime:verified"})
        self.call("finish", {"run_id": self.metered_run_id, "status": "completed", "evidence_ref": "runtime:finished"})
        result = self.usage(coverage_complete=True)
        self.assertTrue(result["coverage_complete"])
        with self.assertRaisesRegex(self.router.RouterError, "coverage already closed"):
            self.usage(sample_id="sample-after-close")

    def test_summary_total_requires_coordinator_executor_and_closed_usage(self):
        self.temp.cleanup()
        self.temp = tempfile.TemporaryDirectory(prefix="team-router-test-")
        self.state = Path(self.temp.name)
        coordinator_card = base_card(task_id="whole-task", phase_id="coordination", domain="general",
                                     kind="coordination", judgment="routine")
        _, coordinator, _ = self.start_bound(coordinator_card, role="coordinator")
        executor_card = base_card(task_id="whole-task", phase_id="implementation")
        _, executor, _ = self.start_bound(executor_card, role="executor")
        for run_id in (coordinator, executor):
            self.call("verify", {"run_id": run_id, "evidence_ref": f"runtime:verify:{run_id}"})
            self.call("finish", {"run_id": run_id, "status": "completed", "evidence_ref": f"runtime:finish:{run_id}"})
        for run_id, sample_id in ((coordinator, "coordinator-usage"), (executor, "executor-usage")):
            self.call("usage", {
                "run_id": run_id, "sample_id": sample_id, "input_tokens": 100,
                "cached_input_tokens": 0, "output_tokens": 10, "reasoning_tokens": 0,
                "includes_child_usage": False, "rate_version": "codex-standard-2026-09-10",
                "speed_mode": "standard", "coverage_complete": True,
            })
        result = self.call("summary", {"scope": "oneos", "task_id": "whole-task"})
        self.assertEqual("complete", result["coverage"])
        self.assertEqual("0.015800", result["total_task_credits"])


class TestFeedback(RouterTestCase):
    def make_task_run(self, task_id, phase_id, effort="medium"):
        card = base_card(task_id=task_id, phase_id=phase_id, domain="general", kind="mechanical",
                         verifiability="deterministic",
                         requested={"model": "gpt-5.6-luna", "effort": effort})
        return self.start_bound(card)[1]

    def feedback(self, event_id, run_id, cause="wrong_result", task_id=None, **changes):
        payload = {
            "event_id": event_id, "run_id": run_id, "evidence_ref": "user:feedback",
            "cause": cause, "source": "user", "user_correction": True,
            "accepted": False, "verified": False,
        }
        payload.update(changes)
        return self.call("feedback", payload)

    def test_feedback_uses_actual_model_and_effort(self):
        run_id = self.make_task_run("task-a", "phase-a", "low")
        result = self.feedback("event-a", run_id)
        self.assertEqual({"model": "gpt-5.6-luna", "effort": "low"}, result["actual"])

    def test_feedback_event_is_idempotent_and_conflict_fails(self):
        run_id = self.make_task_run("task-a", "phase-a")
        self.feedback("event-a", run_id)
        self.assertTrue(self.feedback("event-a", run_id)["replayed"])
        with self.assertRaisesRegex(self.router.RouterError, "conflicting feedback"):
            self.feedback("event-a", run_id, cause="preference_change")

    def test_non_user_source_cannot_mark_user_correction_or_accepted(self):
        run_id = self.make_task_run("task-a", "phase-a")
        with self.assertRaisesRegex(self.router.RouterError, "explicit user"):
            self.feedback("event-a", run_id, source="runtime")

    def test_two_independent_quality_tasks_trigger_reassessment_not_floor(self):
        first = self.make_task_run("task-a", "phase-a", "low")
        second = self.make_task_run("task-b", "phase-b", "low")
        self.feedback("event-a", first)
        result = self.feedback("event-b", second)
        self.assertTrue(result["reassessment_required"])
        history = self.call("history", {
            "scope": "oneos", "pattern": "frozen-local-change", "rules_revision": "rules-v1",
            "model": "gpt-5.6-luna", "effort": "low",
        })
        self.assertTrue(history["reassessment_required"])
        self.assertNotIn("model_floor", history)

    def test_later_acceptance_does_not_erase_earlier_quality_correction_for_task(self):
        first = self.make_task_run("task-a", "phase-a", "low")
        second = self.make_task_run("task-b", "phase-b", "low")
        self.feedback("event-a-quality", first)
        self.feedback("event-a-accepted", first, cause="preference_change",
                      user_correction=False, accepted=True)
        result = self.feedback("event-b-quality", second)
        self.assertTrue(result["reassessment_required"])

    def test_feedback_grouping_does_not_cross_effort_or_revision(self):
        low = self.make_task_run("task-low", "phase-low", "low")
        medium = self.make_task_run("task-medium", "phase-medium", "medium")
        self.feedback("event-low", low)
        result = self.feedback("event-medium", medium)
        self.assertFalse(result["reassessment_required"])
        newer = base_card(task_id="task-new", phase_id="phase-new", rules_revision="rules-v2",
                          domain="general", kind="mechanical", verifiability="deterministic",
                          requested={"model": "gpt-5.6-luna", "effort": "low"})
        new_run = self.start_bound(newer)[1]
        result = self.feedback("event-new", new_run)
        self.assertFalse(result["reassessment_required"])

    def test_requirement_and_environment_causes_do_not_count_as_quality(self):
        first = self.make_task_run("task-a", "phase-a", "low")
        second = self.make_task_run("task-b", "phase-b", "low")
        self.feedback("event-a", first, cause="requirement_change")
        result = self.feedback("event-b", second, cause="environment")
        self.assertFalse(result["reassessment_required"])


class TestCli(RouterTestCase):
    def test_installation_independent_cli_invocation(self):
        input_file = self.state / "card.json"
        input_file.write_text(json.dumps(base_card()), encoding="utf-8")
        command = [
            sys.executable, str(ROUTER_PATH), "--state-dir", str(self.state / "state"),
            "--profile", "cli", "route", "--dry-run", "--input", str(input_file),
        ]
        completed = subprocess.run(command, text=True, capture_output=True, check=False)
        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertEqual("planned", json.loads(completed.stdout)["status"])

    def test_cli_rejects_malformed_json_with_concise_stderr(self):
        completed = subprocess.run(
            [sys.executable, str(ROUTER_PATH), "route", "--input", "-"],
            input="{", text=True, capture_output=True, check=False,
        )
        self.assertEqual(2, completed.returncode)
        self.assertIn("invalid JSON", completed.stderr)
        self.assertEqual("", completed.stdout)


if __name__ == "__main__":
    unittest.main()
