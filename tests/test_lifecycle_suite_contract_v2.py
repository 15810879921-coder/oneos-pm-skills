from __future__ import annotations

import unittest
import importlib.util
from pathlib import Path


ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "skills/yunxiao-development-delivery/scripts/verify_lifecycle_suite.py"
SPEC = importlib.util.spec_from_file_location("verify_lifecycle_suite", SCRIPT)
VERIFY = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(VERIFY)


class LifecycleSuiteContractV2Tests(unittest.TestCase):
    def test_all_lifecycle_skills_share_suite_version(self):
        paths = [
            "skills/YunxiaoPM/SKILL.md",
            "skills/yunxiao-development-delivery/SKILL.md",
            "skills/development-brain/SKILL.md",
            "skills/YunxiaoQA/SKILL.md",
            "skills/yunxiao-release-operations/SKILL.md",
        ]
        for relative in paths:
            with self.subTest(relative=relative):
                text = (ROOT / relative).read_text(encoding="utf-8")
                self.assertIn("10.1.0", text)

    def test_new_writer_is_compatible_with_legacy_reader_boundary(self):
        development = (ROOT / "skills/yunxiao-development-delivery/references/branch-submit-release-ledger.md").read_text(encoding="utf-8")
        release = (ROOT / "skills/yunxiao-release-operations/references/release-code-ledger.md").read_text(encoding="utf-8")
        self.assertIn("旧 `【代码交付记录】`", release)
        self.assertIn("oneos.delivery-ledger/v1", development)
        self.assertIn("oneos.delivery-ledger/v1", release)

    def test_feature_gate_uses_explicit_install_paths(self):
        names = [
            "YunxiaoPM", "yunxiao-development-delivery", "development-brain",
            "YunxiaoQA", "yunxiao-release-operations",
        ]
        values = [f"{name}={ROOT / 'skills' / name / 'SKILL.md'}" for name in names]
        state = VERIFY.verify(values)
        self.assertTrue(state["verified"])
        self.assertEqual(set(state["skills"]), set(names))


if __name__ == "__main__":
    unittest.main()
