from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPTS = Path(__file__).parents[1] / "skills" / "yunxiao-release-operations" / "scripts"
sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location(
    "execute_test_pipeline", SCRIPTS / "execute_test_pipeline.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def candidates():
    return {
        "schemaVersion": "oneos.test-pipeline-candidates/v1",
        "result": "ready",
        "projectId": "PROJECT-1",
        "scopeHash": "scope-hash",
        "candidateCount": 1,
        "candidates": [{
            "pipelineId": "PIPE-1",
            "pipelineName": "oneos-web-test",
            "baseline": {"status": "verified", "value": {"revision": "a" * 40}},
            "pendingChanges": {
                "status": "calculated",
                "components": [{"componentId": "web", "currentHead": "b" * 40}],
            },
            "definitionEvidence": {"sources": [{"repository": "REPO-1", "branch": "develop"}]},
        }],
    }


class ExecuteTestPipelineTests(unittest.TestCase):
    def test_build_plan_binds_ready_candidate_and_test_gate(self):
        plan = MODULE.build_plan(candidates())
        self.assertEqual(plan["releaseGateStage"], "test-pipeline")
        self.assertEqual(plan["actions"][0]["args"], ["--pipeline-id", "PIPE-1"])
        validated = MODULE.gateway.validate_plan(plan)
        self.assertEqual(validated["testPipelineEvidence"]["candidateCount"], 1)
        self.assertEqual(validated["releaseHandoffs"], [])

    def test_non_ready_candidate_is_blocked_before_plan(self):
        value = candidates()
        value["result"] = "needs-selection"
        with self.assertRaisesRegex(MODULE.core.AdapterError, "唯一READY"):
            MODULE.build_plan(value)

    def test_pipeline_selection_cannot_override_structural_candidate(self):
        with self.assertRaisesRegex(MODULE.core.AdapterError, "未命中"):
            MODULE.validate_candidates(candidates(), "PIPE-OTHER")

    def test_monitor_reports_success_after_running(self):
        values = [
            {"status": "RUNNING", "pipelineRunId": "RUN-1"},
            {"status": "SUCCESS", "pipelineRunId": "RUN-1"},
        ]

        def reader(_call):
            return values.pop(0)

        with patch.object(MODULE.time, "sleep", return_value=None):
            result = MODULE.monitor(
                "aliyun", "PIPE-1", "RUN-1", reader=reader,
                timeout_seconds=5, interval_seconds=1,
            )
        self.assertEqual(result["result"], "succeeded")

    def test_monitor_keeps_failure_evidence_separate(self):
        result = MODULE.monitor(
            "aliyun", "PIPE-1", "RUN-1",
            reader=lambda _call: {"status": "FAILED", "stages": [{"status": "FAILED", "logUrl": "https://log"}]},
            timeout_seconds=5, interval_seconds=1,
        )
        self.assertEqual(result["result"], "failed")
        self.assertTrue(result["failureEvidence"]["logRead"])


if __name__ == "__main__":
    unittest.main()
