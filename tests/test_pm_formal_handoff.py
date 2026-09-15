from __future__ import annotations

import argparse
import ast
import copy
import inspect
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from handoff_fixtures import make_bundle, seal
from test_yunxiao_cli_pm_snapshot import MODULE as PM


class FormalProductHandoffTests(unittest.TestCase):
    def setUp(self):
        self.manifest = make_bundle()["manifest"]
        self.items = {
            "REQ-1": {"id": "REQ-1", "subject": "需求", "spaceIdentifier": "PROJECT-1",
                      "status": {"name": "设计完成"}, "assignedTo": {"id": "PM"}},
            "DEL-1": {"id": "DEL-1", "subject": "【交付】Web", "spaceIdentifier": "PROJECT-1",
                      "status": {"name": "待处理"}, "assignedTo": {"id": "DEV-OWNER"}},
        }
        for item in self.items.values():
            item["description"] = PM.hg.upsert_manifest("人工正文", self.manifest)

    def scope(self, manifests=None):
        with mock.patch.object(PM, "get_workitem", side_effect=lambda _, i: copy.deepcopy(self.items[i])), \
             mock.patch.object(PM, "verified_project", return_value=({}, "OneOS")), \
             mock.patch.object(PM, "search_workitems", side_effect=lambda *_: [copy.deepcopy(i) for i in self.items.values() if i["subject"].startswith("【交付】")]), \
             mock.patch.object(PM, "relation_ids", side_effect=lambda _, i, r: [] if i == "REQ-1" else ["REQ-1"]), \
             mock.patch.object(PM, "exact_type", return_value={"id": "TYPE"}), \
             mock.patch.object(PM, "status_ids", return_value={"待开发": "READY"}), \
             mock.patch.object(PM.hg, "read_document", side_effect=lambda d: d["kind"].encode()):
            return PM.build_formal_handoff_scope("aliyun", "PROJECT-1", "REQ-1", manifests or [self.manifest])

    def test_standard_initialization_never_advances_to_development(self):
        tree = ast.parse(inspect.getsource(PM.cmd_apply))
        targets = [n.args[2].value for n in ast.walk(tree) if isinstance(n, ast.Call)
                   and isinstance(n.func, ast.Name) and n.func.id == "advance_requirement"
                   and isinstance(n.args[2], ast.Constant)]
        self.assertNotIn("待开发", targets)
        self.assertIn("设计完成", targets)

    def test_current_manifest_and_owned_delivery_are_required(self):
        self.assertEqual("REQ-1", self.scope()["requirement"]["id"])
        self.items["DEL-1"]["description"] = "只有占位"
        with self.assertRaises(PM.core.AdapterError):
            self.scope()

    def test_unfrozen_other_delivery_blocks_whole_requirement(self):
        self.items["DEL-2"] = {**self.items["DEL-1"], "id": "DEL-2", "subject": "【交付】小程序"}
        with self.assertRaisesRegex(PM.core.AdapterError, "全部.*交付"):
            self.scope()

    def test_multiple_deliveries_must_match_their_own_manifest(self):
        second = copy.deepcopy(self.manifest)
        second["scope"].update(deliveryId="DEL-2", scopeId="SCOPE-2")
        second = seal(second)
        self.items["DEL-2"] = {**self.items["DEL-1"], "id": "DEL-2", "subject": "【交付】小程序",
                               "description": PM.hg.upsert_manifest("小程序人工正文", second)}
        self.items["REQ-1"]["description"] = PM.hg.upsert_manifest(self.items["REQ-1"]["description"], second)
        self.assertEqual(2, len(self.scope([self.manifest, second])["deliveries"]))

    def test_standard_cannot_overwrite_frozen_or_developing_items(self):
        with self.assertRaisesRegex(PM.core.AdapterError, "冻结|初始化"):
            PM.require_unfrozen_initialization({"existing": {"requirement": self.items["REQ-1"], "delivery": self.items["DEL-1"]}})

    def test_changed_product_preflight_blocks_before_any_status_write(self):
        scope = self.scope()
        plan = {"schema": PM.SCHEMA, "command": "preflight-handoff", "liveScope": scope,
                "input": {"spaceId": "PROJECT-1", "requirementId": "REQ-1"},
                "manifests": [self.manifest]}
        plan["preflightHash"] = PM.canonical_hash(plan, {"preflightHash"})
        changed = copy.deepcopy(scope)
        changed["requirement"]["descriptionHash"] = "changed"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "preflight.json"
            path.write_text(json.dumps(plan))
            with mock.patch.object(PM.core, "find_aliyun", return_value="aliyun"), \
                 mock.patch.object(PM.core, "require_auth_env"), \
                 mock.patch.object(PM, "build_formal_handoff_scope", return_value=changed), \
                 mock.patch.object(PM, "update_item") as write:
                with self.assertRaisesRegex(PM.core.AdapterError, "漂移|变化"):
                    PM.cmd_apply_handoff(argparse.Namespace(preflight=str(path), receipt=None))
                write.assert_not_called()

    def test_formal_handoff_writes_only_status_and_accepts_modified_timestamp(self):
        scope = self.scope()
        after = copy.deepcopy(scope)
        after["requirement"].update(status="待开发", gmtModified="after-status-write")
        plan = {"schema": PM.SCHEMA, "command": "preflight-handoff", "liveScope": scope,
                "input": {"spaceId": "PROJECT-1", "requirementId": "REQ-1"}, "manifests": [self.manifest]}
        plan["preflightHash"] = PM.canonical_hash(plan, {"preflightHash"})
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "plan.json"
            path.write_text(json.dumps(plan))
            with mock.patch.object(PM.core, "find_aliyun", return_value="aliyun"), \
                 mock.patch.object(PM.core, "require_auth_env"), \
                 mock.patch.object(PM.core, "write_json") as receipt, \
                 mock.patch.object(PM, "build_formal_handoff_scope", side_effect=[scope, after]), \
                 mock.patch.object(PM, "update_item") as write:
                PM.cmd_apply_handoff(argparse.Namespace(preflight=str(path), receipt=str(Path(directory) / "receipt.json")))
                write.assert_called_once_with("aliyun", "REQ-1", {"status": "READY"})
                self.assertIs(receipt.call_args.args[1]["formal"], True)


if __name__ == "__main__":
    unittest.main()
