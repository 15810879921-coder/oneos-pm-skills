from pathlib import Path
import unittest


ROOT = Path(__file__).parents[1]
SKILL = ROOT / "skills" / "yunxiao-development-delivery"


class DevelopmentCodexTimeAccountingPolicyTests(unittest.TestCase):
    def test_completion_uses_incremental_index_and_bounded_lookup(self):
        policy = (SKILL / "references" / "codex-time-accounting.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("oneos.codex-task-segment/v1", policy)
        self.assertIn("精确索引查询", policy)
        self.assertIn("代码资产反查", policy)
        self.assertIn("时间窗元数据查询", policy)
        self.assertIn("定向深读", policy)
        self.assertIn("正常完成开发流程禁止退化为全量会话深读", policy)
        self.assertIn("只读能力探测", policy)
        self.assertIn("duration_ms", policy)
        self.assertIn("原始会话正文不进入索引", policy)
        self.assertIn("skill-run codex_task_time.py upsert-segment", policy)
        self.assertIn("skill-run codex_task_time.py discover", policy)

    def test_assignment_is_automatic_and_never_requires_developer_confirmation(self):
        policy = (SKILL / "references" / "codex-time-accounting.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("归属结果只有`已归属`、`排除`和`未归属`三种", policy)
        self.assertIn("不得向开发人员发起会话选择或归属确认", policy)
        self.assertNotIn("等待开发人员确认", policy)
        self.assertNotIn("请开发人员选择", policy)

    def test_effort_gaps_do_not_block_development_closure(self):
        policy = (SKILL / "references" / "codex-time-accounting.md").read_text(
            encoding="utf-8"
        )
        controls = (SKILL / "references" / "controls.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("不得阻断已经通过代码交付和验证门禁的开发任务完成", policy)
        self.assertIn("不阻断开发任务完成", controls)
        self.assertNotIn("任一统计或工作日志门禁失败时，不把开发任务改为", policy)


if __name__ == "__main__":
    unittest.main()
