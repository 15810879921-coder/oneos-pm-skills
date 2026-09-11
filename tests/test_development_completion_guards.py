from __future__ import annotations

import argparse
import contextlib
import importlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
SCRIPTS = ROOT / "skills" / "yunxiao-development-delivery" / "scripts"
sys.path.insert(0, str(SCRIPTS))
GATEWAY = importlib.import_module("yunxiao_cli_gateway")
ROUTER = importlib.import_module("route_lifecycle_intent")
TEST_SCOPE = importlib.import_module("yunxiao_cli_test_scope")


def transaction_plan(target_status: str) -> dict:
    return GATEWAY.validate_plan({
        "schema": GATEWAY.PLAN_SCHEMA,
        "authority": "apply",
        "idempotencyKey": f"delivery-{target_status}",
        "guards": [{
            "operation": "projex-get-workitem",
            "args": ["--id", "DELIVERY-1"],
            "expect": {"status.displayName": "处理中"},
        }],
        "actions": [{
            "operation": "projex-update-workitem",
            "args": ["--id", "DELIVERY-1", "--status", "STATUS-ID"],
        }],
        "verifications": [{
            "operation": "projex-get-workitem",
            "args": ["--id", "DELIVERY-1"],
            "expect": {"status.displayName": target_status},
        }],
    })


class DevelopmentCompletionGuardTests(unittest.TestCase):
    def test_audit_wording_wins_over_completion_keyword(self):
        for text in (
            "核对一下完成开发命令的处理逻辑",
            "看下开发完成后为什么没有测试任务",
            "检查完成开发流程",
        ):
            with self.subTest(text=text):
                self.assertEqual(ROUTER.route(text, {})["action"], "audit")
        self.assertEqual(ROUTER.route("请完成开发", {})["action"], "complete_development")

    def test_development_gateway_rejects_delivery_completion(self):
        original = GATEWAY.core.run_devops
        GATEWAY.core.run_devops = lambda *_: {
            "id": "DELIVERY-1", "subject": "【交付】Web｜示例", "status": {"displayName": "处理中"}
        }
        try:
            with self.assertRaisesRegex(GATEWAY.core.AdapterError, "禁止把【交付】推进到已完成"):
                GATEWAY.enforce_development_lifecycle("aliyun", transaction_plan("已完成"))
            checks = GATEWAY.enforce_development_lifecycle("aliyun", transaction_plan("处理中"))
            self.assertEqual(checks[0]["targetStatus"], "处理中")
        finally:
            GATEWAY.core.run_devops = original

    def test_no_formal_plan_still_requires_test_task_and_writes_receipt(self):
        original_find = TEST_SCOPE.core.find_aliyun
        original_auth = TEST_SCOPE.core.require_auth_env
        original_list = TEST_SCOPE.list_plans
        TEST_SCOPE.core.find_aliyun = lambda: "aliyun"
        TEST_SCOPE.core.require_auth_env = lambda: None
        TEST_SCOPE.list_plans = lambda *_: []
        try:
            with tempfile.TemporaryDirectory() as directory:
                output = Path(directory) / "scope.json"
                args = argparse.Namespace(
                    project_id="P-1", requirement_sn="REQ-1", development_task_sn="DEV-1",
                    delivery_end="Web", test_plan_id=None, output=str(output),
                )
                stream = io.StringIO()
                with contextlib.redirect_stdout(stream):
                    self.assertEqual(TEST_SCOPE.command_resolve(args), 0)
                receipt = json.loads(output.read_text(encoding="utf-8"))
                self.assertTrue(receipt["testTaskRequired"])
                self.assertEqual(receipt["testMode"], "mandatory-test-task")
                self.assertEqual(receipt["developmentTask"], "DEV-1")
        finally:
            TEST_SCOPE.core.find_aliyun = original_find
            TEST_SCOPE.core.require_auth_env = original_auth
            TEST_SCOPE.list_plans = original_list

    def test_gateway_persists_partial_receipt_after_first_successful_action(self):
        plan = GATEWAY.validate_plan({
            "schema": GATEWAY.PLAN_SCHEMA,
            "authority": "apply",
            "idempotencyKey": "partial-action-proof",
            "guards": [{
                "operation": "projex-get-workitem", "args": ["--id", "ITEM-1"],
                "expect": {"serialNumber": "ITEM-1"},
            }],
            "actions": [
                {"operation": "projex-create-workitem-comment",
                 "args": ["--id", "ITEM-1", "--content", "first"]},
                {"operation": "projex-create-workitem-comment",
                 "args": ["--id", "ITEM-1", "--content", "second"]},
            ],
            "verifications": [{
                "operation": "projex-get-workitem", "args": ["--id", "ITEM-1"],
                "expect": {"serialNumber": "ITEM-1"},
            }],
        })
        guard_value = {"id": "ITEM-ID", "serialNumber": "ITEM-1", "subject": "普通任务"}
        fingerprint = GATEWAY.stable_hash(plan)
        preflight = {
            "schema": GATEWAY.SCHEMA, "stage": "preflight",
            "fingerprint": fingerprint, "plan": plan,
            "guards": [{"sha256": GATEWAY.stable_hash(guard_value)}],
        }
        originals = {
            "find": GATEWAY.core.find_aliyun,
            "auth": GATEWAY.core.require_auth_env,
            "run": GATEWAY.core.run_devops,
            "user": GATEWAY.core.current_user,
            "now": GATEWAY.core.now_utc,
            "out": GATEWAY.core.output_dir,
        }
        calls = []

        def fake_run(_executable, args):
            if args[0] == "projex-get-workitem":
                return guard_value
            calls.append(args)
            if len(calls) == 2:
                raise GATEWAY.core.AdapterError("second action failed")
            return {"commentId": "COMMENT-1"}

        try:
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                preflight_path = root / "preflight.json"
                receipt_path = root / "receipt.json"
                preflight_path.write_text(json.dumps(preflight), encoding="utf-8")
                GATEWAY.core.find_aliyun = lambda: "aliyun"
                GATEWAY.core.require_auth_env = lambda: None
                GATEWAY.core.run_devops = fake_run
                GATEWAY.core.current_user = lambda _executable: {"id": "USER-1"}
                GATEWAY.core.now_utc = lambda: "2026-09-11T00:00:00Z"
                GATEWAY.core.output_dir = lambda: root
                args = argparse.Namespace(
                    preflight=str(preflight_path), receipt=str(receipt_path),
                )
                with self.assertRaisesRegex(GATEWAY.core.AdapterError, "second action failed"):
                    GATEWAY.cmd_apply(args)
                receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
                self.assertEqual(receipt["result"], "partial")
                self.assertEqual(len(receipt["actions"]), 1)
                self.assertEqual(receipt["actions"][0]["index"], 0)
                self.assertIn("second action failed", receipt["error"])
        finally:
            GATEWAY.core.find_aliyun = originals["find"]
            GATEWAY.core.require_auth_env = originals["auth"]
            GATEWAY.core.run_devops = originals["run"]
            GATEWAY.core.current_user = originals["user"]
            GATEWAY.core.now_utc = originals["now"]
            GATEWAY.core.output_dir = originals["out"]


if __name__ == "__main__":
    unittest.main()
