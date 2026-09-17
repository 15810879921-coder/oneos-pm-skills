from __future__ import annotations

import argparse
import importlib
import json
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path


ROOT = Path(__file__).parents[1]
SCRIPTS = ROOT / "skills" / "yunxiao-development-delivery" / "scripts"
sys.path.insert(0, str(SCRIPTS))
SCOPE = importlib.import_module("yunxiao_cli_test_scope")


class DevelopmentTestScopeTests(unittest.TestCase):
    def resolve(self, responses: dict[str, object], *, expected_result: int = 0) -> dict:
        def run_devops(_executable, args):
            self.assertNotEqual(args[0], "test-hub-list-test-plan")
            value = responses[args[0]]
            return value(args) if callable(value) else value

        value = responses["test-hub-list-test-plan"]
        plans = value.get("items", []) if isinstance(value, dict) else value
        with patch.object(SCOPE.core, "find_aliyun", return_value="aliyun"), \
                patch.object(SCOPE.core, "require_auth_env"), \
                patch.object(SCOPE.core, "run_devops", side_effect=run_devops), \
                patch.object(SCOPE.core, "run_raw", side_effect=AssertionError("plan read must not query or upgrade plugin")) as raw, \
                patch.object(SCOPE, "list_plans_json", return_value=plans,
                             side_effect=plans if isinstance(plans, Exception) else None) as read_json:
            with tempfile.TemporaryDirectory() as directory:
                output = Path(directory) / "scope.json"
                result = SCOPE.command_resolve(argparse.Namespace(
                    project_id="PROJECT-1", requirement_sn="ONEOS-900",
                    development_task_sn="ONEOS-901", delivery_end="Web",
                    test_plan_id=None, output=str(output)))
                self.assertEqual(result, expected_result)
                result = json.loads(output.read_text(encoding="utf-8"))
            read_json.assert_called_once_with("PROJECT-1")
            raw.assert_not_called()
            result["_rawCalls"] = []
            return result

    def test_formal_scope_reads_and_deduplicates_exact_cases(self):
        def results(args: list[str]):
            directory = args[args.index("--directory-identifier") + 1]
            if directory == "DIR-1":
                return {"items": [
                    {"testcaseIdentifier": "CASE-1", "testResultIdentifier": "RESULT-1",
                     "status": "PASS"},
                    {"testcaseIdentifier": "CASE-2", "status": "TODO"},
                ]}
            return {"items": [{"testcaseIdentifier": "CASE-2", "status": "TODO"}]}

        value = self.resolve({
            "test-hub-list-test-plan": {"items": [
                {"testPlanIdentifier": "PLAN-1", "name": "ONEOS-900 正式计划"},
            ]},
            "test-hub-get-test-plan-result-directory-list": [
                {"identifier": "DIR-1", "displayName": "[Web] 主流程"},
                {"identifier": "DIR-2", "displayName": "[Web] 回归"},
                {"identifier": "DIR-3", "displayName": "[小程序] 主流程"},
            ],
            "test-hub-get-test-result-list": results,
        })
        self.assertEqual(value["decision"], "formal-plan")
        self.assertEqual(value["directoryIds"], ["DIR-1", "DIR-2"])
        self.assertEqual(value["selectedCaseIds"], ["CASE-1", "CASE-2"])
        self.assertEqual(value["selectedCaseResults"][0]["testResultId"], "RESULT-1")

    def test_empty_configured_scope_falls_back_to_mandatory_test_task(self):
        value = self.resolve({
            "test-hub-list-test-plan": {"items": [
                {"testPlanIdentifier": "PLAN-1", "name": "ONEOS-900 正式计划"},
            ]},
            "test-hub-get-test-plan-result-directory-list": [
                {"identifier": "DIR-1", "displayName": "[Web] 主流程"},
            ],
            "test-hub-get-test-result-list": {"items": []},
        })
        self.assertEqual(value["decision"], "scope-empty")
        self.assertEqual(value["testMode"], "mandatory-test-task")
        self.assertEqual(value["selectedCaseIds"], [])

    def test_no_plan_keeps_required_test_task_with_empty_exact_scope(self):
        value = self.resolve({"test-hub-list-test-plan": {"items": []}})
        self.assertEqual(value["decision"], "test-task-required")
        self.assertTrue(value["testTaskRequired"])
        self.assertEqual(value["directoryIds"], [])
        self.assertEqual(value["selectedCaseIds"], [])
        self.assertTrue(value["formalTestValidationSkipped"])
        self.assertEqual(value["skipReason"], "no-associated-test-plan")
        self.assertEqual(value["planDiscovery"]["status"], "available-json-api")
        self.assertNotIn(["plugin", "update", "--name", "aliyun-cli-devops"],
                         value["_rawCalls"])

    def test_json_service_failure_records_actual_error_without_plugin_retry(self):
        value = self.resolve({"test-hub-list-test-plan": SCOPE.core.AdapterError("StatusCode: 500 traceId=TRACE-JSON")})
        self.assertEqual(value["decision"], "plan-read-skipped")
        self.assertEqual(value["skipReason"], "plan-read-unavailable-json-api")
        discovery = value["planDiscovery"]
        self.assertEqual(discovery["status"], "unavailable-json-api")
        self.assertFalse(discovery["jsonReadSucceeded"])
        self.assertFalse(discovery["upgradeAttempted"])
        self.assertFalse(discovery["retryAttempted"])
        self.assertEqual(discovery["traceIds"], ["TRACE-JSON"])

    def test_permission_and_invalid_response_fail_without_any_cli_probe(self):
        for message in ("StatusCode: 403 Forbidden", "JSON响应不是计划数组", "项目不一致"):
            with self.subTest(message=message), \
                    patch.object(SCOPE.core, "run_raw") as raw, \
                    patch.object(SCOPE.core, "run_devops") as cli, \
                    patch.object(SCOPE, "list_plans_json", side_effect=SCOPE.core.AdapterError(message)):
                with self.assertRaises(SCOPE.core.AdapterError):
                    SCOPE.discover_plans("PROJECT-1")
                raw.assert_not_called()
                cli.assert_not_called()


if __name__ == "__main__":
    unittest.main()
