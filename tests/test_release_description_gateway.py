from __future__ import annotations

import importlib.util
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from tests.handoff_fixtures import make_bundle


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


def create_plan(description, include_managed=True, include_handoffs=True):
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
    plan = {
        "schema": MODULE.PLAN_SCHEMA,
        "label": "release description test",
        "authority": "apply",
        "idempotencyKey": "release-description-test",
        "guards": [read_call()],
        "actions": actions,
        "verifications": [read_call()],
    }
    if include_handoffs:
        plan["releaseGateStage"] = "release"
        plan["releaseHandoffs"] = [make_bundle("release")]
    return plan


def operation_plan(operation, action_args, *, release_gate=False):
    plan = {
        "schema": MODULE.PLAN_SCHEMA,
        "label": "operation gate test",
        "authority": "execute",
        "idempotencyKey": "operation-gate-test",
        "guards": [read_call()],
        "actions": [{"operation": operation, "args": action_args}],
        "verifications": [read_call()],
    }
    if release_gate:
        plan["releaseGateStage"] = "release"
        plan["releaseHandoffs"] = [make_bundle("release")]
    return plan


def attach_release_merge_plan(plan):
    bundle = plan["releaseHandoffs"][0]
    release_plan = {
        "schemaVersion": "oneos.release-merge-plan/v1",
        "status": "READY", "blockers": [], "releaseTaskId": "REL-1",
        "releaseHandoffs": plan["releaseHandoffs"],
        "items": [{"repositoryId": "REPO-1", "pipelineId": "PROD-PIPE", "sources": [{
            "handoffScope": bundle["manifest"]["scope"],
            "handoffDeliveryVersion": bundle["deliveryVersion"],
            "sourceWorkItemIds": [bundle["developmentReceipt"]["taskId"]],
            "testEvidenceIds": [bundle["qaReceipt"]["taskId"]],
            "exactCommitIds": ["abc123"],
        }]}],
    }
    release_plan["planHash"] = MODULE.stable_hash(release_plan)
    plan["releaseMergePlan"] = release_plan
    plan["guards"].append({
        "operation": "projex-get-workitem", "args": ["--id", "REL-1"],
        "expect": {"id": "REL-1"},
    })
    return plan


def attach_multi_item_release_merge_plan(plan):
    bundle = plan["releaseHandoffs"][0]

    def source(name, mr):
        return {
            "handoffScope": bundle["manifest"]["scope"],
            "handoffDeliveryVersion": bundle["deliveryVersion"],
            "sourceWorkItemIds": [bundle["developmentReceipt"]["taskId"]],
            "testEvidenceIds": [bundle["qaReceipt"]["taskId"]],
            "sourceBranch": f"feature/{name}", "sourceHead": f"HEAD-{name}",
            "exactCommitIds": [f"COMMIT-{name}"], "mr": mr,
        }

    release_plan = {
        "schemaVersion": "oneos.release-merge-plan/v1",
        "status": "READY", "blockers": [], "releaseTaskId": "REL-1",
        "releaseHandoffs": plan["releaseHandoffs"],
        "items": [
            {"repositoryId": "REPO-A", "pipelineId": "PIPE-A",
             "targetBranch": "main-A", "appName": "APP-A",
             "appCodeRepoSn": "APP-REPO-A", "releaseWorkflowSn": "WF-A",
             "releaseStageSn": "STAGE-A", "sources": [source("A", "MR-A")]},
            {"repositoryId": "REPO-B", "pipelineId": "PIPE-B",
             "targetBranch": "main-B", "appName": "APP-B",
             "appCodeRepoSn": "APP-REPO-B", "releaseWorkflowSn": "WF-B",
             "releaseStageSn": "STAGE-B", "sources": [source("B", "MR-B")]},
        ],
    }
    release_plan["planHash"] = MODULE.stable_hash(release_plan)
    plan["releaseMergePlan"] = release_plan
    plan["guards"].append({
        "operation": "projex-get-workitem", "args": ["--id", "REL-1"],
        "expect": {"id": "REL-1"},
    })
    return plan


VISIBLE_DESCRIPTION = "OneOS V1.0更新日志：\n\n【新功能】\n1「任务工单」支持创建工单。"


