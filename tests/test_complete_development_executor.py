from __future__ import annotations

import argparse
import copy
import importlib
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
SCRIPTS = ROOT / "skills" / "yunxiao-development-delivery" / "scripts"
sys.path.insert(0, str(SCRIPTS))
EXECUTOR = importlib.import_module("yunxiao_cli_complete_development")
GATEWAY = importlib.import_module("yunxiao_cli_gateway")


DESCRIPTION = """## 开发交接
### 测试建议
- 验证当前开发范围
### 临时需求变更点
无（本次开发未发生已确认的临时需求变更）
<!-- ONEOS_TEST_SCOPE_START -->
developmentTaskId: DEV-1
requirementId: REQ-1
deliveryId: DEL-1
testMode: mandatory-test-task
scopeId: SCOPE-DEV-1
deliveryEnd: Web
<!-- ONEOS_TEST_SCOPE_END -->"""


def transaction(key: str, actions: list[dict], verifications: list[dict]) -> dict:
    return {
        "schema": GATEWAY.PLAN_SCHEMA,
        "authority": "apply",
        "idempotencyKey": key,
        "guards": [{
            "operation": "projex-get-workitem",
            "args": ["--id", "DEV-1"],
            "expect": {"serialNumber": "DEV-1"},
        }],
        "actions": actions,
        "verifications": verifications,
    }


def test_task_readbacks() -> list[dict]:
    return [
        {
            "operation": "projex-get-workitem",
            "args": ["--id", "TEST-1"],
            "expect": {
                "status.displayName": "待处理",
                "assignedTo.id": "QA-1",
                "description": DESCRIPTION,
            },
        },
        {
            "operation": "projex-list-workitem-relation-records",
            "args": ["--id", "TEST-1", "--relation-type", "PARENT"],
            "expect": {"0.resourceId": "DEL-1"},
        },
        {
            "operation": "projex-list-workitem-relation-records",
            "args": ["--id", "TEST-1", "--relation-type", "ASSOCIATED"],
            "expect": {"0.resourceId": "REQ-1"},
        },
    ]


def valid_plan() -> dict:
    test_readbacks = test_task_readbacks()
    return {
        "schemaVersion": EXECUTOR.SCHEMA,
        "suiteVersion": EXECUTOR.SUITE_VERSION,
        "idempotencyKey": "complete-DEV-1-v1",
        "scope": {
            "projectId": "PROJECT-1",
            "developmentTaskId": "DEV-1",
            "developmentTaskSerial": "DEV-1",
            "requirementId": "REQ-1",
            "requirementSerial": "REQ-1",
            "deliveryId": "DEL-1",
            "testTaskRef": "TEST-1",
            "testSupervisorId": "QA-1",
            "testMode": "mandatory-test-task",
            "scopeId": "SCOPE-DEV-1",
            "deliveryEnd": "Web",
            "requirementTargetStatus": "待测试",
            "matchingTestTaskIds": ["TEST-1"],
        },
        "evidence": {
            "trustedDeliveryVersion": "commit:abc123",
            "developmentValidation": {"status": "passed", "evidence": "validation:run-1"},
            "testScopeResolution": {
                "schemaVersion": "oneos.test-scope-resolution/v2",
                "decision": "test-task-required",
                "projectId": "PROJECT-1",
                "requirement": "REQ-1",
                "developmentTask": "DEV-1",
                "deliveryEnd": "Web",
                "testTaskRequired": True,
                "testMode": "mandatory-test-task",
                "testPlan": None,
                "scopeDirectories": [],
            },
        },
        "stages": {
            "testHandoff": transaction(
                "test-handoff-DEV-1-v1",
                [{
                    "operation": "projex-update-workitem",
                    "args": [
                        "--id", "TEST-1", "--assigned-to", "QA-1",
                        "--description", DESCRIPTION,
                    ],
                }],
                test_readbacks,
            ),
            "developmentComplete": transaction(
                "development-complete-DEV-1-v1",
                [{
                    "operation": "projex-update-workitem",
                    "args": ["--id", "DEV-1", "--status", "STATUS-COMPLETE"],
                }],
                [{
                    "operation": "projex-get-workitem",
                    "args": ["--id", "DEV-1"],
                    "expect": {"status.displayName": "已完成"},
                }],
            ),
            "requirementHandoff": transaction(
                "requirement-handoff-DEV-1-v1",
                [{
                    "operation": "projex-update-workitem",
                    "args": ["--id", "REQ-1", "--status", "STATUS-WAIT-TEST"],
                }],
                [{
                    "operation": "projex-get-workitem",
                    "args": ["--id", "REQ-1"],
                    "expect": {"status.displayName": "待测试"},
                }],
            ),
        },
        "finalReadbacks": [
            {
                "operation": "projex-get-workitem", "args": ["--id", "DEV-1"],
                "expect": {"status.displayName": "已完成"},
            },
            {
                "operation": "projex-get-workitem", "args": ["--id", "REQ-1"],
                "expect": {"status.displayName": "待测试"},
            },
            {
                "operation": "projex-get-workitem", "args": ["--id", "DEL-1"],
                "expect": {"status.displayName": "处理中"},
            },
            *copy.deepcopy(test_readbacks),
        ],
    }


