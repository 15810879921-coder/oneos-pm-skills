from __future__ import annotations

import importlib.util
import unittest
import copy
from pathlib import Path


ROOT = Path(__file__).parents[1]


def load_module(name: str, relative: str):
    path = ROOT / relative
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


GROUPS = load_module(
    "resolve_release_dependency_groups",
    "skills/yunxiao-release-operations/scripts/resolve_release_dependency_groups.py",
)
PLAN = load_module(
    "build_release_merge_plan",
    "skills/yunxiao-release-operations/scripts/build_release_merge_plan.py",
)
EXECUTE = load_module(
    "execute_release_merge_plan",
    "skills/yunxiao-release-operations/scripts/execute_release_merge_plan.py",
)
BRANCH = load_module(
    "resolve_branch_base_e2e",
    "skills/yunxiao-development-delivery/scripts/resolve_branch_base.py",
)
LEDGER = load_module(
    "delivery_ledger_e2e",
    "skills/yunxiao-development-delivery/scripts/yunxiao_cli_delivery_ledger.py",
)


def build_fixture_plan(value, *args):
    """Synthetic histories for the existing state-machine fixtures, not collector tests."""
    value = copy.deepcopy(value)
    for item in value["items"]:
        for source in item.get("sources", [item]):
            history = source.get("sourceCommitHistory", [])
            for row in history:
                if not row["include"]:
                    row.setdefault("reason", "out-of-scope")
            base = item["targetBaseCommit"]
            ids = [row["commitId"] for row in history]
            if source["branchPurity"] == "contained":
                ids = list(dict.fromkeys(source["exactCommitIds"] + [source["sourceHead"]]))
                source_nodes = {sha: ([ids[index - 1]] if index else []) for index, sha in enumerate(ids)}
                target_nodes = {**source_nodes, base: [ids[-1]]}
            else:
                source_nodes = {base: []}
                for index, sha in enumerate(ids):
                    source_nodes[sha] = [ids[index - 1] if index else base]
                target_nodes = {base: []}
            snapshot = {"schemaVersion": PLAN.coverage.HISTORY_SCHEMA,
                        "repositoryId": item["repositoryId"], "sourceHead": source["sourceHead"],
                        "targetBaseCommit": base}
            for field, head, nodes in [("sourcePages", source["sourceHead"], source_nodes),
                                       ("targetPages", base, target_nodes)]:
                snapshot[field] = [
                    {"request": PLAN.coverage.request(item["repositoryId"], head, 1),
                     "commits": [{"id": sha, "parentIds": parents} for sha, parents in nodes.items()]},
                    {"request": PLAN.coverage.request(item["repositoryId"], head, 2), "commits": []}]
            source["historySnapshot"] = snapshot
            source["branchOwner"] = {"type": "development_task", "workItemId": "DEV-1", "relationEvidenceId": "R1"}
    return PLAN.build(value, *args)


def fixture_proof(attempt, key, revision):
    """State-machine unit fixture; actual Git content is exercised in coverage tests."""
    repo = next(row for row in attempt["repositories"] if row["repositoryKey"] == key)
    proof = {"schemaVersion": PLAN.coverage.COVERAGE_SCHEMA, "planHash": attempt["planHash"],
             "repositoryKey": key, "targetBaseCommit": repo["targetBaseCommit"],
             "revision": revision, "expectedTree": "fixture-tree", "actualTree": "fixture-tree"}
    proof["proofHash"] = PLAN.coverage.digest(proof)
    return proof


def fixture_checks(attempt):
    rows = []
    for repo in attempt["repositories"]:
        key = repo["repositoryKey"]
        target = repo.get("resultTargetCommit") or repo["targetBaseCommit"]
        rows.append({"repositoryKey": key, "targetHeadMatches": True, "testsValid": True,
                     "dependencyComplete": True, "mergeable": True, "exactCommitsContained": True,
                     "currentTargetCommit": target, "candidateRevision": "candidate",
                     "candidateCoverage": fixture_proof(attempt, key, "candidate"),
                     "targetCoverage": fixture_proof(attempt, key, target)})
    return {"repositories": rows}


def record_fixture_merge(attempt, key, status, target, error):
    proof = fixture_proof(attempt, key, target) if status == "success" else None
    return EXECUTE.record_merge(attempt, key, status, target, error, proof)


