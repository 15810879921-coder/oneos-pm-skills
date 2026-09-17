"""Exercise the real preflight/apply path; only the official CLI is simulated."""
from __future__ import annotations

import argparse
import copy
import contextlib
import importlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

SCRIPTS = Path(__file__).parents[1] / "skills/yunxiao-development-delivery/scripts"
sys.path.insert(0, str(SCRIPTS))
G = importlib.import_module("yunxiao_cli_gateway")
E = importlib.import_module("yunxiao_cli_complete_development")
from test_complete_development_executor import valid_plan


class GatewayRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        self.root = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        self.stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
        for name, value in (("find_aliyun", "fake-cli"), ("require_auth_env", None),
                            ("current_user", {"id": "U1"}), ("output_dir", self.root)):
            self.stack.enter_context(mock.patch.object(G.core, name, return_value=value))
        self.items = {key: {"id": key, "serialNumber": key, "subject": "普通任务",
                           "status": {"id": "S1", "displayName": "处理中"},
                           "assignedTo": {"id": "U1"}, "description": "original",
                           "spaceIdentifier": "PROJECT-1", "modifiedAt": 1}
                      for key in ("DEV-1", "REQ-1", "TEST-1", "DEL-1")}
        self.writes = []
        self.fail_write = False
        self.fail_read_after_write = False
        self.stack.enter_context(mock.patch.object(G.core, "run_devops", side_effect=self.cli))

    def cli(self, executable, args):
        operation, *flags = args
        target = G._arg_value(flags, "--id")
        if operation == "projex-get-workitem":
            if self.writes and self.fail_read_after_write:
                raise G.core.AdapterError("readback timeout")
            return copy.deepcopy(self.items[target])
        if operation == "projex-list-workitem-relation-records":
            return [{"resourceId": "DEL-1" if "PARENT" in flags else "REQ-1"}]
        self.writes.append(args)
        if self.fail_write:
            raise G.core.AdapterError("write outcome unknown")
        if operation == "projex-update-workitem":
            body_text = G._arg_value(flags, "--biz-body")
            body = json.loads(body_text) if body_text else {}
            for flag, field in (("--description", "description"), ("--assigned-to", "assignedTo")):
                value = G._arg_value(flags, flag)
                if value is not None:
                    self.items[target][field] = {"id": value} if field == "assignedTo" else value
            if "description" in body:
                self.items[target]["description"] = body["description"]
            if "assignedTo" in body:
                self.items[target]["assignedTo"] = {"id": body["assignedTo"]}
            status = G._arg_value(flags, "--status") or body.get("status")
            if status:
                names = {"STATUS-COMPLETE": "已完成", "STATUS-WAIT-TEST": "待测试"}
                self.items[target]["status"] = {"id": status, "displayName": names[status]}
            self.items[target]["modifiedAt"] += 1
        return {"id": "RESULT-1"}

    def plan(self, key="one"):
        return {"schema": G.PLAN_SCHEMA, "authority": "apply", "idempotencyKey": key,
                "guards": [{"operation": "projex-get-workitem", "args": ["--id", "DEV-1"],
                            "expect": {"serialNumber": "DEV-1"}}],
                "actions": [{"operation": "projex-create-workitem-comment",
                             "args": ["--id", "DEV-1", "--content", "hello"]}],
                "verifications": [{"operation": "projex-get-workitem", "args": ["--id", "DEV-1"],
                                   "expect": {"serialNumber": "DEV-1"}}]}

    def preflight(self, plan):
        path = self.root / (plan["idempotencyKey"] + ".json")
        G.write_json(path, plan)
        output = path.with_name(path.stem + "-preflight.json")
        G.cmd_preflight(argparse.Namespace(plan=str(path), output=str(output)))
        return argparse.Namespace(preflight=str(output), receipt=str(self.root / "receipt.json"), resume=False)

    def test_update_clock_drift_does_not_block(self):
        args = self.preflight(self.plan())
        self.items["DEV-1"]["modifiedAt"] = 200
        self.assertEqual(G.cmd_apply(args), 0)
        self.assertEqual(len(self.writes), 1)

    def test_business_drift_still_blocks_even_if_not_in_expect(self):
        for field, value in (("status", {"displayName": "已取消"}),
                             ("assignedTo", {"id": "another"}), ("description", "changed"),
                             ("spaceIdentifier", "OTHER"), ("unknownBusinessField", True)):
            with self.subTest(field=field):
                original = copy.deepcopy(self.items["DEV-1"])
                args = self.preflight(self.plan(field))
                self.items["DEV-1"][field] = value
                with self.assertRaisesRegex(G.core.AdapterError, "漂移"):
                    G.cmd_apply(args)
                self.items["DEV-1"] = original
        self.assertEqual(self.writes, [])

    def test_explicit_clock_expectation_is_not_ignored(self):
        plan = self.plan()
        plan["guards"][0]["expect"]["modifiedAt"] = 1
        args = self.preflight(plan)
        self.items["DEV-1"]["modifiedAt"] = 2
        with self.assertRaisesRegex(G.core.AdapterError, "校验失败"):
            G.cmd_apply(args)

    def test_other_operations_and_nested_business_clocks_are_preserved(self):
        value = {"updatedAt": 1, "child": {"updatedAt": 2}}
        self.assertEqual(G.guard_snapshot({"operation": "codeup-get-branch"}, value), value)
        self.assertEqual(G.guard_snapshot({"operation": "projex-get-workitem"}, value),
                         {"child": {"updatedAt": 2}})

    def test_legacy_preflight_keeps_strict_comparison(self):
        args = self.preflight(self.plan())
        receipt = G.load_object(args.preflight)
        receipt["guards"] = [{"sha256": G.stable_hash(self.items["DEV-1"])}]
        G.write_json(Path(args.preflight), receipt)
        self.items["DEV-1"]["modifiedAt"] = 2
        with self.assertRaisesRegex(G.core.AdapterError, "漂移"):
            G.cmd_apply(args)

    def test_readback_timeout_resumes_without_repeating_writes(self):
        args = self.preflight(self.plan())
        self.fail_read_after_write = True
        with self.assertRaisesRegex(G.core.AdapterError, "readback timeout"):
            G.cmd_apply(args)
        self.assertEqual(len(self.writes), 1)
        with self.assertRaisesRegex(G.core.AdapterError, "resume"):
            G.cmd_apply(args)
        self.fail_read_after_write = False
        args.resume = True
        self.assertEqual(G.cmd_apply(args), 0)
        self.assertEqual(len(self.writes), 1)
        self.assertEqual(G.load_object(args.receipt)["result"], "applied")

    def test_resume_requires_all_verifications_to_pass(self):
        args = self.preflight(self.plan())
        self.fail_read_after_write = True
        with self.assertRaises(G.core.AdapterError):
            G.cmd_apply(args)
        self.fail_read_after_write = False
        self.items["DEV-1"]["serialNumber"] = "OTHER"
        args.resume = True
        with self.assertRaisesRegex(G.core.AdapterError, "校验失败"):
            G.cmd_apply(args)
        self.assertEqual(len(self.writes), 1)
        self.assertEqual(G.load_object(args.receipt)["result"], "partial")

    def test_uncertain_write_is_not_replayed(self):
        args = self.preflight(self.plan())
        self.fail_write = True
        with self.assertRaises(G.core.AdapterError):
            G.cmd_apply(args)
        args.resume = True
        with self.assertRaisesRegex(G.core.AdapterError, "结果不明"):
            G.cmd_apply(args)
        self.assertEqual(len(self.writes), 1)

    def test_applied_retry_recreates_missing_output_without_write(self):
        args = self.preflight(self.plan())
        G.cmd_apply(args)
        args.receipt = str(self.root / "recovered-output.json")
        G.cmd_apply(args)
        self.assertEqual(G.load_object(args.receipt)["result"], "applied")
        self.assertEqual(len(self.writes), 1)

    def test_guard_snapshot_tampering_blocks(self):
        args = self.preflight(self.plan())
        value = G.load_object(args.preflight)
        value["guards"][0]["snapshot"]["assignedTo"] = {"id": "other"}
        G.write_json(Path(args.preflight), value)
        with self.assertRaisesRegex(G.core.AdapterError, "指纹"):
            G.cmd_apply(args)

    def test_same_key_concurrent_attempt_never_writes_or_removes_lock(self):
        args = self.preflight(self.plan())
        lock = self.root / f"yunxiao-applied-{G.stable_hash('one')}.lock"
        lock.touch()
        with self.assertRaisesRegex(G.core.AdapterError, "执行锁"):
            G.cmd_apply(args)
        self.assertTrue(lock.exists())
        self.assertEqual(self.writes, [])

    def test_old_incomplete_receipt_cannot_guess_unattempted_action(self):
        args = self.preflight(self.plan())
        plan = G.load_object(args.preflight)
        ledger = self.root / f"yunxiao-applied-{G.stable_hash('one')}.json"
        G.write_json(ledger, {"fingerprint": plan["fingerprint"], "result": "partial", "actions": []})
        args.resume = True
        with self.assertRaisesRegex(G.core.AdapterError, "结果不明"):
            G.cmd_apply(args)
        self.assertEqual(self.writes, [])

    def test_verified_checkpoint_preserves_outputs_for_unattempted_actions(self):
        plan = self.plan()
        plan["actions"].append({"operation": "projex-create-workitem-comment",
                                "args": ["--id", "DEV-1", "--content", "${action.0.id}"]})
        args = self.preflight(plan)
        ledger = self.root / f"yunxiao-applied-{G.stable_hash('one')}.json"
        G.write_json(ledger, {"fingerprint": G.load_object(args.preflight)["fingerprint"],
                             "result": "partial", "checkpointProtocol": 1, "inFlightAction": None,
                             "actions": [{"index": 0, "operation": plan["actions"][0]["operation"],
                                          "result": {"id": "SAVED-RESULT"}}]})
        args.resume = True
        G.cmd_apply(args)
        self.assertEqual(len(self.writes), 1)
        self.assertEqual(self.writes[0][-1], "SAVED-RESULT")

    def test_changed_plan_same_key_cannot_resume(self):
        args = self.preflight(self.plan())
        self.fail_read_after_write = True
        with self.assertRaises(G.core.AdapterError):
            G.cmd_apply(args)
        self.fail_read_after_write = False
        plan = self.plan()
        plan["actions"][0]["args"][-1] = "different"
        args = self.preflight(plan)
        args.resume = True
        with self.assertRaisesRegex(G.core.AdapterError, "不同计划"):
            G.cmd_apply(args)
        self.assertEqual(len(self.writes), 1)

    def prepare_completion(self):
        self.items["TEST-1"]["status"] = {"id": "WAIT", "displayName": "待处理"}
        plan = valid_plan()
        path, preflight, output = (self.root / name for name in ("plan.json", "preflight.json", "completion.json"))
        G.write_json(path, plan)
        self.stack.enter_context(mock.patch.object(E, "_verify_handoff"))
        E.command_preflight(argparse.Namespace(plan=str(path), output=str(preflight)))
        return argparse.Namespace(preflight=str(preflight), output=str(output))

    def test_actual_executor_carries_own_verified_status_and_description_changes(self):
        args = self.prepare_completion()
        self.assertEqual(E.command_apply(args), 0)
        self.assertEqual(G.load_object(args.output)["result"], "complete")
        self.assertEqual([G._arg_value(call, "--id") for call in self.writes],
                         ["TEST-1", "DEV-1", "REQ-1"])
        E.command_apply(args)
        self.assertEqual(len(self.writes), 3)

    def test_stage_carry_does_not_hide_concurrent_owner_change(self):
        args = self.prepare_completion()
        cli = self.cli
        def concurrent(executable, flags):
            result = cli(executable, flags)
            if flags[0] == "projex-update-workitem" and G._arg_value(flags, "--id") == "DEV-1":
                self.items["DEV-1"]["assignedTo"] = {"id": "other"}
            return result
        with mock.patch.object(G.core, "run_devops", side_effect=concurrent):
            with self.assertRaisesRegex(G.core.AdapterError, "漂移"):
                E.command_apply(args)
        self.assertEqual(len(self.writes), 2)
        self.assertEqual(G.load_object(args.output)["failedStage"], "requirementHandoff")

    def test_executor_recovers_stage_readback_failure_without_duplicate_updates(self):
        args = self.prepare_completion()
        cli = self.cli
        def timeout(executable, flags):
            if flags[0] == "projex-get-workitem" and len(self.writes) == 2:
                raise G.core.AdapterError("readback timeout")
            return cli(executable, flags)
        with mock.patch.object(G.core, "run_devops", side_effect=timeout):
            with self.assertRaisesRegex(G.core.AdapterError, "timeout"):
                E.command_apply(args)
        self.assertEqual(len(self.writes), 2)
        self.assertEqual(G.load_object(args.output)["failedStage"], "developmentComplete")
        E.command_apply(args)
        self.assertEqual(len(self.writes), 3)
        self.assertEqual(G.load_object(args.output)["result"], "complete")


if __name__ == "__main__":
    unittest.main()
