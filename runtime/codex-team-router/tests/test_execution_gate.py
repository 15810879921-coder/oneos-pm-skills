import importlib.util
import json
from pathlib import Path
import shlex
import sqlite3
import sys
import tempfile
import time
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / "skills/team-task-router/scripts"
sys.path.insert(0, str(SCRIPTS))
import execution_gate as eg


class GateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name)
        (self.home / "agents").mkdir()
        for name, pair in eg.ROLE_PAIRS.items():
            (self.home / "agents" / (name + ".toml")).write_text(
                f'name = "{name}"\nmodel = "{pair[0]}"\nmodel_reasoning_effort = "{pair[1]}"\n')
        self.rootlog = self.log("root", "turn", "gpt-6-astra", "max")
        db = sqlite3.connect(self.home / "state_5.sqlite")
        db.execute("CREATE TABLE threads(id TEXT,rollout_path TEXT,source TEXT,agent_path TEXT,created_at INTEGER)")
        db.execute("INSERT INTO threads VALUES(?,?,?,?,?)", ("root", str(self.rootlog), '"vscode"', None, int(time.time())))
        db.commit()
        db.close()
        self.gate = eg.Gate(self.home)
        self.gate.hook(self.payload("UserPromptSubmit"))

    def tearDown(self):
        self.gate.db.close()
        self.temp.cleanup()

    def log(self, thread, turn, model, effort, parent=None, task_metadata=None):
        p = self.home / (thread + ".jsonl")
        source = {"subagent": {"thread_spawn": {"parent_thread_id": parent}}} if parent else "vscode"
        task_metadata = task_metadata or {"kind": "requirement", "created_at": "2026-09-17T00:00:00+08:00", "parent_task_id": None, "parent_type": None}
        rows = [{"type": "session_meta", "payload": {"id": thread, "session_id": "root", "source": source, "task_metadata": task_metadata}},
                {"type": "turn_context", "payload": {"turn_id": turn, "model": model, "effort": effort}}]
        p.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
        return p

    def payload(self, event="PreToolUse", **changes):
        p = dict(session_id="root", turn_id="turn", transcript_path=str(self.rootlog),
                 model="gpt-6-astra", cwd=str(self.home), hook_event_name=event,
                 tool_name="Bash", tool_use_id="call-1", tool_input={"command": "touch should-not-run"},
                 task_metadata={"kind": "development", "created_at": "2026-09-18T01:00:00+08:00", "parent_task_id": "root", "parent_type": "requirement"})
        p.update(changes)
        return p

    def assess(self, **changes):
        r = dict(domain="development", kind="implementation", clarity="clear", judgment="low", impact="local",
                 risk="low", verifiability="testable", execution_size="normal", constraints_ready=True,
                 authorized=True, independent=True, parent_work="independently verify input contract",
                 reason="implement the frozen parser", available_roles=list(eg.ROLE_PAIRS))
        r.update(changes)
        return self.gate.assess("root", "turn", r)

    def denied(self, output):
        return output.get("hookSpecificOutput", {}).get("permissionDecision") == "deny"

    def spawn(self, **changes):
        s = self.gate.load("root", "turn")
        args = dict(agent_type=s["selected_role"], task_name=s["task_name"], fork_turns="none", message="scoped task")
        args.update(changes)
        return self.payload(tool_name="spawn_agent", tool_input=args)

    def child_receipt(self, model="gpt-5.6-luna", effort="medium", parent="root"):
        s = self.gate.load("root", "turn")
        path = "/root/" + s["task_name"]
        log = self.log("child", "child-turn", model, effort, parent)
        db = sqlite3.connect(self.home / "state_5.sqlite")
        source = {"subagent": {"thread_spawn": {"parent_thread_id": parent}}}
        db.execute("INSERT INTO threads VALUES(?,?,?,?,?)", ("child", str(log), json.dumps(source), path, int(time.time())))
        db.commit()
        db.close()
        return {"agent_id": "child", "task_name": path}

    def test_unassessed_tool_is_denied(self):
        self.assertTrue(self.denied(self.gate.hook(self.payload())))

    def test_bootstrap_single_cli_is_allowed_but_chained_shell_is_not(self):
        cmd = f"{shlex.quote(sys.executable)} {shlex.quote(str(eg.SCRIPT))} describe"
        self.assertEqual({}, self.gate.hook(self.payload(tool_input={"command": cmd})))
        for suffix in ("; touch x", " && touch x", " | sh", " $(touch x)"):
            self.assertTrue(self.denied(self.gate.hook(self.payload(tool_input={"command": cmd + suffix}))))

    def test_assessment_requires_exact_current_turn_not_old_context(self):
        with self.rootlog.open("a") as f:
            f.write(json.dumps({"type": "turn_context", "payload": {"turn_id": "other", "model": "gpt-5.6-sol", "effort": "high"}}) + "\n")
        self.gate.hook(self.payload("UserPromptSubmit", turn_id="new"))
        with self.assertRaisesRegex(ValueError, "context unavailable"):
            self.gate.assess("root", "new", eg.describe()["assessment"])

    def test_uninstalled_or_changed_role_is_rejected(self):
        (self.home / "agents/team_luna_executor.toml").write_text('name="team_luna_executor"\nmodel="gpt-6-astra"\nmodel_reasoning_effort="max"\n')
        with self.assertRaisesRegex(ValueError, "role unavailable or changed"):
            self.assess()

    def test_clear_astra_execution_requires_luna_and_real_receipt(self):
        result = self.assess()
        self.assertEqual("team_luna_executor", result["selected_role"])
        self.assertIsNone(result["actual"])
        self.assertTrue(self.denied(self.gate.hook(self.payload())))

    def test_missing_independent_parent_work_blocks_instead_of_fallback(self):
        result = self.assess(parent_work="")
        self.assertEqual("blocked", result["status"])
        self.assertIsNone(result["decision"]["selected"])
        self.assertTrue(self.denied(self.gate.hook(self.payload())))

    def test_wrong_role_or_full_history_fork_is_denied(self):
        self.assess()
        for changes in ({"agent_type": "team_astra_expert"}, {"fork_turns": "all"}, {"model": "gpt-6-astra"}, {"task_name": "old"}):
            self.assertTrue(self.denied(self.gate.hook(self.spawn(**changes))))

    def test_call_without_native_id_does_not_start(self):
        self.assess()
        p = self.spawn()
        p.pop("tool_use_id")
        self.assertTrue(self.denied(self.gate.hook(p)))
        self.assertIsNone(self.gate.load("root", "turn").get("pending"))

    def test_dispatch_without_native_completion_receipt_is_not_proof(self):
        self.assess()
        self.assertEqual({}, self.gate.hook(self.spawn()))
        self.child_receipt()
        self.assertTrue(self.denied(self.gate.hook(self.payload())))
        self.assertIsNone(self.gate.load("root", "turn")["actual"])

    def test_actual_native_child_model_unlocks_parent_work(self):
        self.assess()
        self.gate.hook(self.spawn())
        receipt = self.child_receipt()
        self.gate.hook(self.payload("PostToolUse", tool_name="spawn_agent", tool_response=json.dumps(receipt)))
        self.assertEqual({}, self.gate.hook(self.payload()))
        state = self.gate.load("root", "turn")
        self.assertEqual("gpt-5.6-luna", state["actual"]["model"])
        self.assertEqual("medium", state["actual"]["effort"])
        self.assertEqual("child", state["actual"]["agent_id"])

    def test_mismatched_actual_model_never_unlocks_parent(self):
        self.assess()
        self.gate.hook(self.spawn())
        receipt = self.child_receipt("gpt-6-astra", "max")
        self.gate.hook(self.payload("PostToolUse", tool_name="spawn_agent", tool_response=receipt))
        self.assertTrue(self.denied(self.gate.hook(self.payload())))
        self.assertEqual("blocked_model_mismatch", self.gate.load("root", "turn")["status"])

    def test_other_parent_child_cannot_satisfy_dispatch(self):
        self.assess()
        self.gate.hook(self.spawn())
        receipt = self.child_receipt(parent="different-root")
        self.gate.hook(self.payload("PostToolUse", tool_name="spawn_agent", tool_response=receipt))
        self.assertTrue(self.denied(self.gate.hook(self.payload())))

    def test_different_tool_call_id_cannot_satisfy_dispatch(self):
        self.assess()
        self.gate.hook(self.spawn())
        receipt = self.child_receipt()
        self.gate.hook(self.payload("PostToolUse", tool_name="spawn_agent", tool_response=receipt, tool_use_id="other"))
        self.assertTrue(self.denied(self.gate.hook(self.payload())))

    def test_duplicate_dispatch_is_denied_even_when_first_outcome_unknown(self):
        self.assess()
        self.gate.hook(self.spawn())
        self.assertTrue(self.denied(self.gate.hook(self.spawn())))

    def test_native_failure_is_not_success(self):
        self.assess()
        self.gate.hook(self.spawn())
        receipt = self.child_receipt()
        receipt["error"] = "launch failed"
        self.gate.hook(self.payload("PostToolUse", tool_name="spawn_agent", tool_response=receipt))
        self.assertTrue(self.denied(self.gate.hook(self.payload())))

    def test_child_shared_root_session_id_does_not_use_parent_state(self):
        childlog = self.log("child", "child-turn", "gpt-5.6-luna", "medium", "root")
        payload = self.payload(transcript_path=str(childlog), turn_id="child-turn", model="gpt-5.6-luna")
        self.assertEqual({}, self.gate.hook(payload))
        self.assertTrue(self.denied(self.gate.hook(dict(payload, tool_name="spawn_agent"))))

    def test_new_turn_cannot_reuse_old_assessment(self):
        self.assess(execution_size="tiny")
        self.assertTrue(self.denied(self.gate.hook(self.payload(turn_id="different"))))

    def test_tiny_exception_has_two_tool_budget(self):
        self.assess(execution_size="tiny")
        self.assertEqual({}, self.gate.hook(self.payload()))
        self.assertEqual({}, self.gate.hook(self.payload()))
        self.assertTrue(self.denied(self.gate.hook(self.payload())))

    def test_missing_receipt_stop_warns_without_extra_billed_turn(self):
        self.assess()
        result = self.gate.hook(self.payload("Stop"))
        self.assertIn("systemMessage", result)
        self.assertNotIn("decision", result)

    def test_short_answer_needs_no_delegation_or_repeat_turn(self):
        self.assertEqual({}, self.gate.hook(self.payload("Stop")))

    def test_legacy_task_is_explicitly_allowed(self):
        payload = self.payload(task_metadata={"kind": "development", "created_at": "2026-09-17T23:59:59+08:00", "parent_task_id": "old-root"})
        self.assertEqual({}, self.gate.hook(payload))
        self.assertEqual("legacy_allow", self.gate.load("root", "turn")["scope"]["decision"])

    def test_updated_requirement_root_is_allowed(self):
        payload = self.payload(task_metadata={"kind": "requirement", "created_at": "2026-09-18T01:00:00+08:00", "parent_task_id": None, "parent_type": None})
        self.assertEqual({}, self.gate.hook(payload))
        self.assertEqual("root_allow", self.gate.load("root", "turn")["scope"]["decision"])

    def test_updated_development_child_enters_gate(self):
        self.assertTrue(self.denied(self.gate.hook(self.payload(task_metadata={"kind": "development", "created_at": "2026-09-18T01:00:00+08:00", "parent_task_id": "root", "parent_type": "requirement"}))))
        self.assertEqual("child_gate", self.gate.load("root", "turn")["scope"]["decision"])

    def test_unknown_metadata_is_diagnostic_and_does_not_guess(self):
        result = self.gate.hook(self.payload(task_metadata={"kind": "something-else", "created_at": "2026-09-18T01:00:00+08:00", "parent_task_id": "root", "parent_type": "requirement"}))
        self.assertNotEqual("deny", result.get("hookSpecificOutput", {}).get("permissionDecision"))
        scope = self.gate.load("root", "turn")["scope"]
        self.assertEqual("unknown_allow", scope["decision"])
        self.assertIn("unsupported", scope["reason"])

    def test_unknown_policy_version_is_diagnostic(self):
        result = self.gate.hook(self.payload(task_metadata={"kind": "development", "created_at": "2026-09-18T01:00:00+08:00", "parent_task_id": "root", "parent_type": "requirement", "policy_version": "future"}))
        self.assertNotEqual("deny", result.get("hookSpecificOutput", {}).get("permissionDecision"))
        self.assertIn("policy_version", self.gate.load("root", "turn")["scope"]["reason"])

    def test_coordinator_role_keeps_astra_max(self):
        result = self.assess(kind="coordination", judgment="routine", parent_work="")
        self.assertEqual("self", result["decision"]["execution_kind"])
        self.assertEqual({"model": "gpt-6-astra", "effort": "max"}, result["decision"]["selected"])

    def test_external_send_message_tool_is_not_bootstrap_exempt(self):
        self.assertTrue(self.denied(self.gate.hook(self.payload(tool_name="mcp__chat__send_message"))))

    def test_unknown_dispatch_cannot_be_retried(self):
        self.assess()
        self.gate.hook(self.spawn())
        with self.assertRaisesRegex(ValueError, "explicit native failed"):
            self.gate.retry("root", "turn")

    def test_verified_failed_dispatch_can_retry_once_then_stops(self):
        self.assess()
        self.gate.hook(self.spawn())
        failure = self.payload("PostToolUse", tool_name="spawn_agent", tool_response={"error": "unavailable"})
        self.gate.hook(failure)
        self.gate.retry("root", "turn")
        self.assertEqual({}, self.gate.hook(self.spawn()))
        self.gate.hook(failure)
        with self.assertRaisesRegex(ValueError, "failed twice"):
            self.gate.retry("root", "turn")

    def test_second_independent_phase_keeps_first_native_receipt(self):
        self.assess()
        self.gate.hook(self.spawn())
        receipt = self.child_receipt()
        self.gate.hook(self.payload("PostToolUse", tool_name="spawn_agent", tool_response=receipt))
        result = self.assess(phase="second-review", kind="review", judgment="routine")
        self.assertEqual("team_terra_specialist", result["selected_role"])
        state = self.gate.load("root", "turn")
        self.assertEqual("child", state["prior_phases"][0]["actual"]["agent_id"])
        self.assertIsNone(state["actual"])


if __name__ == "__main__":
    unittest.main()
