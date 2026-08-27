from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path


SCRIPTS = (
    Path(__file__).parents[1]
    / "skills"
    / "yunxiao-release-operations"
    / "scripts"
)
sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location(
    "yunxiao_release_gateway", SCRIPTS / "yunxiao_cli_gateway.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def read_call():
    return {
        "operation": "projex-get-workitem",
        "args": ["--id", "TASK-ID"],
        "expect": None,
    }


def managed_comment(schema="oneos.release-batch/v2"):
    payload = {
        "schemaVersion": schema,
        "scopeHash": "scope-hash",
        "idempotencyKey": "release-prepare-scope-hash",
    }
    return {
        "operation": "projex-create-workitem-comment",
        "args": [
            "--id",
            "${action.0.id}",
            "--content",
            "【发布受管数据】" + json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        ],
    }


def create_plan(description, include_managed=True):
    actions = [
        {
            "operation": "projex-create-workitem",
            "args": [
                "--space-id",
                "PROJECT-ID",
                "--subject",
                "【发版】OneOS V1.0",
                "--workitem-type-id",
                "TYPE-ID",
                "--format-type",
                "MARKDOWN",
                "--description",
                description,
            ],
        }
    ]
    if include_managed:
        actions.append(managed_comment())
    return {
        "schema": MODULE.PLAN_SCHEMA,
        "label": "release description test",
        "authority": "apply",
        "idempotencyKey": "release-description-test",
        "guards": [read_call()],
        "actions": actions,
        "verifications": [read_call()],
    }


VISIBLE_DESCRIPTION = "OneOS V1.0更新日志：\n\n【新功能】\n1「任务工单」支持创建工单。"


class ReleaseDescriptionGatewayTests(unittest.TestCase):
    def test_multiline_business_description_and_managed_comment_pass(self):
        plan = MODULE.validate_plan(create_plan(VISIBLE_DESCRIPTION))
        self.assertEqual(plan["actions"][0]["args"][-1], VISIBLE_DESCRIPTION)

    def test_single_line_release_log_is_rejected(self):
        with self.assertRaisesRegex(MODULE.core.AdapterError, "真实换行"):
            MODULE.validate_plan(
                create_plan("OneOS V1.0更新日志： 【新功能】 1「任务工单」支持创建工单。")
            )

    def test_machine_json_in_description_is_rejected(self):
        polluted = VISIBLE_DESCRIPTION + "\n<!-- YUNXIAO_RELEASE_BATCH_START -->"
        with self.assertRaisesRegex(MODULE.core.AdapterError, "机器JSON"):
            MODULE.validate_plan(create_plan(polluted))

    def test_html_comment_in_non_changelog_description_is_rejected(self):
        polluted = "发布证据\n<!-- YUNXIAO_RELEASE_PRODUCTION_EVIDENCE_START -->"
        with self.assertRaisesRegex(MODULE.core.AdapterError, "机器JSON"):
            MODULE.validate_plan(create_plan(polluted))

    def test_release_task_without_managed_comment_is_rejected(self):
        with self.assertRaisesRegex(MODULE.core.AdapterError, "发布受管数据"):
            MODULE.validate_plan(create_plan(VISIBLE_DESCRIPTION, include_managed=False))

    def test_managed_comment_schema_is_rejected_when_wrong(self):
        plan = create_plan(VISIBLE_DESCRIPTION, include_managed=False)
        plan["actions"].append(managed_comment("oneos.release-batch/v1"))
        with self.assertRaisesRegex(MODULE.core.AdapterError, "schemaVersion"):
            MODULE.validate_plan(plan)


if __name__ == "__main__":
    unittest.main()