def plan_input():
    common = {
        "targetBranch": "master",
        "targetBranchVerified": True,
        "testEvidenceIds": ["TEST-1"],
        "pipelineId": "PIPE-1",
        "deploymentTarget": "oneos",
        "targetBaseCommit": "base",
        "dependencyGroupId": "DEP-1",
        "deliveryUnitIds": ["DU-1"],
    }
    return {
        "schemaVersion": PLAN.INPUT_SCHEMA,
        "releaseTaskId": "REL-1",
        "dependencyGroupIds": ["DEP-1"],
        "items": [
            {**common, "repositoryId": "WEB", "componentId": "web",
             "sourceBranch": "feature/A", "sourceHead": "w1",
             "branchPurity": "pure", "pipelineId": "PIPE-WEB",
             "sourceHistoryComplete": True, "sourceHistoryEvidenceId": "H-WEB",
             "sourceCommitHistory": [{"commitId": "w1", "include": True, "evidenceId": "E-W1"}],
             "exactCommitIds": ["w1"]},
            {**common, "repositoryId": "API", "componentId": "api",
             "sourceBranch": "feature/A", "sourceHead": "a1", "exactCommitIds": ["c2"],
             "branchPurity": "mixed", "pipelineId": "PIPE-API",
             "sourceHistoryComplete": True, "sourceHistoryEvidenceId": "H-API",
             "sourceCommitHistory": [
                 {"commitId": "c2", "include": True, "evidenceId": "E-C2"},
                 {"commitId": "a1", "include": False, "evidenceId": "E-A1"},
             ]},
            {**common, "repositoryId": "COMMON", "componentId": "common",
             "sourceBranch": "feature/A", "sourceHead": "m1", "exactCommitIds": ["c3"],
             "branchPurity": "contained", "pipelineId": "PIPE-COMMON",
             "containmentEvidenceId": "CONTAIN-1"},
        ],
    }


