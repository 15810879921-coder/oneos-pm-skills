from __future__ import annotations

import os
from pathlib import Path
import sys
import unittest

SCRIPTS = Path(os.environ.get("ONEOS_RELEASE_TEST_SCRIPTS",
               str(Path(__file__).parents[1] / "skills/yunxiao-release-operations/scripts")))
sys.path.insert(0, str(SCRIPTS))
import release_read_batch as B


class ReleasePerformanceRuntimeTests(unittest.TestCase):
    def test_batch_read_preserves_order_and_hashes_values(self):
        value = {"schemaVersion": B.SCHEMA, "requests": [
            {"id": "release", "operation": "projex-get-workitem", "args": ["--id", "ONEOS-1"]},
            {"id": "pipeline", "operation": "flow-get-pipeline", "args": ["--pipeline-id", "7"]},
        ]}
        result = B.run_batch(value, reader=lambda call: {"operation": call["operation"]}, workers=2)
        self.assertEqual([row["id"] for row in result["results"]], ["release", "pipeline"])
        self.assertEqual(result["requestCount"], 2)
        self.assertEqual(result["results"][0]["valueHash"],
                         B.gateway.stable_hash({"operation": "projex-get-workitem"}))

    def test_batch_read_rejects_writes_and_duplicate_ids(self):
        with self.assertRaisesRegex(B.gateway.core.AdapterError, "只读"):
            B.run_batch({"schemaVersion": B.SCHEMA, "requests": [
                {"id": "x", "operation": "flow-create-pipeline-run", "args": []},
            ]}, reader=lambda call: {})
        with self.assertRaisesRegex(ValueError, "唯一"):
            B.run_batch({"schemaVersion": B.SCHEMA, "requests": [
                {"id": "x", "operation": "projex-get-workitem", "args": ["--id", "1"]},
                {"id": "x", "operation": "projex-get-workitem", "args": ["--id", "2"]},
            ]}, reader=lambda call: {})

if __name__ == "__main__":
    unittest.main()
