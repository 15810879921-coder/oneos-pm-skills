from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts/build-yunxiao-skill-index.py"
SPEC = importlib.util.spec_from_file_location("build_yunxiao_skill_index", SCRIPT)
INDEX = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(INDEX)


class YunxiaoSkillIndexTests(unittest.TestCase):
    def test_index_matches_live_suite_and_paths(self):
        index = INDEX.load_index()
        INDEX.validate_index(index)
        self.assertEqual(tuple(skill["name"] for skill in index["skills"]), INDEX.SKILL_ORDER)
        self.assertEqual(INDEX.suite_versions(), {index["suiteVersion"]})

    def test_generated_markdown_is_current(self):
        index = INDEX.load_index()
        expected = INDEX.render_markdown(index)
        actual = INDEX.OUTPUT.read_text(encoding="utf-8")
        self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main()
