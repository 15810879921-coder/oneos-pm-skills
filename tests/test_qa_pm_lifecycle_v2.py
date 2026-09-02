from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]


def load_module(name: str, relative: str):
    path = ROOT / relative
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


CREATE_BUG = load_module("qa_create_bug", "skills/YunxiaoQA/scripts/create_bug.py")
RETEST = load_module("qa_bug_retest", "skills/YunxiaoQA/scripts/yunxiao_cli_bug_retest.py")
ACCEPT = load_module("pm_accept_release", "skills/YunxiaoPM/scripts/accept_release.py")


class QaPmLifecycleV2Tests(unittest.TestCase):
    def test_bug_development_hint_is_optional_and_escaped(self):
        unchanged = CREATE_BUG.append_development_trace("<p>正文</p>", None, None)
        self.assertEqual(unchanged, "<p>正文</p>")
        traced = CREATE_BUG.append_development_trace(
            "<p>正文</p>",
            {"serialNumber": "ONEOS-1", "subject": "【开发】<script>"},
            "DU-1<bad>",
        )
        self.assertIn("ONEOS-1", traced)
        self.assertIn("&lt;script&gt;", traced)
        self.assertIn("DU-1&lt;bad&gt;", traced)

    def test_retest_ids_are_deterministic_and_change_with_version(self):
        first = RETEST.build_retest_ids("TEST-1", "PLAN-1", "CASE-1", "RUN-1", "V1", "BUG-1")
        same = RETEST.build_retest_ids("TEST-1", "PLAN-1", "CASE-1", "RUN-1", "V1", "BUG-1")
        changed = RETEST.build_retest_ids("TEST-1", "PLAN-1", "CASE-1", "RUN-1", "V2", "BUG-1")
        self.assertEqual(first, same)
        self.assertNotEqual(first, changed)

    def test_partial_acceptance_scope_requires_exact_component_target_version(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "scope.json"
            path.write_text(
                json.dumps(
                    {
                        "components": [
                            {
                                "deliveryUnitId": "DU-1",
                                "componentId": "WEB",
                                "deploymentTargetId": "PROD-WEB",
                                "productionVersion": "V1",
                                "branchInstanceIds": ["B2", "B1", "B1"],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            rows = ACCEPT.read_component_scope(path)
            self.assertEqual(rows[0]["branchInstanceIds"], ["B1", "B2"])
            args = type("Args", (), {"action": "pass", "release_sn": "REL-1",
                                      "acceptor": "验收人", "evidence": "E1", "reason": ""})()
            block = ACCEPT.acceptance_block(args, "accept-key", ["REQ-1"], "PROD-1", [], rows)
            self.assertIn("YUNXIAOPM_COMPONENT_ACCEPTANCE:accept-key:START", block)
            self.assertNotIn(ACCEPT.ACCEPT_START, block)
            path.write_text(json.dumps([{"componentId": "WEB"}]), encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "缺少字段"):
                ACCEPT.read_component_scope(path)


if __name__ == "__main__":
    unittest.main()
