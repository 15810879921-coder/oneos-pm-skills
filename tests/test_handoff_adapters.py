from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from handoff_fixtures import make_bundle
from test_complete_development_executor import EXECUTOR, valid_plan
from test_yunxiao_cli_pm_snapshot import MODULE as PM

# Each standalone skill owns a runtime with this basename; isolate imports in
# this cross-skill test instead of relying on discovery order in sys.modules.
_spec = importlib.util.spec_from_file_location("pm_handoff_runtime", Path(PM.__file__).with_name("yunxiao_cli_runtime.py"))
_runtime = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_runtime)
PM.core = _runtime

_qa_scripts = Path(__file__).parents[1] / "skills" / "YunxiaoQA" / "scripts"
_qa_spec = importlib.util.spec_from_file_location(
    "qa_handoff_lifecycle", _qa_scripts / "yunxiao_cli_test_lifecycle.py",
)
QA = importlib.util.module_from_spec(_qa_spec)
_qa_module_names = ("yunxiao_cli_runtime", "yunxiao_cli_testhub", "handoff_gate")
_qa_saved_modules = {name: sys.modules.get(name) for name in _qa_module_names}
for _qa_module_name in _qa_module_names:
    sys.modules.pop(_qa_module_name, None)
sys.path.insert(0, str(_qa_scripts))
assert _qa_spec and _qa_spec.loader
_qa_spec.loader.exec_module(QA)
sys.path.pop(0)
for _qa_module_name, _qa_saved in _qa_saved_modules.items():
    if _qa_saved is None:
        sys.modules.pop(_qa_module_name, None)
    else:
        sys.modules[_qa_module_name] = _qa_saved