class ReleaseMergeLifecycleV2Tests(unittest.TestCase):
    def test_full_task_late_multi_branch_partial_release_scenario(self):
        base_request = {
            "schemaVersion": BRANCH.REQUEST_SCHEMA,
            "intent": "temporary",
            "targetDeliveryUnitId": "TEMPDEV-1",
            "workingTree": "clean",
            "currentBranch": "feature/OLD",
            "currentCommit": "old",
            "currentBranchDeliveryUnitId": "OLD",
            "integrationBase": {"verified": True, "branch": "develop", "commit": "base", "evidenceId": "R1"},
        }
        web_branch = BRANCH.resolve({**base_request, "repositoryId": "WEB"})
        api_branch = BRANCH.resolve({**base_request, "repositoryId": "API"})
        self.assertTrue(web_branch["ignoredCurrentBranch"] and api_branch["ignoredCurrentBranch"])

        summary = {
            "修改内容": "认领临时开发并聚合测试发现的缺陷分支",
            "修改原因": "正式开发任务在代码和测试之后补建",
            "影响范围": "登录页面与认证接口",
            "验证情况": "测试环境已按精确版本复测通过",
        }
        adopted, _ = LEDGER.build_event(
            {"eventType": "DELIVERY_ADOPTED", "deliveryUnitId": "TEMPDEV-1",
             "ledgerOwnerItemId": "DEV-1", "idempotencyKey": "adopt-1",
             "payload": {"changeSummary": summary, "adoptionId": "ADOPT-1",
                         "formalWorkItemId": "DEV-1", "relationEvidenceId": "REL-1"}},
            [],
        )
        aggregated, _ = LEDGER.build_event(
            {"eventType": "DEVELOPMENT_TASK_AGGREGATED", "deliveryUnitId": "TEMPDEV-1",
             "ledgerOwnerItemId": "DEV-1", "idempotencyKey": "aggregate-1",
             "payload": {"changeSummary": summary, "developmentTaskId": "DEV-1",
                         "bugIds": ["BUG-1", "BUG-2"], "branchInstanceIds": ["BR-B1", "BR-B2"]}},
            [adopted],
        )
        self.assertEqual(LEDGER.validate([adopted, aggregated])["status"], "passed")

        value = plan_input()
        value["items"][0]["sources"] = [
            {"sourceBranch": "tempdev/TEMPDEV-1", "sourceHead": "h1",
             "testEvidenceIds": ["TW"], "sourceWorkItemIds": ["DEV-1"],
             "deliveryUnitIds": ["TEMPDEV-1"], "branchPurity": "pure",
             "sourceHistoryComplete": True, "sourceHistoryEvidenceId": "H1",
             "sourceCommitHistory": [{"commitId": "h1", "include": True, "evidenceId": "EH1"}],
             "exactCommitIds": ["h1"]},
            {"sourceBranch": "fix/BUG-1", "sourceHead": "h2",
             "testEvidenceIds": ["TB1"], "sourceWorkItemIds": ["BUG-1"],
             "deliveryUnitIds": ["DU-B1"], "branchPurity": "pure",
             "sourceHistoryComplete": True, "sourceHistoryEvidenceId": "H2",
             "sourceCommitHistory": [{"commitId": "h2", "include": True, "evidenceId": "EH2"}],
             "exactCommitIds": ["h2"]},
        ]
        merge_plan = build_fixture_plan(value)
        self.assertEqual(merge_plan["status"], "READY")
        self.assertEqual(merge_plan["items"][0]["action"], "BUILD_CLEAN_CANDIDATE")
        attempt = EXECUTE.init(merge_plan)
        EXECUTE.preflight(attempt, fixture_checks(attempt))
        pending = [repo["repositoryKey"] for repo in attempt["repositories"] if repo["mergeStatus"] != "SUCCESS"]
        record_fixture_merge(attempt, pending[0], "success", "target-1", None)
        record_fixture_merge(attempt, pending[1], "failed", None, "temporary conflict")
        self.assertEqual(attempt["state"], "PARTIAL_TARGET_MERGE")
        EXECUTE.preflight(attempt, fixture_checks(attempt))
        record_fixture_merge(attempt, pending[1], "success", "target-2", None)
        EXECUTE.start_deployment(attempt)
        EXECUTE.record_deployment(attempt, "failed", None)
        EXECUTE.start_deployment(attempt)
        EXECUTE.record_deployment(attempt, "success", "PROD-V2")
        self.assertEqual(attempt["state"], "DEPLOYED")

    def test_dependency_groups_require_verified_edges(self):
        result = GROUPS.resolve(
            {
                "schemaVersion": GROUPS.INPUT_SCHEMA,
                "items": [{"itemId": "A"}, {"itemId": "B"}, {"itemId": "C"}],
                "edges": [
                    {"from": "A", "to": "B", "type": "api", "verified": True, "evidenceId": "E1"}
                ],
            }
        )
        self.assertEqual(result["status"], "passed")
        self.assertEqual(sorted(len(group["itemIds"]) for group in result["groups"]), [1, 2])

    def test_merge_plan_selects_pure_mixed_and_contained_actions(self):
        result = build_fixture_plan(plan_input())
        self.assertEqual(result["status"], "READY")
        self.assertEqual(
            [item["action"] for item in result["items"]],
            ["MERGE_SOURCE_BRANCH", "BUILD_CLEAN_CANDIDATE", "ALREADY_CONTAINED"],
        )
        revised = build_fixture_plan(plan_input(), result, "目标分支更新后重新冻结")
        self.assertEqual(revised["mergePlanVersion"], 2)
        self.assertEqual(revised["previousMergePlanId"], result["mergePlanId"])
        with self.assertRaisesRegex(ValueError, "revisionReason"):
            build_fixture_plan(plan_input(), result)

    def test_multiple_bug_branches_become_one_clean_repository_candidate(self):
        value = plan_input()
        value["items"] = [
            {
                "repositoryId": "WEB",
                "componentId": "web",
                "targetBranch": "master",
                "targetBranchVerified": True,
                "targetBaseCommit": "base",
                "deploymentTarget": "oneos-web",
                "pipelineId": "PIPE-WEB",
                "dependencyGroupId": "DEP-1",
                "sources": [
                    {"sourceBranch": "fix/BUG-1", "sourceHead": "h1",
                     "testEvidenceIds": ["T1"], "sourceWorkItemIds": ["BUG-1"],
                     "deliveryUnitIds": ["DU-B1"], "branchPurity": "pure", "mr": "MR-1",
                     "sourceHistoryComplete": True, "sourceHistoryEvidenceId": "H1",
                     "sourceCommitHistory": [{"commitId": "h1", "include": True, "evidenceId": "EH1"}],
                     "exactCommitIds": ["h1"]},
                    {"sourceBranch": "fix/BUG-2", "sourceHead": "h2",
                     "testEvidenceIds": ["T2"], "sourceWorkItemIds": ["BUG-2"],
                     "deliveryUnitIds": ["DU-B2"], "branchPurity": "pure", "mr": "MR-2",
                     "sourceHistoryComplete": True, "sourceHistoryEvidenceId": "H2",
                     "sourceCommitHistory": [{"commitId": "h2", "include": True, "evidenceId": "EH2"}],
                     "exactCommitIds": ["h2"]},
                ],
            }
        ]
        result = build_fixture_plan(value)
        self.assertEqual(result["status"], "READY")
        self.assertEqual(result["items"][0]["action"], "BUILD_CLEAN_CANDIDATE")
        self.assertEqual(result["items"][0]["exactCommitIds"], ["h1", "h2"])
        self.assertEqual(result["items"][0]["deliveryUnitIds"], ["DU-B1", "DU-B2"])

    def test_merge_plan_blocks_silently_omitted_intermediate_commit(self):
        value = plan_input()
        source = value["items"][0]
        source.update({
            "sourceHead": "c3",
            "exactCommitIds": ["c1", "c3"],
            "sourceCommitHistory": [
                {"commitId": "c1", "include": True, "evidenceId": "E1"},
                {"commitId": "c2", "include": True, "evidenceId": "E2"},
                {"commitId": "c3", "include": True, "evidenceId": "E3"},
            ],
        })
        result = build_fixture_plan(value)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertTrue(any("不闭合" in blocker and "c2" in blocker for blocker in result["blockers"]))

    def test_mixed_branch_allows_only_evidenced_exclusion(self):
        value = plan_input()
        source = value["items"][1]
        source.update({
            "sourceHead": "c3",
            "exactCommitIds": ["c1", "c3"],
            "sourceCommitHistory": [
                {"commitId": "c1", "include": True, "evidenceId": "E1"},
                {"commitId": "outside", "include": False, "evidenceId": "OUTSIDE-1"},
                {"commitId": "c3", "include": True, "evidenceId": "E3"},
            ],
        })
        result = build_fixture_plan(value)
        self.assertEqual(result["status"], "READY")
        self.assertEqual(result["items"][1]["exactCommitIds"], ["c1", "c3"])

    def test_partial_merge_must_resume_before_deploy_and_deploy_can_retry(self):
        plan = build_fixture_plan(plan_input())
        attempt = EXECUTE.init(plan)
        EXECUTE.preflight(attempt, fixture_checks(attempt))
        keys = [repo["repositoryKey"] for repo in attempt["repositories"] if repo["action"] != "ALREADY_CONTAINED"]
        record_fixture_merge(attempt, keys[0], "success", "target-web", None)
        record_fixture_merge(attempt, keys[1], "failed", None, "conflict")
        self.assertEqual(attempt["state"], "PARTIAL_TARGET_MERGE")
        with self.assertRaisesRegex(ValueError, "全部.*预检|全部目标分支"):
            EXECUTE.start_deployment(attempt)
        EXECUTE.preflight(attempt, fixture_checks(attempt))
        record_fixture_merge(attempt, keys[1], "success", "target-api", None)
        self.assertEqual(attempt["state"], "TARGETS_READY")
        EXECUTE.start_deployment(attempt)
        EXECUTE.record_deployment(attempt, "failed", None)
        self.assertEqual(attempt["state"], "MERGED_NOT_DEPLOYED")
        EXECUTE.start_deployment(attempt)
        self.assertEqual(attempt["deployment"]["attemptNo"], 2)
        EXECUTE.record_deployment(attempt, "success", "PROD-V1")
        self.assertEqual(attempt["state"], "DEPLOYED")

    def test_partial_merge_can_be_reverted_without_touching_contained_code(self):
        plan = build_fixture_plan(plan_input())
        attempt = EXECUTE.init(plan)
        EXECUTE.preflight(attempt, fixture_checks(attempt))
        keys = [repo["repositoryKey"] for repo in attempt["repositories"] if repo["action"] != "ALREADY_CONTAINED"]
        record_fixture_merge(attempt, keys[0], "success", "target-web", None)
        record_fixture_merge(attempt, keys[1], "failed", None, "conflict")
        EXECUTE.record_revert(attempt, keys[0], "reverted-web")
        self.assertEqual(attempt["state"], "REVERTED")


if __name__ == "__main__":
    unittest.main()