class ReleaseDescriptionGatewayTests(unittest.TestCase):
    def test_codeup_body_file_is_validated_and_hash_bound(self):
        with tempfile.TemporaryDirectory() as directory:
            body_path = Path(directory) / "body.json"
            body = {"branch": "release/ONEOS-995-candidate",
                    "commit_message": "ONEOS-995 精确候选",
                    "actions": [{"action": "update", "content": "source",
                                 "file_path": "src/example.txt", "previous_path": ""}]}
            raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
            body_path.write_bytes(raw)
            action = {"operation": "codeup-commit-multiple-files",
                      "args": ["--repository-id", "123", "--body-file", str(body_path)]}
            MODULE.validate_codeup_file_commit(action, "execute")
            self.assertEqual(action["bodySha256"], hashlib.sha256(raw).hexdigest())
            body["actions"][0]["action"] = "delete"
            body_path.write_text(json.dumps(body, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(MODULE.core.AdapterError, "create/update"):
                MODULE.validate_codeup_file_commit({"operation": action["operation"],
                                                    "args": action["args"]}, "execute")

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

    def test_release_task_without_handoff_gate_is_rejected(self):
        with self.assertRaisesRegex(MODULE.core.AdapterError, "releaseGateStage"):
            MODULE.validate_plan(create_plan(VISIBLE_DESCRIPTION, include_handoffs=False))

    def test_managed_comment_schema_is_rejected_when_wrong(self):
        plan = create_plan(VISIBLE_DESCRIPTION, include_managed=False)
        plan["actions"].append(managed_comment("oneos.release-batch/v1"))
        with self.assertRaisesRegex(MODULE.core.AdapterError, "schemaVersion"):
            MODULE.validate_plan(plan)

    def test_release_handoff_is_rechecked_in_preflight_and_apply(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan_path = root / "plan.json"
            preflight_path = root / "preflight.json"
            plan_path.write_text(
                json.dumps(create_plan(VISIBLE_DESCRIPTION), ensure_ascii=False),
                encoding="utf-8",
            )
            gate_calls = []
            readback = {"id": "TASK-ID", "status": "ready"}
            with patch.object(MODULE.core, "find_aliyun", return_value="aliyun"), \
                    patch.object(MODULE.core, "require_auth_env", return_value={}), \
                    patch.object(MODULE.core, "current_user", return_value={"id": "USER-1"}), \
                    patch.object(MODULE.core, "output_dir", return_value=root), \
                    patch.object(MODULE, "verify_release_handoffs",
                                 side_effect=lambda executable, bundles: gate_calls.append(executable)), \
                    patch.object(MODULE, "execute_read", return_value=readback), \
                    patch.object(MODULE.core, "run_devops", return_value={"result": {"id": "REL-1"}}):
                MODULE.cmd_preflight(SimpleNamespace(
                    plan=str(plan_path), output=str(preflight_path),
                ))
                MODULE.cmd_apply(SimpleNamespace(
                    preflight=str(preflight_path), receipt=None,
                ))
            self.assertEqual(gate_calls, ["aliyun", "aliyun"])

    def test_production_pipeline_cannot_self_declare_test_exception(self):
        plan = operation_plan(
            "flow-create-pipeline-run", ["--pipeline-id", "PROD-PIPE"],
        )
        plan["releaseGateStage"] = "test-pipeline"
        with self.assertRaisesRegex(MODULE.core.AdapterError, "候选流水线回执"):
            MODULE.validate_plan(plan)

    def test_refuse_and_incident_record_remain_available_for_risk_reduction(self):
        refused = operation_plan(
            "flow-refuse-pipeline-validate", ["--pipeline-run-id", "RUN-1"],
        )
        self.assertEqual(MODULE.validate_plan(refused)["releaseHandoffs"], [])
        incident = operation_plan(
            "projex-create-workitem-comment",
            ["--id", "REL-1", "--content", "【发布事故记录】" + json.dumps({
                "schemaVersion": "oneos.release-incident/v1",
                "releaseTaskId": "REL-1", "detectedAt": "2026-09-15T08:00:00Z",
            }, ensure_ascii=False, separators=(",", ":"))],
        )
        self.assertEqual(MODULE.validate_plan(incident)["releaseHandoffs"], [])

    def test_production_action_must_bind_current_release_merge_plan(self):
        plan = operation_plan(
            "flow-create-pipeline-run", ["--pipeline-id", "PROD-PIPE"],
            release_gate=True,
        )
        with self.assertRaisesRegex(MODULE.core.AdapterError, "releaseMergePlan"):
            MODULE.validate_plan(plan)

    def test_production_action_accepts_exact_frozen_source_binding(self):
        plan = attach_release_merge_plan(operation_plan(
            "flow-create-pipeline-run", ["--pipeline-id", "PROD-PIPE"],
            release_gate=True,
        ))
        validated = MODULE.validate_plan(plan)
        self.assertEqual(validated["releaseMergePlan"]["releaseTaskId"], "REL-1")

    def test_production_action_rejects_wrong_scope_inside_merge_plan(self):
        plan = attach_release_merge_plan(operation_plan(
            "flow-create-pipeline-run", ["--pipeline-id", "PROD-PIPE"],
            release_gate=True,
        ))
        source = plan["releaseMergePlan"]["items"][0]["sources"][0]
        source["handoffScope"] = {**source["handoffScope"], "projectId": "PROJECT-OTHER"}
        plan["releaseMergePlan"]["planHash"] = MODULE.stable_hash({
            key: value for key, value in plan["releaseMergePlan"].items()
            if key != "planHash"
        })
        with self.assertRaisesRegex(MODULE.core.AdapterError, "scope"):
            MODULE.validate_plan(plan)

    def test_production_action_rejects_pipeline_outside_frozen_plan(self):
        plan = attach_release_merge_plan(operation_plan(
            "flow-create-pipeline-run", ["--pipeline-id", "PROD-OTHER"],
            release_gate=True,
        ))
        with self.assertRaisesRegex(MODULE.core.AdapterError, "pipelineId"):
            MODULE.validate_plan(plan)

    def test_production_action_rejects_repository_outside_frozen_plan(self):
        plan = attach_release_merge_plan(operation_plan(
            "codeup-create-branch",
            ["--repository-id", "REPO-OTHER", "--branch", "release/ONEOS-1"],
            release_gate=True,
        ))
        with self.assertRaisesRegex(MODULE.core.AdapterError, "repositoryId"):
            MODULE.validate_plan(plan)

    def test_multi_item_plan_accepts_each_exact_pipeline_tuple(self):
        plan = operation_plan(
            "flow-create-pipeline-run", ["--pipeline-id", "PIPE-A"],
            release_gate=True,
        )
        plan["actions"].append({
            "operation": "flow-create-pipeline-run",
            "args": ["--pipeline-id", "PIPE-B"],
        })
        validated = MODULE.validate_plan(attach_multi_item_release_merge_plan(plan))
        self.assertEqual(len(validated["actions"]), 2)

    def test_repository_cannot_use_merge_request_from_another_item(self):
        plan = attach_multi_item_release_merge_plan(operation_plan(
            "codeup-merge-change-request",
            ["--repository-id", "REPO-A", "--local-id", "MR-B"],
            release_gate=True,
        ))
        with self.assertRaisesRegex(MODULE.core.AdapterError, "MR"):
            MODULE.validate_plan(plan)

    def test_app_cannot_use_workflow_or_branch_from_another_item(self):
        plan = attach_multi_item_release_merge_plan(operation_plan(
            "app-stack-execute-change-request-release-stage",
            ["--app-name", "APP-A", "--release-workflow-sn", "WF-B",
             "--release-stage-sn", "STAGE-B"],
            release_gate=True,
        ))
        with self.assertRaisesRegex(MODULE.core.AdapterError, "releaseWorkflowSn"):
            MODULE.validate_plan(plan)

        plan = attach_multi_item_release_merge_plan(operation_plan(
            "app-stack-execute-change-request-release-stage",
            ["--app-name", "APP-A", "--release-workflow-sn", "WF-A",
             "--release-stage-sn", "STAGE-A",
             "--params", json.dumps({"branch": "feature/B"})],
            release_gate=True,
        ))
        with self.assertRaisesRegex(MODULE.core.AdapterError, "分支/版本"):
            MODULE.validate_plan(plan)

    def test_branch_and_version_must_match_one_source_tuple(self):
        plan = attach_multi_item_release_merge_plan(operation_plan(
            "flow-create-pipeline-run",
            ["--pipeline-id", "PIPE-A", "--params", json.dumps({
                "branch": "feature/A", "revision": "HEAD-A2",
            })],
            release_gate=True,
        ))
        item = plan["releaseMergePlan"]["items"][0]
        second = {**item["sources"][0], "sourceBranch": "feature/A2",
                  "sourceHead": "HEAD-A2", "exactCommitIds": ["COMMIT-A2"]}
        item["sources"].append(second)
        plan["releaseMergePlan"]["planHash"] = MODULE.stable_hash({
            key: value for key, value in plan["releaseMergePlan"].items()
            if key != "planHash"
        })
        with self.assertRaisesRegex(MODULE.core.AdapterError, "pipelineId"):
            MODULE.validate_plan(plan)


if __name__ == "__main__":
    unittest.main()
