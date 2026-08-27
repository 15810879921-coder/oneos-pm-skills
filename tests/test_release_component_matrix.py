from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT = (
    Path(__file__).parents[1]
    / "skills"
    / "yunxiao-release-operations"
    / "scripts"
    / "validate_release_component_matrix.py"
)
SPEC = importlib.util.spec_from_file_location("validate_release_component_matrix", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def matrix():
    return {
        "releaseCodeItems": [{"itemId": "ONEOS-1", "channel": "Web"}],
        "codeAnchors": [
            {
                "itemId": "ONEOS-1",
                "repositoryId": "REPO-1",
                "sourceBranch": "feature/ONEOS-1",
                "targetBranch": "release",
                "targetBranchVerified": True,
                "deploymentTarget": "oneos-web",
                "commit": "abc123",
                "changedPaths": ["src/page.ts"],
            }
        ],
        "componentMatrix": [
            {
                "repositoryId": "REPO-1",
                "targetBranch": "release",
                "deploymentTarget": "oneos-web",
                "pipelineId": "PIPE-1",
                "pipelineName": "web-release",
                "pipelineRepositoryId": "REPO-1",
                "pipelineTargetBranch": "release",
                "pipelineDeploymentTarget": "oneos-web",
                "environment": "prod",
                "sourceItemIds": ["ONEOS-1"],
            }
        ],
    }


class ReleaseComponentMatrixTests(unittest.TestCase):
    def test_matching_verified_component_passes(self):
        errors, result = MODULE.validate(matrix())
        self.assertEqual(errors, [])
        self.assertEqual(result["status"], "passed")

    def test_unverified_target_branch_blocks(self):
        value = matrix()
        value["codeAnchors"][0]["targetBranchVerified"] = False
        errors, _ = MODULE.validate(value)
        self.assertIn("codeAnchors[0].targetBranchVerified must be true", errors)

    def test_pipeline_source_mismatch_blocks(self):
        value = matrix()
        value["componentMatrix"][0]["pipelineRepositoryId"] = "REPO-2"
        errors, _ = MODULE.validate(value)
        self.assertIn("componentMatrix[0] pipeline repository mismatch", errors)


if __name__ == "__main__":
    unittest.main()
