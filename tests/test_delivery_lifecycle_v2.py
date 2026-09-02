from __future__ import annotations

import importlib.util
import argparse
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]


def load_module(name: str, relative: str):
    path = ROOT / relative
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


BRANCH = load_module(
    "resolve_branch_base",
    "skills/yunxiao-development-delivery/scripts/resolve_branch_base.py",
)
ROUTER = load_module(
    "route_lifecycle_intent",
    "skills/yunxiao-development-delivery/scripts/route_lifecycle_intent.py",
)
LEDGER = load_module(
    "yunxiao_cli_delivery_ledger",
    "skills/yunxiao-development-delivery/scripts/yunxiao_cli_delivery_ledger.py",
)
SUBMISSION = load_module(
    "yunxiao_cli_submission_attempt",
    "skills/yunxiao-development-delivery/scripts/yunxiao_cli_submission_attempt.py",
)
BUG_BATCH = load_module(
    "yunxiao_cli_bug_batch_v2",
    "skills/yunxiao-development-delivery/scripts/yunxiao_cli_bug_batch.py",
)


def chinese_summary():
    return {
        "修改内容": "修复登录状态判断并补充空值处理",
        "修改原因": "旧逻辑会把过期状态误判为有效",
        "影响范围": "仅影响登录校验模块",
        "验证情况": "已执行单元测试并通过",
    }