def suite_state() -> dict:
    names = [
        "YunxiaoPM", "yunxiao-development-delivery", "development-brain",
        "YunxiaoQA", "yunxiao-release-operations",
    ]
    return EXECUTOR.suite.verify([
        f"{name}={ROOT / 'skills' / name / 'SKILL.md'}" for name in names
    ])


class CompleteDevelopmentExecutorTests(unittest.TestCase):
    def test_valid_plan_enforces_test_handoff_before_closure(self):
        plan = EXECUTOR.validate_plan(valid_plan())
        self.assertEqual(plan["scope"]["testMode"], "mandatory-test-task")
        self.assertIn("testHandoff", plan["stages"])

    def test_lightweight_mode_is_rejected(self):
        plan = valid_plan()
        plan["scope"]["testMode"] = "lightweight-verification"
        with self.assertRaisesRegex(GATEWAY.core.AdapterError, "testMode只允许"):
            EXECUTOR.validate_plan(plan)

    def test_web_validation_cannot_be_skipped(self):
        plan = valid_plan()
        plan["evidence"]["developmentValidation"] = {
            "status": "skipped", "evidence": "not-applicable",
        }
        with self.assertRaisesRegex(GATEWAY.core.AdapterError, "只有小程序范围允许"):
            EXECUTOR.validate_plan(plan)

    def test_formal_plan_requires_scope_directories(self):
        plan = valid_plan()
        plan["scope"]["testMode"] = "formal-plan"
        plan["evidence"]["testScopeResolution"].update(
            decision="formal-plan", testMode="formal-plan",
            testPlan={"id": "PLAN-1"}, scopeDirectories=[],
        )
        with self.assertRaisesRegex(GATEWAY.core.AdapterError, "非空端侧目录"):
            EXECUTOR.validate_plan(plan)

    def test_new_test_task_must_reference_test_handoff(self):
        plan = valid_plan()
        plan["scope"]["matchingTestTaskIds"] = []
        plan["scope"]["testTaskRef"] = "${stage.developmentComplete.action.0.id}"
        with self.assertRaisesRegex(GATEWAY.core.AdapterError, "testHandoff动作回执"):
            EXECUTOR.validate_plan(plan)

    def test_new_test_task_receipt_reference_is_supported(self):
        plan = valid_plan()
        plan["scope"]["matchingTestTaskIds"] = []
        plan["scope"]["testTaskRef"] = "${stage.testHandoff.action.0.id}"
        stage = plan["stages"]["testHandoff"]
        stage["actions"] = [{
            "operation": "projex-create-workitem",
            "args": [
                "--subject", "【测试】示例", "--assigned-to", "QA-1",
                "--description", DESCRIPTION,
            ],
        }]
        for readback in stage["verifications"]:
            readback["args"] = [
                "${action.0.id}" if value == "TEST-1" else value
                for value in readback["args"]
            ]
        for readback in plan["finalReadbacks"]:
            readback["args"] = [
                "${stage.testHandoff.action.0.id}"
                if value in {"TEST-1", "${action.0.id}"} else value
                for value in readback["args"]
            ]
        validated = EXECUTOR.validate_plan(plan)
        self.assertEqual(
            validated["scope"]["testTaskRef"], "${stage.testHandoff.action.0.id}",
        )

    def test_requirement_cannot_advance_to_test_complete(self):
        plan = valid_plan()
        plan["scope"]["requirementTargetStatus"] = "测试完成"
        with self.assertRaisesRegex(GATEWAY.core.AdapterError, "不得把需求推进到测试完成"):
            EXECUTOR.validate_plan(plan)

    def test_testing_requirement_must_be_read_only(self):
        plan = valid_plan()
        plan["scope"]["requirementTargetStatus"] = "测试中"
        with self.assertRaisesRegex(GATEWAY.core.AdapterError, "不得由开发执行器再次推进"):
            EXECUTOR.validate_plan(plan)

    def test_development_stage_rejects_extra_write(self):
        plan = valid_plan()
        plan["stages"]["developmentComplete"]["actions"].append({
            "operation": "projex-create-workitem-comment",
            "args": ["--id", "DEV-1", "--content", "extra"],
        })
        with self.assertRaisesRegex(GATEWAY.core.AdapterError, "越权写操作"):
            EXECUTOR.validate_plan(plan)

    def test_suite_state_is_rechecked_from_installed_paths(self):
        state = suite_state()
        self.assertTrue(EXECUTOR._verify_suite_state(state)["verified"])
        state["suiteVersion"] = "10.1.0"
        with self.assertRaisesRegex(GATEWAY.core.AdapterError, "必须全部回读为10.1.1"):
            EXECUTOR._verify_suite_state(state)

    def test_critical_failure_stops_later_stages_and_persists_partial_receipt(self):
        plan = EXECUTOR.validate_plan(valid_plan())
        original_apply = EXECUTOR.gateway.cmd_apply
        calls: list[str] = []

        def fail_test_handoff(args: argparse.Namespace) -> int:
            calls.append(Path(args.preflight).name)
            raise GATEWAY.core.AdapterError("test handoff failed")

        try:
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                preflight_path = root / "complete-preflight.json"
                output_path = root / "complete-receipt.json"
                stage_root = EXECUTOR._stage_dir(preflight_path)
                preflight = {
                    "schemaVersion": EXECUTOR.PREFLIGHT_SCHEMA,
                    "suiteVersion": EXECUTOR.SUITE_VERSION,
                    "result": "ready",
                    "fingerprint": GATEWAY.stable_hash(plan),
                    "suiteState": suite_state(),
                    "plan": plan,
                    "stagePreflights": {
                        name: {"status": "ready", "path": str(stage_root / f"{name}.json")}
                        for name in plan["stages"]
                    },
                }
                preflight_path.write_text(json.dumps(preflight), encoding="utf-8")
                EXECUTOR.gateway.cmd_apply = fail_test_handoff
                with self.assertRaisesRegex(GATEWAY.core.AdapterError, "test handoff failed"):
                    EXECUTOR.command_apply(argparse.Namespace(
                        preflight=str(preflight_path), output=str(output_path),
                    ))
                receipt = json.loads(output_path.read_text(encoding="utf-8"))
                self.assertEqual(calls, ["testHandoff.json"])
                self.assertEqual(receipt["result"], "partial")
                self.assertEqual(receipt["failedStage"], "testHandoff")
                self.assertNotIn("developmentComplete", receipt["stages"])
        finally:
            EXECUTOR.gateway.cmd_apply = original_apply

    def test_apply_uses_fixed_stage_order_and_finishes_with_final_readbacks(self):
        raw = valid_plan()
        raw["stages"]["requirementDevelopmentComplete"] = transaction(
            "requirement-development-complete-DEV-1-v1",
            [{
                "operation": "projex-update-workitem",
                "args": ["--id", "REQ-1", "--status", "STATUS-DEVELOPMENT-COMPLETE"],
            }],
            [{
                "operation": "projex-get-workitem",
                "args": ["--id", "REQ-1"],
                "expect": {"status.displayName": "开发完成"},
            }],
        )
        plan = EXECUTOR.validate_plan(raw)
        original_apply = EXECUTOR.gateway.cmd_apply
        original_final = EXECUTOR._run_final_readbacks
        calls: list[str] = []

        def apply_stage(args: argparse.Namespace) -> int:
            name = Path(args.preflight).stem
            calls.append(name)
            GATEWAY.write_json(Path(args.receipt), {
                "result": "complete", "actions": [], "stage": name,
            })
            return 0

        try:
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                preflight_path = root / "complete-preflight.json"
                output_path = root / "complete-receipt.json"
                stage_root = EXECUTOR._stage_dir(preflight_path)
                stage_preflights = {}
                for name in plan["stages"]:
                    path = stage_root / f"{name}.json"
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text("{}", encoding="utf-8")
                    stage_preflights[name] = {"status": "ready", "path": str(path)}
                preflight_path.write_text(json.dumps({
                    "schemaVersion": EXECUTOR.PREFLIGHT_SCHEMA,
                    "suiteVersion": EXECUTOR.SUITE_VERSION,
                    "result": "ready",
                    "fingerprint": GATEWAY.stable_hash(plan),
                    "suiteState": suite_state(),
                    "plan": plan,
                    "stagePreflights": stage_preflights,
                }), encoding="utf-8")
                EXECUTOR.gateway.cmd_apply = apply_stage
                EXECUTOR._run_final_readbacks = lambda *_: [{"verified": True}]
                self.assertEqual(EXECUTOR.command_apply(argparse.Namespace(
                    preflight=str(preflight_path), output=str(output_path),
                )), 0)
                receipt = json.loads(output_path.read_text(encoding="utf-8"))
                self.assertEqual(calls, [
                    "testHandoff", "developmentComplete",
                    "requirementDevelopmentComplete", "requirementHandoff",
                ])
                self.assertEqual(receipt["result"], "complete")
                self.assertEqual(receipt["finalReadbacks"], [{"verified": True}])
        finally:
            EXECUTOR.gateway.cmd_apply = original_apply
            EXECUTOR._run_final_readbacks = original_final


if __name__ == "__main__":
    unittest.main()
