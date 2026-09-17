from __future__ import annotations

import argparse
import copy
import importlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path
from handoff_fixtures import make_bundle


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
<!-- {"schemaVersion":"oneos.test-scope/v1","requirementId":"REQ-1","deliveryId":"DEL-1","developmentTaskId":"DEV-1","deliveryEnd":"Web","scopeId":"SCOPE-DEV-1","testMode":"mandatory-test-task","testPlanId":null,"directoryIds":[],"selectedCaseIds":[],"deliveryVersion":"commit:abc123","idempotencyKey":"scope-DEV-1-v1"} -->
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


def update_body(**values) -> str:
    return json.dumps(values, ensure_ascii=False, separators=(",", ":"))


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
    plan = {
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
            "testPlanId": None,
            "directoryIds": [],
            "selectedCaseIds": [],
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
                "directoryIds": [],
                "selectedCaseIds": [],
                "selectedCaseResults": [],
                "formalTestValidationSkipped": True,
                "skipReason": "no-associated-test-plan",
                "planDiscovery": {
                    "status": "available",
                    "plugin": "aliyun-cli-devops",
                    "versionBefore": "0.9.0",
                    "versionAfter": "0.9.0",
                    "upgradeAttempted": False,
                    "retryAttempted": False,
                    "traceIds": [],
                },
            },
        },
        "stages": {
            "testHandoff": transaction(
                "test-handoff-DEV-1-v1",
                [{
                    "operation": "projex-update-workitem",
                    "args": [
                        "--id", "TEST-1", "--biz-body",
                        update_body(assignedTo="QA-1", description=DESCRIPTION,
                                    formatType="MARKDOWN"),
                    ],
                }],
                test_readbacks,
            ),
            "developmentComplete": transaction(
                "development-complete-DEV-1-v1",
                [{
                    "operation": "projex-update-workitem",
                    "args": ["--id", "DEV-1", "--biz-body",
                             update_body(status="STATUS-COMPLETE")],
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
                    "args": ["--id", "REQ-1", "--biz-body",
                             update_body(status="STATUS-WAIT-TEST")],
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
    bundle = make_bundle("development")
    plan["evidence"]["handoffEvidence"] = bundle
    description = EXECUTOR.hg.upsert_bundle("开发人员的人工说明", bundle)
    stage = plan["stages"]["developmentComplete"]
    stage["actions"][0]["args"][-1] = update_body(
        status="STATUS-COMPLETE", description=description, formatType="MARKDOWN"
    )
    stage["verifications"][0]["expect"]["description"] = description
    plan["finalReadbacks"][0]["expect"]["description"] = description
    return plan


class CompleteDevelopmentExecutorTests(unittest.TestCase):
    def test_update_actions_use_official_cli_biz_body(self):
        plan = valid_plan()
        for stage_name in ("testHandoff", "developmentComplete", "requirementHandoff"):
            action = plan["stages"][stage_name]["actions"][0]
            self.assertIn("--biz-body", action["args"])
            self.assertNotIn("--status", action["args"])
            self.assertNotIn("--description", action["args"])
            self.assertNotIn("--assigned-to", action["args"])

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

    def test_formal_plan_requires_exact_cases(self):
        plan = valid_plan()
        plan["scope"]["testMode"] = "formal-plan"
        plan["scope"]["testPlanId"] = "PLAN-1"
        plan["scope"]["directoryIds"] = ["DIR-1"]
        plan["evidence"]["testScopeResolution"].update(
            decision="formal-plan", testMode="formal-plan",
            testPlan={"id": "PLAN-1"}, scopeDirectories=[{"id": "DIR-1"}],
            directoryIds=["DIR-1"], selectedCaseIds=[],
        )
        with self.assertRaisesRegex(GATEWAY.core.AdapterError, "具体用例"):
            EXECUTOR.validate_plan(plan)

    def test_formal_plan_scope_must_match_resolution(self):
        plan = valid_plan()
        plan["scope"].update(
            testMode="formal-plan", testPlanId="PLAN-1",
            directoryIds=["DIR-1"], selectedCaseIds=["CASE-OTHER"],
        )
        plan["evidence"]["testScopeResolution"].update(
            decision="formal-plan", testMode="formal-plan",
            testPlan={"id": "PLAN-1"}, scopeDirectories=[{"id": "DIR-1"}],
            directoryIds=["DIR-1"], selectedCaseIds=["CASE-1"],
        )
        with self.assertRaisesRegex(GATEWAY.core.AdapterError, "具体用例与解析回执不一致"):
            EXECUTOR.validate_plan(plan)

    def test_mandatory_scope_accepts_empty_formal_directory_resolution(self):
        plan = valid_plan()
        plan["evidence"]["testScopeResolution"].update(
            decision="scope-empty", testPlan={"id": "PLAN-1"},
            scopeDirectories=[{"id": "DIR-1"}], directoryIds=["DIR-1"],
            formalTestValidationSkipped=True, skipReason="scope-empty",
        )
        self.assertEqual(EXECUTOR.validate_plan(plan)["scope"]["testMode"],
                         "mandatory-test-task")

    def test_mandatory_scope_rejects_claimed_case_ids(self):
        plan = valid_plan()
        plan["scope"]["selectedCaseIds"] = ["CASE-1"]
        with self.assertRaisesRegex(GATEWAY.core.AdapterError, "不得伪造"):
            EXECUTOR.validate_plan(plan)

    def test_plan_read_skip_requires_plugin_upgrade_diagnostics(self):
        plan = valid_plan()
        plan["evidence"]["testScopeResolution"].update(
            decision="plan-read-skipped",
            formalTestValidationSkipped=True,
            skipReason="plan-read-unavailable-after-plugin-upgrade",
            planDiscovery={
                "status": "unavailable-after-plugin-upgrade",
                "plugin": "aliyun-cli-devops",
                "versionBefore": "0.5.2",
                "versionAfter": "0.9.0",
                "upgradeAttempted": True,
                "retryAttempted": True,
                "initialError": "StatusCode: 500 Code: <nil> traceId=TRACE-1",
                "retryError": "StatusCode: 500 Detail: <nil> traceId=TRACE-2",
                "traceIds": ["TRACE-1", "TRACE-2"],
            },
        )
        validated = EXECUTOR.validate_plan(plan)
        self.assertEqual(
            validated["evidence"]["testScopeResolution"]["decision"],
            "plan-read-skipped",
        )

    def test_plan_read_skip_without_retry_diagnostics_is_rejected(self):
        plan = valid_plan()
        plan["evidence"]["testScopeResolution"].update(
            decision="plan-read-skipped",
            planDiscovery={"status": "unavailable-after-plugin-upgrade"},
        )
        with self.assertRaisesRegex(GATEWAY.core.AdapterError, "插件升级、重试"):
            EXECUTOR.validate_plan(plan)

    def test_json_recovery_requires_success_evidence(self):
        plan = valid_plan()
        discovery = plan["evidence"]["testScopeResolution"]["planDiscovery"]
        discovery.update(status="recovered-after-json-api", jsonReadAttempted=True,
                         jsonReadSucceeded=True, transport="official-openapi-json",
                         contentType="application/json")
        EXECUTOR.validate_plan(plan)
        discovery["jsonReadSucceeded"] = False
        with self.assertRaisesRegex(GATEWAY.core.AdapterError, "JSON恢复读取"):
            EXECUTOR.validate_plan(plan)

    def test_default_json_read_requires_success_evidence(self):
        plan = valid_plan()
        discovery = plan["evidence"]["testScopeResolution"]["planDiscovery"]
        discovery.update(status="available-json-api", jsonReadAttempted=True,
                         jsonReadSucceeded=True, transport="official-openapi-json",
                         contentType="application/json")
        EXECUTOR.validate_plan(plan)
        del discovery["jsonReadSucceeded"]
        with self.assertRaisesRegex(GATEWAY.core.AdapterError, "JSON恢复读取"):
            EXECUTOR.validate_plan(plan)

    def test_json_failure_receipt_does_not_require_irrelevant_plugin_upgrade(self):
        plan = valid_plan()
        resolution = plan["evidence"]["testScopeResolution"]
        resolution.update(decision="plan-read-skipped", skipReason="plan-read-unavailable-json-api",
                          planDiscovery={"status": "unavailable-json-api",
                              "transport": "official-openapi-json", "contentType": "application/json",
                              "jsonReadAttempted": True, "jsonReadSucceeded": False,
                              "jsonReadError": "StatusCode: 500 traceId=JSON-FAIL",
                              "upgradeAttempted": False, "retryAttempted": False})
        EXECUTOR.validate_plan(plan)
        resolution["planDiscovery"]["jsonReadError"] = ""
        with self.assertRaisesRegex(GATEWAY.core.AdapterError, "真实JSON失败"):
            EXECUTOR.validate_plan(plan)

    def test_no_plan_without_successful_discovery_is_rejected(self):
        plan = valid_plan()
        plan["evidence"]["testScopeResolution"]["planDiscovery"] = {
            "status": "unavailable-after-plugin-upgrade",
        }
        with self.assertRaisesRegex(GATEWAY.core.AdapterError, "成功的测试计划读取回执"):
            EXECUTOR.validate_plan(plan)

    def test_no_plan_must_explicitly_skip_formal_validation(self):
        plan = valid_plan()
        plan["evidence"]["testScopeResolution"]["formalTestValidationSkipped"] = False
        with self.assertRaisesRegex(GATEWAY.core.AdapterError, "显式记录跳过"):
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

    @mock.patch.object(EXECUTOR, "_verify_handoff")
    def test_preflight_without_other_skill_installations_or_suite_state(self, handoff):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan_path = root / "plan.json"
            plan_path.write_text(json.dumps(valid_plan()), encoding="utf-8")

            def preflight_stage(args):
                GATEWAY.write_json(Path(args.output), {"fingerprint": "checked"})

            # A legacy path may be stale or missing; neither it nor any SKILL.md
            # should be consulted when validating real completion evidence.
            for legacy in ([], ["--suite-state", str(root / "missing-suite.json")]):
                with self.subTest(legacy=legacy):
                    output = root / "preflight.json"
                    args = EXECUTOR.build_parser().parse_args([
                        "preflight", "--plan", str(plan_path), "--output", str(output), *legacy,
                    ])
                    with mock.patch.object(GATEWAY, "cmd_preflight", side_effect=preflight_stage):
                        self.assertEqual(args.func(args), 0)
                    result = json.loads(output.read_text(encoding="utf-8"))
                    self.assertEqual(result["result"], "ready")
                    self.assertNotIn("suiteState", result)
                    self.assertIn("testHandoff", result["stagePreflights"])
            self.assertEqual(handoff.call_count, 2)

    def test_development_only_install_still_checks_delivery_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            scripts = root / "yunxiao-development-delivery" / "scripts"
            shutil.copytree(SCRIPTS, scripts, ignore=shutil.ignore_patterns(
                "__pycache__", "*.pyc", "verify_lifecycle_suite.py",
            ))
            plan = valid_plan()
            del plan["evidence"]["trustedDeliveryVersion"]
            plan_path = root / "plan.json"
            plan_path.write_text(json.dumps(plan), encoding="utf-8")
            result = subprocess.run([
                sys.executable, "-B", str(scripts / "yunxiao_cli_complete_development.py"),
                "preflight", "--plan", str(plan_path),
            ], cwd=root, capture_output=True, text=True, encoding="utf-8", timeout=30,
                env={**os.environ, "PYTHONIOENCODING": "utf-8"})
            self.assertEqual(result.returncode, 69, result.stderr)
            self.assertIn("缺少可信交付版本", json.loads(result.stderr)["error"])
            self.assertNotIn("生命周期Skill", result.stderr)

    @mock.patch.object(EXECUTOR, "_verify_handoff", side_effect=GATEWAY.core.AdapterError("交棒证据失效"))
    def test_no_suite_gate_does_not_bypass_live_handoff(self, _handoff):
        with tempfile.TemporaryDirectory() as directory:
            plan_path = Path(directory) / "plan.json"
            plan_path.write_text(json.dumps(valid_plan()), encoding="utf-8")
            with mock.patch.object(GATEWAY, "cmd_preflight") as stage:
                with self.assertRaisesRegex(GATEWAY.core.AdapterError, "交棒证据失效"):
                    EXECUTOR.command_preflight(argparse.Namespace(plan=str(plan_path), output=None))
                stage.assert_not_called()

    @mock.patch.object(EXECUTOR, "_verify_handoff")
    def test_critical_failure_stops_later_stages_and_persists_partial_receipt(self, _gate):
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

    @mock.patch.object(EXECUTOR, "_verify_handoff")
    def test_apply_uses_fixed_stage_order_and_finishes_with_final_readbacks(self, _gate):
        raw = valid_plan()
        raw["stages"]["requirementDevelopmentComplete"] = transaction(
            "requirement-development-complete-DEV-1-v1",
            [{
                "operation": "projex-update-workitem",
                "args": ["--id", "REQ-1", "--biz-body",
                         update_body(status="STATUS-DEVELOPMENT-COMPLETE")],
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
                    # Old installation metadata is informational, even when stale.
                    "suiteState": {"verified": False, "suiteVersion": "old", "evidencePaths": {}},
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