class DeliveryLifecycleV2Tests(unittest.TestCase):
    def test_question_is_read_only_but_clear_action_creates_temporary_mapping(self):
        audit = ROUTER.route("能不能修改这段代码？", {})
        self.assertEqual(audit["action"], "audit")
        action = ROUTER.route("帮我改造这个功能", {})
        self.assertEqual(action["action"], "implement")
        self.assertTrue(action["mayCreateTempBranch"])

    def test_temporary_submit_can_resume_from_verified_local_ledger(self):
        value = ROUTER.route(
            "提交代码",
            {"deliveryUnitId": "TEMPDEV-1", "temporaryLedgerVerified": True},
        )
        self.assertFalse(value["requiresItemResolution"])

    def test_unrelated_current_branch_is_ignored(self):
        value = BRANCH.resolve(
            {
                "schemaVersion": BRANCH.REQUEST_SCHEMA,
                "intent": "temporary",
                "repositoryId": "R1",
                "targetDeliveryUnitId": "TEMPDEV-1",
                "workingTree": "clean",
                "currentBranch": "feature/OLD-1",
                "currentCommit": "old",
                "currentBranchDeliveryUnitId": "OLD-1",
                "integrationBase": {
                    "verified": True,
                    "branch": "develop",
                    "commit": "base123",
                    "evidenceId": "READBACK-1",
                },
            }
        )
        self.assertEqual(value["action"], "create_branch")
        self.assertEqual(value["baseCommit"], "base123")
        self.assertTrue(value["ignoredCurrentBranch"])

    def test_test_bug_prefers_exact_deployed_commit(self):
        value = BRANCH.resolve(
            {
                "schemaVersion": BRANCH.REQUEST_SCHEMA,
                "intent": "test_bug",
                "repositoryId": "R1",
                "targetDeliveryUnitId": "BUG-1",
                "targetWorkItemId": "ONEOS-1",
                "workingTree": "clean",
                "testDeployment": {
                    "verified": True,
                    "branch": "test",
                    "commit": "tested123",
                    "evidenceId": "FLOW-1",
                },
            }
        )
        self.assertEqual(value["baseCommit"], "tested123")
        self.assertFalse(value["retestRequired"])

    def test_mixed_dirty_blocks_only_repository(self):
        value = BRANCH.resolve(
            {
                "schemaVersion": BRANCH.REQUEST_SCHEMA,
                "intent": "development",
                "repositoryId": "R1",
                "targetDeliveryUnitId": "DU-1",
                "workingTree": "mixed",
            }
        )
        self.assertEqual(value["status"], "blocked")
        self.assertEqual(value["action"], "pause_repository")

    def test_ledger_hash_chain_idempotency_and_tamper_detection(self):
        spec = {
            "eventType": "COMMIT_RECORDED",
            "deliveryUnitId": "DU-1",
            "ledgerOwnerItemId": "ONEOS-1",
            "idempotencyKey": "commit-1",
            "sourceCommitIds": ["abc"],
            "payload": {"changeSummary": chinese_summary()},
        }
        first, created = LEDGER.build_event(spec, [])
        self.assertTrue(created)
        same, created_again = LEDGER.build_event(spec, [first])
        self.assertFalse(created_again)
        self.assertEqual(first["eventId"], same["eventId"])
        second_spec = {
            **spec,
            "eventType": "DEVELOPMENT_COMPLETED",
            "idempotencyKey": "complete-1",
        }
        second, _ = LEDGER.build_event(second_spec, [first])
        self.assertEqual(LEDGER.validate([first, second])["status"], "passed")
        second["payload"]["changed"] = True
        self.assertEqual(LEDGER.validate([first, second])["status"], "blocked")

    def test_ledger_rejects_non_chinese_change_description(self):
        with self.assertRaisesRegex(ValueError, "中文"):
            LEDGER.build_event(
                {
                    "eventType": "COMMIT_RECORDED",
                    "deliveryUnitId": "DU-1",
                    "ledgerOwnerItemId": "ONEOS-1",
                    "idempotencyKey": "bad-1",
                    "payload": {
                        "changeSummary": {
                            "修改内容": "update",
                            "修改原因": "fix",
                            "影响范围": "web",
                            "验证情况": "passed",
                        }
                    },
                },
                [],
            )

    def test_multi_repository_attempt_resumes_without_downgrading_success(self):
        attempt = SUBMISSION.start(
            {
                "deliveryUnitId": "DU-1",
                "idempotencyKey": "submit-1",
                "repositories": [
                    {"repositoryId": "WEB", "branchInstanceId": "B1"},
                    {"repositoryId": "API", "branchInstanceId": "B2"},
                ],
            }
        )
        SUBMISSION.record(attempt, "WEB", "SUCCEEDED", "mr_created", ["c1"], "MR-1", None)
        SUBMISSION.record(attempt, "API", "FAILED", "push", [], None, "network")
        self.assertEqual(attempt["status"], "PARTIAL")
        with self.assertRaisesRegex(ValueError, "不得.*降级"):
            SUBMISSION.record(attempt, "WEB", "FAILED", "retry", [], None, "bad")
        SUBMISSION.record(attempt, "API", "SUCCEEDED", "mr_created", ["c2"], "MR-2", None)
        self.assertEqual(attempt["status"], "SUCCEEDED")

    def test_bug_batch_plan_is_directly_compatible_with_delivery_preflight_schema(self):
        snapshot = {
            "schema": BUG_BATCH.SCHEMA,
            "currentUser": {"id": "U1"},
            "spaceIds": ["S1"],
            "bugs": [{"id": "B1", "serialNumber": "BUG-1", "status": "处理中",
                      "assignedTo": {"id": "U1"}, "verifier": {"id": "Q1"}}],
        }
        snapshot["snapshotHash"] = BUG_BATCH.snapshot_hash(snapshot)
        resolutions = {
            "testPipeline": {"pipelineId": "PIPE-TEST", "environment": "test"},
            "resolutions": [
                {
                    "bugSerialNumber": "BUG-1",
                    "repositoryId": "1001",
                    "sourceBranch": "fix/BUG-1",
                    "sourceHead": "source-head",
                    "targetBranch": "develop",
                    "branchInstanceId": "BR-1",
                    "deliveryUnitId": "DU-BUG-1",
                    "associationMode": "independent_bug",
                    "baseBranch": "develop",
                    "baseCommit": "base-head",
                    "baseEvidenceId": "BASE-1",
                }
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            snapshot_path = Path(directory) / "snapshot.json"
            resolution_path = Path(directory) / "resolutions.json"
            output_path = Path(directory) / "plan.json"
            snapshot_path.write_text(json.dumps(snapshot), encoding="utf-8")
            resolution_path.write_text(json.dumps(resolutions), encoding="utf-8")
            result = BUG_BATCH.cmd_build_plan(
                argparse.Namespace(snapshot=str(snapshot_path), resolutions=str(resolution_path), output=str(output_path))
            )
            self.assertEqual(result, 0)
            plan = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(plan["schema"], "oneos.yunxiao-cli-bug-delivery-plan/v2")
            self.assertEqual(plan["groups"][0]["associationMode"], "unassociated-fix")
            self.assertEqual(plan["groups"][0]["items"][0]["retestIdentity"][:11], "BUG-RETEST-")


if __name__ == "__main__":
    unittest.main()
