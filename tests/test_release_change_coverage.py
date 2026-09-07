from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(os.environ.get("ONEOS_RELEASE_TEST_SCRIPTS",
               str(Path(__file__).parents[1] / "skills/yunxiao-release-operations/scripts")))
sys.path.insert(0, str(SCRIPTS))
import validate_release_change_coverage as C
import build_release_merge_plan as P
import execute_release_merge_plan as E


class CoverageTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="oneos-coverage-test-")
        self.addCleanup(self.directory.cleanup)
        self.repo = Path(self.directory.name)
        self.env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        self.env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
        self.git("init")
        self.git("config", "user.name", "Coverage Test")
        self.git("config", "user.email", "coverage@example.invalid")
        self.base = self.commit("root.txt", b"base\n", "base")
        self.a = self.commit("a.txt", b"A\n", "A")
        self.b = self.commit("b.txt", b"B\n", "B")
        self.c = self.commit("c.txt", b"C\n", "C")

    def git(self, *args):
        p = subprocess.run(["git", "-C", str(self.repo), "-c", "core.hooksPath=" + os.devnull,
                            "-c", "commit.gpgsign=false", *args], env=self.env, capture_output=True)
        if p.returncode:
            raise AssertionError(p.stderr.decode(errors="replace"))
        return p.stdout.decode().strip()

    def commit(self, path, contents, message):
        (self.repo / path).write_bytes(contents)
        self.git("add", "--", path)
        self.git("commit", "-m", message)
        return self.git("rev-parse", "HEAD")

    def reader(self, call):
        args = call["args"]
        head = args[args.index("--ref-name") + 1]
        page = int(args[args.index("--page") + 1])
        rows = []
        for line in self.git("rev-list", "--parents", head).splitlines():
            ids = line.split()
            rows.append({"id": ids[0], "parentIds": ids[1:]})
        return rows[(page - 1) * 100:page * 100]

    def tree_entries(self, revision):
        entries = []
        for row in self.git("ls-tree", "-z", revision).split("\0"):
            if not row:
                continue
            metadata, name = row.split("\t", 1)
            mode, kind, sha = metadata.split()
            entries.append({"mode": mode, "type": kind, "id": sha, "name": name, "path": name})
        return entries

    def test_official_tree_does_not_require_candidate_commit_locally(self):
        plan = P.build(self.data())
        remote_only = "f" * 40
        calls = []
        def reader(call):
            calls.append(call)
            return self.tree_entries(self.c)
        proof = C.verify_tree(plan, plan["items"][0], self.repo, remote_only, reader)
        self.assertEqual(proof["revision"], remote_only)
        self.assertEqual(len(calls), 1)
        C.validate_proof(proof, plan["planHash"], C.repository_key(plan["items"][0]), self.base, remote_only)

    def test_root_tree_hash_covers_nested_content_and_git_sort_order(self):
        (self.repo / "a").mkdir()
        self.commit("a/中文.txt", b"nested\n", "nested")
        self.commit("a.file", b"sibling\n", "tree prefix ordering")
        rows = self.tree_entries("HEAD")
        expected = self.git("rev-parse", "HEAD^{tree}")
        self.assertEqual(C.root_tree_hash(list(reversed(rows))), expected)
        self.assertNotEqual(C.root_tree_hash(rows[:-1]), expected)
        with self.assertRaises(ValueError):
            C.root_tree_hash(rows + [rows[0]])

    def data(self, base=None):
        base = base or self.base
        history = C.collect("R", self.c, base, self.reader)
        return {"schemaVersion": P.INPUT_SCHEMA, "releaseTaskId": "REL-TEST",
                "dependencyGroupIds": ["DEP-TEST"], "items": [{
                    "repositoryId": "R", "componentId": "web", "targetBranch": "production",
                    "targetBranchVerified": True, "targetBaseCommit": base,
                    "deploymentTarget": "isolated-test", "pipelineId": "NO-LIVE-PIPELINE",
                    "dependencyGroupId": "DEP-TEST", "sourceBranch": "feature/DEV-1",
                    "sourceHead": self.c, "branchPurity": "pure", "exactCommitIds": [self.a, self.b, self.c],
                    "sourceHistoryComplete": True, "sourceHistoryEvidenceId": "official-fixture",
                    "sourceWorkItemIds": ["DELIVERY-1"], "deliveryUnitIds": ["DU-1"],
                    "testEvidenceIds": ["TEST-FIXTURE"], "historySnapshot": history,
                    "branchOwner": {"type": "development_task", "workItemId": "DEV-1", "relationEvidenceId": "REL-1"},
                    "sourceCommitHistory": [{"commitId": sha, "include": True, "evidenceId": "scope-" + sha}
                                            for sha in [self.a, self.b, self.c]]}]}

    def test_history_and_selection_both_omit_middle_commit(self):
        value = self.data()
        item = value["items"][0]
        item["exactCommitIds"].remove(self.b)
        item["sourceCommitHistory"].pop(1)
        result = P.build(value)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertTrue(any(self.b in message for message in result["blockers"]))
        # Removing the same record from the read-back still leaves a detectable parent gap.
        rows = item["historySnapshot"]["sourcePages"][0]["commits"]
        rows[:] = [row for row in rows if row["id"] != self.b]
        self.assertTrue(any("父提交" in message for message in P.build(value)["blockers"]))

    def test_pagination_scope_and_duplicate_pages(self):
        for mutation in ["terminal", "ref", "duplicate"]:
            with self.subTest(mutation=mutation):
                value = self.data()
                pages = value["items"][0]["historySnapshot"]["sourcePages"]
                if mutation == "terminal":
                    pages.pop()
                elif mutation == "ref":
                    pages[0]["request"]["args"][3] = self.base
                else:
                    pages[0]["commits"].append(copy.deepcopy(pages[0]["commits"][0]))
                self.assertEqual(P.build(value)["status"], "BLOCKED")

    def test_real_collector_paginates_and_rejects_repeated_page(self):
        calls = []
        def reader(call):
            calls.append(call)
            return self.reader(call)
        C.collect("R", self.c, self.base, reader)
        self.assertEqual(len(calls), 4)
        with self.assertRaisesRegex(ValueError, "分页重复"):
            C.collect("R", self.c, self.base, lambda call: [{"id": self.a, "parentIds": [self.base]}])

    def test_topology_is_parent_first_even_when_sha_order_is_opposite(self):
        self.assertEqual(C.topological({"a": ["m"], "m": ["z"], "z": []}), ["z", "m", "a"])
        plan = P.build(self.data())
        self.assertEqual(plan["items"][0]["replayOrder"], [self.a, self.b, self.c])

    def test_branch_owner_and_required_dependency(self):
        for owner in [{"type": "delivery", "workItemId": "DELIVERY-1", "relationEvidenceId": "R"},
                      {"type": "independent_bug", "workItemId": "BUG-1", "relationEvidenceId": "R", "relatedWorkItemIds": ["TEST-1"]}]:
            value = self.data()
            value["items"][0]["branchOwner"] = owner
            self.assertEqual(P.build(value)["status"], "BLOCKED")
        value = self.data()
        item = value["items"][0]
        item["branchPurity"] = "mixed"
        item["exactCommitIds"].remove(self.b)
        item["sourceCommitHistory"][1].update(include=False, reason="out-of-scope")
        item["sourceCommitHistory"][2]["requiresCommitIds"] = [self.b]
        self.assertTrue(any("必要依赖" in error for error in P.build(value)["blockers"]))

    def test_missing_and_extra_candidate_content_rejected(self):
        plan = P.build(self.data())
        self.git("checkout", "-b", "missing", self.base)
        self.git("cherry-pick", self.a, self.c)
        with self.assertRaisesRegex(ValueError, "最终文件树"):
            C.verify_tree(plan, plan["items"][0], self.repo, "HEAD")
        self.git("checkout", "-b", "extra", self.c)
        extra = self.commit("extra.txt", b"not in release\n", "extra")
        with self.assertRaisesRegex(ValueError, "最终文件树"):
            C.verify_tree(plan, plan["items"][0], self.repo, extra)

    def test_tree_check_leaves_dirty_checkout_untouched(self):
        plan = P.build(self.data())
        (self.repo / "root.txt").write_text("uncommitted user work", encoding="utf-8")
        (self.repo / "untracked.txt").write_text("preserve", encoding="utf-8")
        before = self.git("status", "--porcelain=v1")
        index = (self.repo / ".git/index").read_bytes()
        proof = C.verify_tree(plan, plan["items"][0], self.repo, self.c)
        self.assertEqual(proof["expectedTree"], self.git("rev-parse", self.c + "^{tree}"))
        self.assertEqual(before, self.git("status", "--porcelain=v1"))
        self.assertEqual(index, (self.repo / ".git/index").read_bytes())

    def test_target_already_contains_parent(self):
        plan = P.build(self.data(self.b))
        self.assertEqual(plan["items"][0]["replayOrder"], [self.c])
        C.verify_tree(plan, plan["items"][0], self.repo, self.c)

    def test_target_ancestor_reverted_is_not_active_content(self):
        self.git("checkout", "-b", "reverted-ancestor", self.a)
        self.git("revert", "--no-edit", self.a)
        target = self.git("rev-parse", "HEAD")
        plan = P.build(self.data(target))
        self.git("cherry-pick", self.b, self.c)
        with self.assertRaisesRegex(ValueError, "等价检查失败"):
            C.verify_tree(plan, plan["items"][0], self.repo, "HEAD")

    def test_contained_still_requires_preflight_and_tree_proof(self):
        data = self.data(self.c)
        data["items"][0]["branchPurity"] = "contained"
        data["items"][0]["containmentEvidenceId"] = "target-history"
        plan = P.build(data)
        attempt = E.init(plan)
        self.assertEqual(attempt["state"], "TARGETS_READY")
        with self.assertRaisesRegex(ValueError, "预检"):
            E.start_deployment(attempt)
        proof = C.verify_tree(plan, plan["items"][0], self.repo, self.c)
        E.preflight(attempt, {"repositories": [{"repositoryKey": C.repository_key(plan["items"][0]),
            "targetHeadMatches": True, "testsValid": True, "dependencyComplete": True,
            "exactCommitsContained": True, "currentTargetCommit": self.c, "targetCoverage": proof}]})
        self.assertTrue(attempt["preflightPassed"])
        E.start_deployment(attempt)

    def test_merge_commit_requires_explicit_parent(self):
        self.git("checkout", "-b", "side", self.base)
        side = self.commit("side.txt", b"side\n", "side")
        self.git("checkout", "-b", "merging", self.c)
        self.git("merge", "--no-ff", "-m", "merge side", side)
        merged = self.git("rev-parse", "HEAD")
        data = self.data()
        item = data["items"][0]
        item["sourceHead"] = merged
        item["historySnapshot"] = C.collect("R", merged, self.base, self.reader)
        item["branchPurity"] = "mixed"
        item["sourceCommitHistory"].extend([
            {"commitId": side, "include": False, "reason": "out-of-scope", "evidenceId": "side represented by merge"},
            {"commitId": merged, "include": True, "evidenceId": "approved merge diff"}])
        item["exactCommitIds"].append(merged)
        self.assertEqual(P.build(data)["status"], "BLOCKED")
        item["sourceCommitHistory"][-1]["replayParent"] = self.c
        plan = P.build(data)
        self.assertEqual(plan["status"], "READY")
        C.verify_tree(plan, plan["items"][0], self.repo, merged)

    def test_equivalent_patch_and_reverted_patch(self):
        self.git("checkout", "-b", "squashed", self.base)
        (self.repo / "a.txt").write_bytes(b"A\n")
        target = self.commit("a.txt", b"A\n", "different sha equivalent A")
        data = self.data(target)
        item = data["items"][0]
        item["branchPurity"] = "mixed"
        item["sourceCommitHistory"][0]["reason"] = "target-equivalent"
        plan = P.build(data)
        self.assertEqual(plan["items"][0]["replayOrder"], [self.b, self.c])
        self.git("cherry-pick", self.b, self.c)
        C.verify_tree(plan, plan["items"][0], self.repo, "HEAD")
        self.git("checkout", "-b", "reverted", target)
        self.git("rm", "a.txt")
        self.git("commit", "-m", "revert equivalent A")
        reverted = self.git("rev-parse", "HEAD")
        data = self.data(reverted)
        data["items"][0]["branchPurity"] = "mixed"
        data["items"][0]["sourceCommitHistory"][0]["reason"] = "target-equivalent"
        plan = P.build(data)
        with self.assertRaisesRegex(ValueError, "等价检查失败"):
            C.verify_tree(plan, plan["items"][0], self.repo, reverted)

    def test_plan_tamper_old_plan_and_bool_only_preflight_rejected(self):
        plan = P.build(self.data())
        tampered = copy.deepcopy(plan)
        tampered["items"][0]["exactCommitIds"].remove(self.b)
        with self.assertRaisesRegex(ValueError, "哈希"):
            E.init(tampered)
        old = copy.deepcopy(plan)
        old.pop("coverageVersion")
        old.pop("planHash")
        old.pop("mergePlanId")
        old["mergePlanId"] = "MERGEPLAN-" + C.digest(old)[:20]
        old["planHash"] = C.digest(old)
        with self.assertRaisesRegex(ValueError, "旧计划"):
            E.init(old)
        attempt = E.init(plan)
        key = attempt["repositories"][0]["repositoryKey"]
        E.preflight(attempt, {"repositories": [{"repositoryKey": key, "targetHeadMatches": True,
                    "testsValid": True, "dependencyComplete": True, "mergeable": True,
                    "currentTargetCommit": self.base}]})
        self.assertFalse(attempt["preflightPassed"])
        legacy = copy.deepcopy(attempt)
        legacy.pop("frozenPlan")
        E.validate_attempt(legacy)  # Historical read-only summary remains available.
        with self.assertRaises(ValueError):
            E.preflight(legacy, {"repositories": []})

    def test_full_offline_plan_candidate_target_and_deployment_state(self):
        plan = P.build(self.data())
        item = plan["items"][0]
        proof = C.verify_tree(plan, item, self.repo, self.c)
        attempt = E.init(plan)
        key = C.repository_key(item)
        check = {"repositoryKey": key, "targetHeadMatches": True, "testsValid": True,
                 "dependencyComplete": True, "mergeable": True, "currentTargetCommit": self.base,
                 "candidateRevision": self.c, "candidateCoverage": proof}
        E.preflight(attempt, {"repositories": [check]})
        self.assertTrue(attempt["preflightPassed"])
        with self.assertRaises(ValueError):
            E.record_merge(attempt, key, "success", self.c, None)
        E.record_merge(attempt, key, "success", self.c, None, proof)
        E.start_deployment(attempt)  # State only; never calls a pipeline.
        self.assertEqual(attempt["state"], "MERGED_NOT_DEPLOYED")
        wrong = copy.deepcopy(proof)
        wrong["revision"] = self.a
        with self.assertRaises(ValueError):
            C.validate_proof(wrong, plan["planHash"], key, self.base, self.c)

    def test_binary_rename_delete_patch_tree(self):
        self.git("checkout", "-b", "binary", self.base)
        self.a = self.commit("binary.dat", bytes(range(256)), "binary")
        self.git("mv", "binary.dat", "renamed.dat")
        self.git("commit", "-m", "rename")
        self.b = self.git("rev-parse", "HEAD")
        self.git("rm", "root.txt")
        self.git("commit", "-m", "delete")
        self.c = self.git("rev-parse", "HEAD")
        plan = P.build(self.data())
        C.verify_tree(plan, plan["items"][0], self.repo, self.c)


if __name__ == "__main__":
    unittest.main()
