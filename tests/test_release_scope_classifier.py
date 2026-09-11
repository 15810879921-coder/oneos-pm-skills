from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT = (
    Path(__file__).parents[1]
    / "skills"
    / "yunxiao-release-operations"
    / "scripts"
    / "classify_release_scope.py"
)
SPEC = importlib.util.spec_from_file_location("classify_release_scope", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def item(**updates):
    value = {
        "id": "REQ-1",
        "projectId": "P-1",
        "iterationId": "I-1",
        "formallyInIteration": True,
        "requirementStatus": "测试完成",
        "developmentTasks": [{"id": "DEV-1", "status": "已完成"}],
        "testTasks": [{
            "id": "TEST-1",
            "developmentTaskId": "DEV-1",
            "status": "已完成",
            "testMode": "formal-plan",
            "hasRequiredCases": False,
        }],
        "bugs": [],
    }
    value.update(updates)
    return value


def payload(requirement):
    return {
        "projectId": "P-1",
        "iterationId": "I-1",
        "iterationRequirements": [requirement],
    }


class ReleaseScopeClassifierTests(unittest.TestCase):
    def test_formal_plan_requires_completed_task_and_existing_cases_to_pass(self):
        self.assertTrue(MODULE.classify(payload(item()))["releaseReady"])

        task_gap = MODULE.classify(payload(item(testTasks=[{
            "id": "TEST-1", "developmentTaskId": "DEV-1", "status": "处理中",
            "testMode": "formal-plan", "hasRequiredCases": False,
        }])))
        self.assertFalse(task_gap["releaseReady"])
        self.assertIn(
            "测试任务TEST-1不是已完成",
            task_gap["C_selectedIncomplete"][0]["reasons"],
        )

        case_gap = MODULE.classify(
            payload(item(testTasks=[{
                "id": "TEST-1", "developmentTaskId": "DEV-1", "status": "已完成",
                "testMode": "formal-plan", "hasRequiredCases": True,
                "requiredCaseStatus": "failed",
            }]))
        )
        self.assertIn(
            "测试任务TEST-1必需用例未通过",
            case_gap["C_selectedIncomplete"][0]["reasons"],
        )

    def test_lightweight_verification_is_blocked_even_when_it_passed(self):
        result = MODULE.classify(
            payload(
                item(
                    testTasks=[{
                        "id": "TEST-1", "developmentTaskId": "DEV-1", "status": "已完成",
                        "testMode": "lightweight-verification", "hasRequiredCases": False,
                    }],
                )
            )
        )
        self.assertFalse(result["releaseReady"])
        self.assertIn(
            "测试任务TEST-1仍使用已停用的轻量验证模式",
            result["C_selectedIncomplete"][0]["reasons"],
        )

    def test_every_development_task_requires_exactly_one_completed_test_task(self):
        missing = MODULE.classify(payload(item(
            developmentTasks=[
                {"id": "DEV-1", "status": "已完成"},
                {"id": "DEV-2", "status": "已完成"},
            ],
        )))
        self.assertFalse(missing["releaseReady"])
        self.assertIn(
            "开发任务DEV-2缺少对应测试任务",
            missing["C_selectedIncomplete"][0]["reasons"],
        )

        duplicate = MODULE.classify(payload(item(testTasks=[
            {"id": "TEST-1", "developmentTaskId": "DEV-1", "status": "已完成",
             "testMode": "mandatory-test-task", "hasRequiredCases": False},
            {"id": "TEST-2", "developmentTaskId": "DEV-1", "status": "已完成",
             "testMode": "mandatory-test-task", "hasRequiredCases": False},
        ])))
        self.assertFalse(duplicate["releaseReady"])
        self.assertIn(
            "开发任务DEV-1存在多个测试任务",
            duplicate["C_selectedIncomplete"][0]["reasons"],
        )

    def test_any_unclosed_bug_blocks_release_readiness(self):
        result = MODULE.classify(
            payload(
                item(
                    bugs=[
                        {"id": "BUG-1", "serialNumber": "BUG-1", "status": "处理中"}
                    ]
                )
            )
        )
        self.assertFalse(result["releaseReady"])
        self.assertIn(
            "Bug BUG-1未关闭：处理中",
            result["C_selectedIncomplete"][0]["reasons"],
        )

    def test_safe_readiness_gap_can_persist_draft_but_cross_project_cannot(self):
        safe = MODULE.classify(payload(item(testTasks=[{
            "id": "TEST-1", "developmentTaskId": "DEV-1", "status": "处理中",
            "testMode": "formal-plan", "hasRequiredCases": False,
        }])))
        self.assertTrue(safe["canPersistDraft"])
        self.assertFalse(safe["releaseReady"])

        unsafe = MODULE.classify(payload(item(projectId="P-2")))
        self.assertFalse(unsafe["canPersistDraft"])

    def test_exceptional_scope_does_not_require_iteration(self):
        requirement = item(
            iterationId="",
            formallyInIteration=False,
            formallyInExceptionalScope=True,
        )
        result = MODULE.classify(
            {
                "projectId": "P-1",
                "scopeMode": "exceptional",
                "exceptionalReason": "热修复",
                "selectedRequirementIds": ["REQ-1"],
                "iterationRequirements": [requirement],
            }
        )
        self.assertTrue(result["releaseReady"])
        self.assertEqual(result["iterationId"], "")


if __name__ == "__main__":
    unittest.main()