class HandoffAdapterTests(unittest.TestCase):
    def test_development_stage_cannot_defer_receipt_check_until_after_closure(self):
        plan = valid_plan()
        plan["stages"]["developmentComplete"]["verifications"][0]["expect"].pop("description")
        with self.assertRaisesRegex(EXECUTOR.core.AdapterError, "阶段内完整回读"):
            EXECUTOR.validate_plan(plan)
    def test_live_development_gate_rechecks_materials_and_preserves_human_text(self):
        plan = valid_plan()
        b = plan["evidence"]["handoffEvidence"]
        docs = {i: {"id": i, "spaceIdentifier": "PROJECT-1",
                    "description": EXECUTOR.hg.upsert_manifest("", b["manifest"])}
                for i in ("REQ-1", "DEL-1")}
        docs["DEV-1"] = {"id": "DEV-1", "description": "开发人员的人工说明",
                         "spaceIdentifier": "PROJECT-1", "parentId": "DEL-1"}
        with mock.patch.object(EXECUTOR.core, "find_aliyun", return_value="aliyun"), \
             mock.patch.object(EXECUTOR.core, "require_auth_env"), \
             mock.patch.object(EXECUTOR.gateway, "execute_read", side_effect=lambda _, c:
                 [{"resourceId": "REQ-1"}] if c["operation"].endswith("relation-records") else docs[c["args"][1]]), \
             mock.patch.object(EXECUTOR.hg, "read_document", side_effect=lambda d: d["kind"].encode()):
            EXECUTOR._verify_handoff(plan)
            docs["DEV-1"]["description"] += "\n新的人工修改"
            with self.assertRaisesRegex(EXECUTOR.core.AdapterError, "人工正文"):
                EXECUTOR._verify_handoff(plan)

    def test_live_handoff_cannot_skip_missing_manifest_changed_material_or_scope(self):
        for defect in ("missing_manifest", "changed_material", "wrong_project", "wrong_parent", "wrong_requirement"):
            plan = valid_plan()
            bundle = plan["evidence"]["handoffEvidence"]
            docs = {item: {"id": item, "spaceIdentifier": "PROJECT-1",
                    "description": EXECUTOR.hg.upsert_manifest("", bundle["manifest"])}
                    for item in ("REQ-1", "DEL-1")}
            docs["DEV-1"] = {"id": "DEV-1", "spaceIdentifier": "PROJECT-1",
                "parentId": "DEL-1", "description": "开发人员的人工说明"}
            if defect == "missing_manifest":
                docs["REQ-1"]["description"] = "旧版产品文字"
            if defect == "wrong_project":
                docs["REQ-1"]["spaceIdentifier"] = "OTHER"
            if defect == "wrong_parent":
                docs["DEV-1"]["parentId"] = "OTHER"
            with self.subTest(defect=defect), \
                 mock.patch.object(EXECUTOR.core, "find_aliyun", return_value="aliyun"), \
                 mock.patch.object(EXECUTOR.core, "require_auth_env"), \
                 mock.patch.object(EXECUTOR.gateway, "execute_read", side_effect=lambda _, c:
                    [{"resourceId": "OTHER" if defect == "wrong_requirement" else "REQ-1"}]
                    if c["operation"].endswith("relation-records") else docs[c["args"][1]]), \
                 mock.patch.object(EXECUTOR.hg, "read_document", side_effect=lambda d:
                    b"changed" if defect == "changed_material" else d["kind"].encode()), \
                 self.assertRaises(EXECUTOR.core.AdapterError):
                EXECUTOR._verify_handoff(plan)

    def test_missing_bundle_blocks_preflight_and_old_ready_receipt_without_writes(self):
        plan = valid_plan()
        plan["evidence"].pop("handoffEvidence")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "plan.json"
            path.write_text(json.dumps(plan), encoding="utf-8")
            ready = Path(directory) / "old-ready.json"
            ready.write_text(json.dumps({"schemaVersion": EXECUTOR.PREFLIGHT_SCHEMA,
                "result": "ready", "plan": plan,
                "fingerprint": EXECUTOR.gateway.stable_hash(plan)}), encoding="utf-8")
            with mock.patch.object(EXECUTOR.gateway, "cmd_preflight") as preflight, \
                 mock.patch.object(EXECUTOR.gateway, "cmd_apply") as write:
                with self.assertRaisesRegex(EXECUTOR.core.AdapterError, "交棒"):
                    EXECUTOR.command_preflight(argparse.Namespace(plan=str(path), output=None))
                with self.assertRaisesRegex(EXECUTOR.core.AdapterError, "交棒"):
                    EXECUTOR.command_apply(argparse.Namespace(preflight=str(ready), output=None))
                preflight.assert_not_called()
                write.assert_not_called()

    def test_changed_live_handoff_blocks_apply_before_any_stage_write(self):
        plan = EXECUTOR.validate_plan(valid_plan())
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "preflight.json"
            path.write_text(json.dumps({"schemaVersion": EXECUTOR.PREFLIGHT_SCHEMA,
                "result": "ready", "plan": plan,
                "fingerprint": EXECUTOR.gateway.stable_hash(plan)}))
            with mock.patch.object(EXECUTOR, "_verify_handoff", side_effect=EXECUTOR.core.AdapterError("交棒已变化")), \
                 mock.patch.object(EXECUTOR.gateway, "cmd_apply") as write:
                with self.assertRaisesRegex(EXECUTOR.core.AdapterError, "交棒已变化"):
                    EXECUTOR.command_apply(argparse.Namespace(preflight=str(path), output=None))
                write.assert_not_called()

    def test_pm_verifies_actual_required_bytes_before_publication(self):
        manifest = make_bundle()["manifest"]
        scope = {"project": {"id": "PROJECT-1"}, "requirement": {"id": "REQ-1"},
                 "delivery": {"id": "DEL-1"}}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "handoff.json"
            path.write_text(json.dumps(manifest))
            with mock.patch.object(PM.hg, "read_document", side_effect=lambda d: d["kind"].encode()):
                self.assertEqual(PM.load_handoff_manifest(str(path), scope), manifest)
            with mock.patch.object(PM.hg, "read_document", return_value=b"changed"):
                with self.assertRaisesRegex(PM.core.AdapterError, "实际内容"):
                    PM.load_handoff_manifest(str(path), scope)

    def test_development_completion_refuses_no_understanding_receipt(self):
        plan = valid_plan()
        plan["evidence"].pop("handoffEvidence", None)
        with self.assertRaisesRegex(EXECUTOR.core.AdapterError, "交棒"):
            EXECUTOR.validate_plan(plan)

    def test_development_completion_refuses_wrong_task_receipt(self):
        plan = valid_plan()
        b = make_bundle("development")
        b["developmentReceipt"]["taskId"] = "DEV-OTHER"
        from handoff_fixtures import seal
        b["developmentReceipt"] = seal(b["developmentReceipt"])
        plan["evidence"]["handoffEvidence"] = b
        with self.assertRaisesRegex(EXECUTOR.core.AdapterError, "交棒"):
            EXECUTOR.validate_plan(plan)

    def test_pm_snapshot_preflight_refuses_missing_handoff_manifest(self):
        with mock.patch.object(PM.core, "find_aliyun", return_value="aliyun"), \
             mock.patch.object(PM.core, "require_auth_env"), \
             mock.patch.object(PM.core, "write_json"), \
             mock.patch.object(PM, "load_product_snapshot", return_value={
                 "path": "snapshot.md", "schema": PM.PRODUCT_SNAPSHOT_SCHEMA,
                 "snapshotId": "ps-0000000000000000", "sha256": "0" * 64}), \
             mock.patch.object(PM, "build_product_snapshot_scope", return_value={
                 "project": {"id": "PROJECT-1", "name": "测试"},
                 "requirement": {"id": "REQ-1"}, "delivery": {"id": "DEL-1"}}):
            with self.assertRaisesRegex(PM.core.AdapterError, "交棒"):
                PM.cmd_preflight_product_snapshot(argparse.Namespace(
                    snapshot_file="snapshot.md", handoff_file=None,
                    space_id="PROJECT-1", requirement_id="REQ-1", delivery_id="DEL-1", output="unused.json"))

    def test_qa_gate_binds_managed_scope_tasks_version_and_execution(self):
        bundle = make_bundle("release")
        development = make_bundle("development")
        development_item = {
            "id": "DEV-1",
            "description": QA.hg.upsert_bundle("开发人工正文", development),
        }
        with mock.patch.object(QA, "get_workitem", return_value=development_item), \
             mock.patch.object(QA.hg, "verify_live_bundle"), \
             mock.patch.object(QA.hg, "verify_documents", return_value={"acceptance": "hash"}):
            result = QA.validate_handoff_bundle(
                "aliyun", bundle, "qa-complete", "PROJECT-1", "REQ-1", "DEL-1",
                "SCOPE-DEV-1", "DEV-1", "TEST-1",
                delivery_version="commit:abc123", qa_execution_id="RUN-1",
            )
        self.assertEqual(result["scope"]["scopeId"], "SCOPE-DEV-1")

    def test_qa_gate_rejects_wrong_test_task_and_execution(self):
        bundle = make_bundle("release")
        with self.assertRaisesRegex(QA.core.AdapterError, "QA理解回执"):
            QA.validate_handoff_bundle(
                "aliyun", bundle, "qa-complete", "PROJECT-1", "REQ-1", "DEL-1",
                "SCOPE-DEV-1", "DEV-1", "TEST-OTHER",
                delivery_version="commit:abc123", qa_execution_id="RUN-1",
            )
        development = make_bundle("development")
        with mock.patch.object(QA, "get_workitem", return_value={
                "id": "DEV-1", "description": QA.hg.upsert_bundle("", development),
             }), mock.patch.object(QA.hg, "verify_live_bundle"), \
             mock.patch.object(QA.hg, "verify_documents", return_value={}):
            with self.assertRaisesRegex(QA.core.AdapterError, "executionId"):
                QA.validate_handoff_bundle(
                    "aliyun", bundle, "qa-complete", "PROJECT-1", "REQ-1", "DEL-1",
                    "SCOPE-DEV-1", "DEV-1", "TEST-1",
                    delivery_version="commit:abc123", qa_execution_id="RUN-OTHER",
                )


if __name__ == "__main__":
    unittest.main()
