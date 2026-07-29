# 交接契约（开发 Skill 入口）

YunxiaoPM 与开发 Skill **不要**互相 include 全文；仅认下列契约。口径见 [settled-rules.md](settled-rules.md)。

```text
PM 完成交棒 → 需求=待开发；【交付】=ONEOS-xx；负责人=何斐；ASSOCIATED→需求
若交付仍占位 → 回报已标红风险
开发 Skill 入口 → 认「需求编号 + 交付任务编号」
占位时只可信需求「原始诉求（AutoRDO）」，可要求产品补设计完成

生成【开发】描述：
  · 仅当类型=【优化】→ 按需求 MD 精炼，只写「修改前规则」关键点，禁止贴全文
  · 类型=【新增】→ 不适用改前模板
  · 细则：dev-task-description.md
```

共享常量可引用本 Skill `assets/` 短路径，勿加载整份对方规则。

测试侧：**YunxiaoQA**（`~/.cursor/skills/YunxiaoQA/`）；本契约不覆盖提测/缺陷。
