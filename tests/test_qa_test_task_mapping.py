from __future__ import annotations

import importlib.util
import argparse
import contextlib
import io
import json
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path


ROOT = Path(__file__).parents[1]
SCRIPTS = ROOT / "skills" / "YunxiaoQA" / "scripts"
sys.path.insert(0, str(SCRIPTS))
saved_modules = {
    name: sys.modules.pop(name)
    for name in ("yunxiao_cli_runtime", "yunxiao_cli_testhub")
    if name in sys.modules
}
try:
    spec = importlib.util.spec_from_file_location(
        "qa_test_task_mapping_lifecycle", SCRIPTS / "yunxiao_cli_test_lifecycle.py"
    )
    QA = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(QA)
finally:
    for name in ("yunxiao_cli_runtime", "yunxiao_cli_testhub"):
        sys.modules.pop(name, None)
    sys.modules.update(saved_modules)
    sys.path.remove(str(SCRIPTS))


class QaTestTaskMappingTests(unittest.TestCase):
    def scope(self):
        return {"schemaVersion": QA.TEST_SCOPE_SCHEMA, "scopeId": "scope-web",
                "requirementId": "REQ-1", "deliveryId": "DEL-1",
                "developmentTaskId": "DEV-1", "testMode": "formal-plan",
                "testPlanId": "PLAN-1", "directoryIds": ["DIR-WEB"],
                "selectedCaseIds": ["CASE-1", "CASE-2"]}

    def run_start(self, *, conflict=False):
        scope = self.scope()
        test = {"id": "TEST-1", "serialNumber": "ONEOS-1", "subject": "【测试】Web",
                "status": {"name": "待处理"}, "description": "人工正文\n" +
                QA.TEST_SCOPE_START + "\n" + json.dumps(scope) + "\n" + QA.TEST_SCOPE_END}
        req = {"id": "REQ-1", "serialNumber": "ONEOS-2", "subject": "需求",
               "status": {"name": "待测试"}}
        latest_req = {**req, "status": {"name": "已取消"}} if conflict else req
        writes = []

        def update(_cli, target, fields):
            writes.append((target, fields))
            self.assertEqual(set(fields), {"status"})
            original = test if target == "TEST-1" else req
            return {**original, "status": {"name": fields["status"]}}

        with tempfile.TemporaryDirectory() as directory, contextlib.ExitStack() as stack:
            args = argparse.Namespace(command="start", space_id="P-1", test_sn="ONEOS-1",
                req_sn="ONEOS-2", handoff_bundle=None, apply=True, idempotency_key="start-1",
                output=str(Path(directory) / "receipt.json"))
            stack.enter_context(patch.object(QA.core, "find_aliyun", return_value="aliyun"))
            stack.enter_context(patch.object(QA.core, "require_auth_env", return_value={"organizationId": "ORG"}))
            stack.enter_context(patch.object(QA, "exact_workitem", side_effect=[test, req]))
            stack.enter_context(patch.object(QA, "get_workitem", side_effect=[test, latest_req]))
            stack.enter_context(patch.object(QA, "relation_ids", side_effect=lambda cli, target, kind:
                ["DEL-1"] if kind == "PARENT" else ["REQ-1"]))
            stack.enter_context(patch.object(QA, "update_item", side_effect=update))
            stack.enter_context(patch.object(QA, "status_id", side_effect=lambda cli, project, item, name: name))
            bundle = stack.enter_context(patch.object(QA, "validate_handoff_bundle"))
            deployment = stack.enter_context(patch.object(QA, "validate_deployment"))
            with contextlib.redirect_stdout(io.StringIO()):
                if conflict:
                    with self.assertRaisesRegex(QA.core.AdapterError, "需求或正式关系已变化"):
                        QA.run(args)
                    self.assertEqual(writes, [])
                else:
                    self.assertEqual(QA.run(args), 0)
                    receipt = json.loads(Path(args.output).read_text(encoding="utf-8"))
                    self.assertTrue(receipt["verified"])
                    self.assertEqual(len(writes), 2)
                    self.assertIn("仅接收任务", receipt["warnings"][0])
            bundle.assert_not_called()
            deployment.assert_not_called()

    def test_start_without_product_bundle_deployment_or_iteration(self):
        self.run_start()

    def test_start_stale_requirement_still_blocks_without_writes(self):
        self.run_start(conflict=True)

    def check_scope(self, *, status="PASS", missing=False, duplicate=False,
                    wrong_plan=False, outside=False, complete=True):
        first = {"id": "CASE-1", "status": "PASS", "testResultIdentifier": "RUN-1"}
        second = {"id": "CASE-2", "status": status, "testResultIdentifier": "RUN-2"}
        items = [first] if missing else [first, second]
        if duplicate:
            items.append({**first, "status": "FAILURE"})
        counts = {"total": 2, "passed": 2 if status == "PASS" else 1,
                  "failed": int(status == "FAILURE"), "blocked": int(status == "POSTPONE"),
                  "unexecuted": int(status == "TODO")}
        evidence = {"testPlan": {"id": "OTHER" if wrong_plan else "PLAN-1"},
                    "caseRun": {"id": "RUN-1"}, "caseCounts": counts,
                    "report": {"url": "https://devops.aliyun.com/testhub/plan/PLAN-1/dashboard"}}
        snapshot = {"matched": first, "results": [
            {"directoryId": "DIR-WEB", "items": items},
            {"directoryId": "DIR-MINI", "items": [{"id": "CASE-3", "status": "TODO"}]}]}
        with patch.object(QA, "read_plan_case", return_value=snapshot), \
                patch.object(QA.core, "run_devops", side_effect=AssertionError("不应查询全计划计数")):
            return QA.validate_testhub("aliyun", evidence, "CASE-3" if outside else "CASE-1",
                test_scope=self.scope(), require_complete=complete)

    def test_sibling_scope_todo_does_not_block_current_scope_completion(self):
        result = self.check_scope()
        self.assertEqual(result["caseCounts"]["passed"], 2)
        self.assertEqual(result["selectedCaseIds"], ["CASE-1", "CASE-2"])

    def test_current_scope_failed_blocked_todo_and_unknown_still_block(self):
        for status in ("FAILURE", "POSTPONE", "TODO", "UNKNOWN"):
            with self.subTest(status=status), self.assertRaises(QA.core.AdapterError):
                self.check_scope(status=status)

    def test_missing_ambiguous_outside_or_wrong_plan_scope_still_block(self):
        for field in ("missing", "duplicate", "outside", "wrong_plan"):
            with self.subTest(field=field), self.assertRaises(QA.core.AdapterError):
                self.check_scope(**{field: True})

    def test_record_can_record_scoped_failure_without_claiming_completion(self):
        result = self.check_scope(status="FAILURE", complete=False)
        self.assertEqual(result["caseCounts"]["failed"], 1)

    def aggregate(self, tests: list[dict]) -> dict:
        return {
            "development": [
                {"id": "DEV-1", "status": "已完成"},
                {"id": "DEV-2", "status": "已完成"},
                {"id": "DEV-CANCELLED", "status": "已取消"},
            ],
            "tests": tests,
        }

    def test_one_completed_test_per_active_development_task_passes(self):
        gaps = QA.development_test_mapping_gaps(self.aggregate([
            {"id": "TEST-1", "status": "已完成", "developmentTaskId": "DEV-1",
             "testMode": "formal-plan"},
            {"id": "TEST-2", "status": "处理中", "developmentTaskId": "DEV-2",
             "testMode": "mandatory-test-task"},
        ]), "TEST-2")
        self.assertEqual(gaps, [])

    def test_missing_duplicate_or_lightweight_mapping_blocks_aggregation(self):
        gaps = QA.development_test_mapping_gaps(self.aggregate([
            {"id": "TEST-1", "status": "已完成", "developmentTaskId": "DEV-1",
             "testMode": "lightweight-verification"},
            {"id": "TEST-1B", "status": "已完成", "developmentTaskId": "DEV-1",
             "testMode": "mandatory-test-task"},
        ]), "TEST-1B")
        self.assertTrue(any("轻量验证" in gap for gap in gaps))
        self.assertTrue(any("多个测试任务" in gap for gap in gaps))
        self.assertTrue(any("DEV-2缺少对应测试任务" in gap for gap in gaps))

    def test_invalid_scope_and_unfinished_sibling_block_aggregation(self):
        gaps = QA.development_test_mapping_gaps(self.aggregate([
            {"id": "TEST-1", "status": "处理中", "developmentTaskId": "DEV-1",
             "testMode": "formal-plan"},
            {"id": "TEST-2", "status": "已完成", "testScopeError": "缺少范围"},
        ]), "TEST-2")
        self.assertTrue(any("TEST-1不是已完成" in gap for gap in gaps))
        self.assertTrue(any("TEST-2范围无效" in gap for gap in gaps))
        self.assertTrue(any("DEV-2缺少对应测试任务" in gap for gap in gaps))


if __name__ == "__main__":
    unittest.main()
