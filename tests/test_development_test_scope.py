from __future__ import annotations

import argparse
import importlib
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
SCRIPTS = ROOT / "skills" / "yunxiao-development-delivery" / "scripts"
sys.path.insert(0, str(SCRIPTS))
SCOPE = importlib.import_module("yunxiao_cli_test_scope")


class DevelopmentTestScopeTests(unittest.TestCase):
    def resolve(self, responses: dict[str, object]) -> dict:
        original_find = SCOPE.core.find_aliyun
        original_auth = SCOPE.core.require_auth_env
        original_run = SCOPE.core.run_devops

        def run_devops(_executable: str, args: list[str]):
            operation = args[0]
            value = responses[operation]
            return value(args) if callable(value) else value

        try:
            SCOPE.core.find_aliyun = lambda: "aliyun"
            SCOPE.core.require_auth_env = lambda: {"organizationId": "ORG-1"}
            SCOPE.core.run_devops = run_devops
            with tempfile.TemporaryDirectory() as directory:
                output = Path(directory) / "scope.json"
                result = SCOPE.command_resolve(argparse.Namespace(
                    project_id="PROJECT-1", requirement_sn="ONEOS-900",
                    development_task_sn="ONEOS-901", delivery_end="Web",
                    test_plan_id=None, output=str(output),
                ))
                self.assertEqual(result, 0)
                return json.loads(output.read_text(encoding="utf-8"))
        finally:
            SCOPE.core.find_aliyun = original_find
            SCOPE.core.require_auth_env = original_auth
            SCOPE.core.run_devops = original_run

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


if __name__ == "__main__":
    unittest.main()
