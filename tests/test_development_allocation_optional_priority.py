from __future__ import annotations

import importlib.util
import argparse
import json
import sys
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = (
    Path(__file__).parents[1]
    / "skills"
    / "yunxiao-development-delivery"
    / "scripts"
    / "yunxiao_cli_allocate_task.py"
)
SCRIPT_DIR = str(SCRIPT.parent)
sys.path.insert(0, SCRIPT_DIR)
SPEC = importlib.util.spec_from_file_location("yunxiao_cli_allocate_task", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class DevelopmentAllocationTests(unittest.TestCase):
    def test_apply_reads_delivery_metadata_once_before_create(self):
        frozen = {
            "input": {}, "scopeFingerprint": "same",
            "requirementSnapshot": {"sha256": "snapshot"},
            "technicalPlan": {"sha256": "plan"}, "action": "create",
            "liveScope": {"delivery": {"id": "DELIVERY-ID"}, "owner": {"id": "OWNER-ID"}},
        }
        class StopBeforeWrite(Exception):
            pass
        with mock.patch.object(MODULE.core, "find_aliyun", return_value="aliyun"), \
                mock.patch.object(MODULE.core, "require_auth_env"), \
                mock.patch.object(MODULE, "load_preflight", return_value=frozen), \
                mock.patch.object(MODULE, "build_preflight", return_value=frozen) as preflight, \
                mock.patch.object(MODULE, "get_workitem", return_value={
                    "workitemType": {"id": "TYPE-ID"}, "sprint": {"id": "SPRINT-ID"},
                }) as get_item, \
                mock.patch.object(MODULE, "create_development", side_effect=StopBeforeWrite) as create:
            with self.assertRaises(StopBeforeWrite):
                MODULE.cmd_apply(argparse.Namespace(preflight="preflight.json"))
        preflight.assert_called_once()
        get_item.assert_called_once_with("aliyun", "DELIVERY-ID")
        self.assertEqual(create.call_args.args[1]["workitemTypeId"], "TYPE-ID")
        self.assertEqual(create.call_args.args[1]["sprintId"], "SPRINT-ID")

    def test_create_development_omits_missing_source_priority(self):
        captured = {}

        def fake_run(_executable, args):
            captured["args"] = args
            return {"id": "DEV-ID"}

        scope = {
            "delivery": {
                "id": "DELIVERY-ID",
                "subject": "【交付】示例",
                "priorityId": None,
            },
            "projectId": "PROJECT-ID",
            "workitemTypeId": "TYPE-ID",
            "fieldIds": {"planStart": "start", "planFinish": "finish"},
            "input": {"planStart": "2026-08-27", "planFinish": "2026-08-28"},
        }
        with mock.patch.object(MODULE.core, "run_devops", side_effect=fake_run), \
                mock.patch.object(MODULE, "get_workitem", return_value={"id": "DEV-ID"}), \
                mock.patch.object(MODULE, "field_value", return_value=None):
            created = MODULE.create_development("aliyun", scope, "OWNER-ID")

        self.assertEqual(created["id"], "DEV-ID")
        index = captured["args"].index("--custom-field-values") + 1
        values = json.loads(captured["args"][index])
        self.assertNotIn("priority", values)
        self.assertEqual(values["start"], "2026-08-27 00:00:00")
        self.assertEqual(values["finish"], "2026-08-28 23:59:59")

    def test_allocation_does_not_hardcode_delivery_owner_name(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn("来源【交付】负责人不是何斐", source)
        self.assertIn("来源【交付】负责人无法官方回读", source)


if __name__ == "__main__":
    unittest.main()
