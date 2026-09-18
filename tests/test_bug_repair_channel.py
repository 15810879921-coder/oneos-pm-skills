from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "skills" / "YunxiaoQA" / "scripts"))
sys.path.insert(0, str(ROOT / "skills" / "yunxiao-development-delivery" / "scripts"))


def load(name: str, relative: str):
    path = ROOT / relative
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


QA = load("qa_bug_repair_request", "skills/YunxiaoQA/scripts/yunxiao_cli_bug_repair_request.py")
DEV = load("dev_bug_repair_channel", "skills/yunxiao-development-delivery/scripts/yunxiao_cli_bug_repair_channel.py")
EVIDENCE = load("bug_fix_evidence", "skills/yunxiao-development-delivery/scripts/yunxiao_bug_fix_evidence.py")
ROUTE = load("route_lifecycle_intent", "skills/yunxiao-development-delivery/scripts/route_lifecycle_intent.py")


class BugRepairChannelTests(unittest.TestCase):
    def test_qa_evidence_requires_actual_expected_steps_and_reference(self):
        value = QA.validate_evidence({
            "steps": ["打开页面"], "actual": "空白", "expected": "有数据",
            "evidence": [{"type": "screenshot", "ref": "CASE-1"}],
        }, "ONEOS-1", "ONEOS-2")
        self.assertEqual(value["schemaVersion"], "oneos.test-bug-evidence/v1")
        self.assertEqual(value["testTask"], "ONEOS-2")

    def test_qa_evidence_rejects_secret(self):
        with self.assertRaisesRegex(QA.core.AdapterError, "凭据"):
            QA.validate_evidence({
                "steps": ["打开"], "actual": "x", "expected": "y",
                "evidence": [{"type": "log", "ref": "password=bad"}],
            }, "ONEOS-1", "ONEOS-2")

    def test_development_acceptance_requires_structured_request(self):
        request = {
            "schemaVersion": "oneos.test-bug-repair-request/v1",
            "status": "requested", "bugSerialNumber": "ONEOS-1", "bugId": "B1",
            "testTaskId": "T1", "evidenceHash": "hash", "idempotencyKey": "key",
        }
        self.assertEqual(request["schemaVersion"], DEV.REQUEST_SCHEMA)
        self.assertEqual(DEV.parse_requests([
            {"content": "【测试缺陷修复请求】\n<!-- " + json.dumps(request) + " -->"}
        ], "ONEOS-1")[0]["bugId"], "B1")

    def test_defer_record_requires_approval_and_preserves_history(self):
        snapshot = {"snapshotHash": "snap"}
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "defer.json"
            path.write_text(json.dumps({
                "schemaVersion": "oneos.bug-deferred-fix/v1", "snapshotHash": "snap",
                "results": [{"bugSerialNumber": "ONEOS-1", "reason": "第三方依赖待升级",
                              "approvedBy": "PM-1", "approvalEvidence": "APPROVAL-1",
                              "nextAction": "下个版本处理"}],
            }), encoding="utf-8")
            records = EVIDENCE.validate_defer(str(path), snapshot, {"ONEOS-1"})
        description = EVIDENCE.append_defer_record("原描述", records["ONEOS-1"], "MARKDOWN")
        self.assertEqual(EVIDENCE.existing_defer_record(description), records["ONEOS-1"])
        self.assertIn("【研发暂不修复】", description)

    def test_natural_language_routes_to_special_repair_channel(self):
        result = ROUTE.route("处理测试修复请求：缺陷=ONEOS-123", {})
        self.assertEqual(result["action"], "accept_test_bug_repair")
        self.assertEqual(result["workItemSerial"], "ONEOS-123")


if __name__ == "__main__":
    unittest.main()
