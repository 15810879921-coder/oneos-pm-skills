import copy
import importlib.util
import sys
import unittest
from pathlib import Path
from unittest import mock
from handoff_fixtures import make_bundle, seal

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/yunxiao-development-delivery/scripts"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("start_handoff", SCRIPTS / "yunxiao_cli_handoff.py")
START = importlib.util.module_from_spec(spec)
spec.loader.exec_module(START)


class StartHandoffTests(unittest.TestCase):
    def setUp(self):
        self.bundle = make_bundle("development")
        self.items = {i: {"id": i, "description": START.hg.upsert_manifest("", self.bundle["manifest"])}
                      for i in ("REQ-1", "DEL-1")}
        self.items["DEV-1"] = {"id": "DEV-1", "description": "开发人工说明",
                               "spaceIdentifier": "PROJECT-1", "parentId": "DEL-1"}
        self.read = mock.patch.object(START.gateway, "execute_read",
            side_effect=lambda _, call: self.items[call["args"][1]]).start()
        mock.patch.object(START.hg, "read_document", side_effect=lambda doc: doc["kind"].encode()).start()
        self.addCleanup(mock.patch.stopall)

    def test_formal_start_reads_live_product_and_real_document_bytes(self):
        result = START.verify_start("aliyun", self.bundle, "DEV-1")
        self.assertTrue(result["verified"])
        self.assertEqual(result["handoffSha256"], self.bundle["manifest"]["sha256"])
        self.assertEqual({c.args[1]["args"][1] for c in self.read.call_args_list}, {"DEV-1", "REQ-1", "DEL-1"})

    def test_old_locally_valid_bundle_cannot_start_after_live_contract_changes(self):
        newer = copy.deepcopy(self.bundle["manifest"])
        newer["version"] = "2"
        self.items["REQ-1"]["description"] = START.hg.upsert_manifest("", seal(newer))
        START.hg.validate_bundle(self.bundle, "development")
        with self.assertRaisesRegex(START.core.AdapterError, "换版"):
            START.verify_start("aliyun", self.bundle, "DEV-1")

    def test_wrong_task_and_changed_actual_material_block(self):
        with self.assertRaisesRegex(START.core.AdapterError, "任务编号"):
            START.verify_start("aliyun", self.bundle, "OTHER")
        with mock.patch.object(START.hg, "read_document", return_value=b"updated"):
            with self.assertRaisesRegex(START.core.AdapterError, "实际内容"):
                START.verify_start("aliyun", self.bundle, "DEV-1")

    def test_existing_unrelated_task_cannot_claim_the_same_contract(self):
        self.items["UNRELATED-DEV"] = {"id": "UNRELATED-DEV", "spaceIdentifier": "PROJECT-1",
                                       "parentId": "OTHER-DEL", "description": "另一需求的开发任务"}
        self.bundle["developmentReceipt"]["taskId"] = "UNRELATED-DEV"
        self.bundle["developmentReceipt"] = seal(self.bundle["developmentReceipt"])
        with self.assertRaisesRegex(START.core.AdapterError, "归属"):
            START.verify_start("aliyun", self.bundle, "UNRELATED-DEV")

    def test_wrapped_cli_response_is_unwrapped_before_identity_check(self):
        self.read.side_effect = lambda _, call: {"data": self.items[call["args"][1]]}
        self.assertTrue(START.verify_start("aliyun", self.bundle, "DEV-1")["verified"])


if __name__ == "__main__":
    unittest.main()
