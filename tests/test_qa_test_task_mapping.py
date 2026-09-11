from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
SCRIPTS = ROOT / "skills" / "YunxiaoQA" / "scripts"
sys.path.insert(0, str(SCRIPTS))
saved_modules = {
    name: sys.modules.pop(name)
    for name in ("yunxiao_cli_runtime", "yunxiao_cli_testhub")
    if name in sys.modules
}
try:
    spec = importlib.util.spec_from_file_location(
        "qa_test_task_mapping_lifecycle", SCRIPTS / "yunxiao_cli_test_lifecycle.py"
    )
    QA = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(QA)
finally:
    for name in ("yunxiao_cli_runtime", "yunxiao_cli_testhub"):
        sys.modules.pop(name, None)
    sys.modules.update(saved_modules)
    sys.path.remove(str(SCRIPTS))


class QaTestTaskMappingTests(unittest.TestCase):
    def aggregate(self, tests: list[dict]) -> dict:
        return {
            "development": [
                {"id": "DEV-1", "status": "已完成"},
                {"id": "DEV-2", "status": "已完成"},
                {"id": "DEV-CANCELLED", "status": "已取消"},
            ],
            "tests": tests,
        }

    def test_one_completed_test_per_active_development_task_passes(self):
        gaps = QA.development_test_mapping_gaps(self.aggregate([
            {"id": "TEST-1", "status": "已完成", "developmentTaskId": "DEV-1",
             "testMode": "formal-plan"},
            {"id": "TEST-2", "status": "处理中", "developmentTaskId": "DEV-2",
             "testMode": "mandatory-test-task"},
        ]), "TEST-2")
        self.assertEqual(gaps, [])

    def test_missing_duplicate_or_lightweight_mapping_blocks_aggregation(self):
        gaps = QA.development_test_mapping_gaps(self.aggregate([
            {"id": "TEST-1", "status": "已完成", "developmentTaskId": "DEV-1",
             "testMode": "lightweight-verification"},
            {"id": "TEST-1B", "status": "已完成", "developmentTaskId": "DEV-1",
             "testMode": "mandatory-test-task"},
        ]), "TEST-1B")
        self.assertTrue(any("轻量验证" in gap for gap in gaps))
        self.assertTrue(any("多个测试任务" in gap for gap in gaps))
        self.assertTrue(any("DEV-2缺少对应测试任务" in gap for gap in gaps))

    def test_invalid_scope_and_unfinished_sibling_block_aggregation(self):
        gaps = QA.development_test_mapping_gaps(self.aggregate([
            {"id": "TEST-1", "status": "处理中", "developmentTaskId": "DEV-1",
             "testMode": "formal-plan"},
            {"id": "TEST-2", "status": "已完成", "testScopeError": "缺少范围"},
        ]), "TEST-2")
        self.assertTrue(any("TEST-1不是已完成" in gap for gap in gaps))
        self.assertTrue(any("TEST-2范围无效" in gap for gap in gaps))
        self.assertTrue(any("DEV-2缺少对应测试任务" in gap for gap in gaps))


if __name__ == "__main__":
    unittest.main()
