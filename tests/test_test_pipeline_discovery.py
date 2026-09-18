from __future__ import annotations

import os
from pathlib import Path
import sys
import unittest

SCRIPTS = Path(__file__).parents[1] / "skills/yunxiao-release-operations/scripts"
sys.path.insert(0, str(SCRIPTS))
import discover_test_pipelines as D


PROJECT = "PROJ-1"
REPO = "repo-1"
BRANCH = "develop"
BASE = "a" * 40
HEAD = "b" * 40


def scope():
    return {"projectId": PROJECT, "components": [{
        "componentId": "web", "repositoryId": REPO, "targetBranch": BRANCH,
        "deploymentTarget": "web-test",
    }]}


class DiscoveryTests(unittest.TestCase):
    def pipeline(self, name="web-flow"):
        return {"id": "P-1", "name": name, "projectId": PROJECT,
                "environment": "test", "deploymentTarget": "web-test",
                "pipelineConfig": {"sources": [{"data": {"repo": REPO, "branch": BRANCH}}]}}

    def reader(self, calls):
        pipeline = self.pipeline()
        def read(call):
            calls.append(call)
            op = call["operation"]
            args = call["args"]
            if op == "flow-list-pipelines":
                page = args[args.index("--page") + 1]
                if page == "1":
                    return [{"id": f"X-{i}"} for i in range(10)]
                return [{"id": "P-1"}]
            if op == "flow-get-pipeline":
                pipeline_id = args[args.index("--pipeline-id") + 1]
                if pipeline_id != "P-1":
                    return {"id": pipeline_id, "name": "other", "projectId": PROJECT, "environment": "prod"}
                return pipeline
            if op == "flow-list-pipeline-runs":
                return [{"pipelineRunId": "RUN-1", "status": "SUCCESS"}]
            if op == "flow-get-pipeline-run":
                return {"pipelineRunId": "RUN-1", "status": "SUCCESS", "completedAt": "2026-09-18T01:00:00Z", "commitId": BASE}
            if op == "codeup-list-commits":
                return [{"id": HEAD}, {"id": BASE}]
            raise AssertionError(op)
        return read

    def test_paginates_and_calculates_pending_changes(self):
        calls = []
        result = D.discover(scope(), self.reader(calls))
        self.assertEqual(result["result"], "ready")
        self.assertEqual(result["pipelinePages"], 2)
        self.assertEqual(result["candidateCount"], 1)
        candidate = result["candidates"][0]
        self.assertEqual(candidate["baselineRevision"], BASE)
        self.assertEqual(candidate["pendingChanges"]["status"], "calculated")
        self.assertEqual(candidate["pendingChanges"]["components"][0]["count"], 1)
        self.assertTrue(any(call["operation"] == "codeup-list-commits" for call in calls))

    def test_name_alone_and_wrong_project_are_rejected(self):
        pipeline = self.pipeline("test-web")
        pipeline["projectId"] = "OTHER"
        result = D.match_pipeline(pipeline, PROJECT, scope()["components"], "test-web")
        self.assertEqual(result["match"], "rejected")
        self.assertTrue(any("项目不匹配" in reason for reason in result["reasons"]))

    def test_prod_environment_is_rejected_even_when_source_matches(self):
        pipeline = self.pipeline()
        pipeline["environment"] = "production"
        result = D.match_pipeline(pipeline, PROJECT, scope()["components"])
        self.assertEqual(result["match"], "rejected")
        self.assertTrue(any("不是test" in reason for reason in result["reasons"]))

    def test_no_sha_baseline_blocks(self):
        calls = []
        reader = self.reader(calls)
        original = reader
        def no_sha(call):
            value = original(call)
            if call["operation"] == "flow-get-pipeline-run":
                value["commitId"] = "artifact-1"
            return value
        result = D.discover(scope(), no_sha)
        self.assertEqual(result["result"], "needs-selection")
        self.assertEqual(result["candidates"][0]["baseline"]["status"], "unavailable")

    def test_duplicate_page_is_rejected(self):
        def duplicate(call):
            if call["operation"] == "flow-list-pipelines":
                return [{"id": "P-1"}]
            raise AssertionError("not reached")
        with self.assertRaises(Exception):
            D.paged(duplicate, "flow-list-pipelines", [], ("pipelines",), 1)


if __name__ == "__main__":
    unittest.main()
