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
    def resolve(self, responses: dict[str, object], *, plugin_versions: list[str] | None = None,
                expected_result: int = 0) -> dict:
        original_find = SCOPE.core.find_aliyun
        original_auth = SCOPE.core.require_auth_env
        original_run = SCOPE.core.run_devops
        original_raw = SCOPE.core.run_raw
        raw_calls: list[list[str]] = []
        versions = iter(plugin_versions or ["0.9.0"])

        def run_devops(_executable: str, args: list[str]):
            operation = args[0]
            value = responses[operation]
            if hasattr(value, "__next__"):
                value = next(value)
            if isinstance(value, Exception):
                raise value
            return value(args) if callable(value) else value

        def run_raw(_executable: str, args: list[str], **_kwargs):
            raw_calls.append(args)
            if args[:3] == ["plugin", "show", "--name"]:
                return f"Name:\taliyun-cli-devops\nVersion:\t{next(versions)}"
            if args[:3] == ["plugin", "update", "--name"]:
                return "Updated: 1"
            raise AssertionError(f"unexpected raw call: {args}")

        try:
            SCOPE.core.find_aliyun = lambda: "aliyun"
            SCOPE.core.require_auth_env = lambda: {"organizationId": "ORG-1"}
            SCOPE.core.run_devops = run_devops
            SCOPE.core.run_raw = run_raw
            with tempfile.TemporaryDirectory() as directory:
                output = Path(directory) / "scope.json"
                result = SCOPE.command_resolve(argparse.Namespace(
                    project_id="PROJECT-1", requirement_sn="ONEOS-900",
                    development_task_sn="ONEOS-901", delivery_end="Web",
                    test_plan_id=None, output=str(output),
                ))
                self.assertEqual(result, expected_result)
                value = json.loads(output.read_text(encoding="utf-8"))
                value["_rawCalls"] = raw_calls
                return value
        finally:
            SCOPE.core.find_aliyun = original_find
            SCOPE.core.require_auth_env = original_auth
            SCOPE.core.run_devops = original_run
            SCOPE.core.run_raw = original_raw

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
        self.assertEqual(value["planDiscovery"]["status"], "available")
        self.assertNotIn(["plugin", "update", "--name", "aliyun-cli-devops"],
                         value["_rawCalls"])

    def test_failed_plan_read_updates_only_devops_plugin_and_retries(self):
        error = SCOPE.core.AdapterError(
            'CLI调用失败：devops test-hub-list-test-plan；StatusCode: 500 '
            'Content type not supported traceId":"TRACE-1"'
        )
        value = self.resolve({
            "test-hub-list-test-plan": iter([error, {"items": []}]),
        }, plugin_versions=["0.5.2", "0.9.0"])
        self.assertEqual(value["decision"], "test-task-required")
        self.assertEqual(value["planDiscovery"]["status"],
                         "recovered-after-plugin-upgrade")
        self.assertEqual(value["planDiscovery"]["versionBefore"], "0.5.2")
        self.assertEqual(value["planDiscovery"]["versionAfter"], "0.9.0")
        self.assertIn(["plugin", "update", "--name", "aliyun-cli-devops"],
                      value["_rawCalls"])
        self.assertEqual(value["planDiscovery"]["traceIds"], ["TRACE-1"])

    def test_failed_retry_skips_plan_stage_with_visible_diagnostics(self):
        first = SCOPE.core.AdapterError(
            'CLI调用失败；StatusCode: 500 traceId":"TRACE-OLD"'
        )
        second = SCOPE.core.AdapterError(
            'CLI调用失败；StatusCode: 500 traceId":"TRACE-NEW"'
        )
        value = self.resolve({
            "test-hub-list-test-plan": iter([first, second]),
        }, plugin_versions=["0.9.0", "0.9.0"])
        self.assertEqual(value["decision"], "plan-read-skipped")
        self.assertEqual(value["testMode"], "mandatory-test-task")
        self.assertTrue(value["formalTestValidationSkipped"])
        self.assertEqual(value["planDiscovery"]["status"],
                         "unavailable-after-plugin-upgrade")
        self.assertEqual(value["planDiscovery"]["traceIds"],
                         ["TRACE-OLD", "TRACE-NEW"])
        self.assertIn("最终回报必须披露", value["note"])

    def test_plugin_upgrade_failure_still_retries_and_skips_with_diagnostics(self):
        first = SCOPE.core.AdapterError(
            'CLI调用失败；StatusCode: 500 traceId":"TRACE-OLD"'
        )
        second = SCOPE.core.AdapterError(
            'CLI调用失败；StatusCode: 500 traceId":"TRACE-NEW"'
        )
        original_find = SCOPE.core.find_aliyun
        original_auth = SCOPE.core.require_auth_env
        original_run = SCOPE.core.run_devops
        original_raw = SCOPE.core.run_raw

        def failed_update(_executable: str, args: list[str], **_kwargs):
            if args[:3] == ["plugin", "show", "--name"]:
                return "Name:\taliyun-cli-devops\nVersion:\t0.9.0"
            if args[:3] == ["plugin", "update", "--name"]:
                raise SCOPE.core.AdapterError("plugin registry timeout")
            raise AssertionError(f"unexpected raw call: {args}")

        try:
            SCOPE.core.find_aliyun = lambda: "aliyun"
            SCOPE.core.require_auth_env = lambda: {"organizationId": "ORG-1"}
            SCOPE.core.run_raw = failed_update
            calls = iter([first, second])
            SCOPE.core.run_devops = lambda _exe, _args: (
                (_ for _ in ()).throw(next(calls))
            )
            plans, discovery = SCOPE.discover_plans("aliyun", "PROJECT-1")
        finally:
            SCOPE.core.find_aliyun = original_find
            SCOPE.core.require_auth_env = original_auth
            SCOPE.core.run_devops = original_run
            SCOPE.core.run_raw = original_raw

        self.assertIsNone(plans)
        self.assertTrue(discovery["upgradeAttempted"])
        self.assertFalse(discovery["upgradeSucceeded"])
        self.assertIn("registry timeout", discovery["upgradeError"])
        self.assertTrue(discovery["retryAttempted"])
        self.assertEqual(discovery["traceIds"], ["TRACE-OLD", "TRACE-NEW"])

    def test_permission_failure_does_not_upgrade_or_skip(self):
        original_find = SCOPE.core.find_aliyun
        original_auth = SCOPE.core.require_auth_env
        original_run = SCOPE.core.run_devops
        original_raw = SCOPE.core.run_raw
        raw_calls: list[list[str]] = []
        try:
            SCOPE.core.find_aliyun = lambda: "aliyun"
            SCOPE.core.require_auth_env = lambda: {"organizationId": "ORG-1"}
            SCOPE.core.run_raw = lambda _exe, args, **_kwargs: (
                raw_calls.append(args) or "Name:\taliyun-cli-devops\nVersion:\t0.9.0"
            )
            SCOPE.core.run_devops = lambda _exe, _args: (_ for _ in ()).throw(
                SCOPE.core.AdapterError("StatusCode: 403 Forbidden")
            )
            with self.assertRaisesRegex(SCOPE.core.AdapterError, "403"):
                SCOPE.discover_plans("aliyun", "PROJECT-1")
            self.assertNotIn(["plugin", "update", "--name", "aliyun-cli-devops"], raw_calls)
        finally:
            SCOPE.core.find_aliyun = original_find
            SCOPE.core.require_auth_env = original_auth
            SCOPE.core.run_devops = original_run
            SCOPE.core.run_raw = original_raw


if __name__ == "__main__":
    unittest.main()
