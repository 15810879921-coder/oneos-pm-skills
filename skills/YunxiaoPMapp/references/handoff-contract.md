# 交接契约（开发 Skill 入口）

YunxiaoPMapp 与开发 Skill **不要**互相 include 全文；仅认下列契约。

```text
PM 完成交棒 → 需求=待开发；【交付】任务编号=ONEOS-xx；负责人=何斐；ASSOCIATED 需求
若交付描述仍为占位 → 回报已标红风险
开发 Skill 入口 → 认「需求编号 + 交付任务编号」
占位时只可信需求「原始诉求（AutoRDO）」并有权要求产品补设计完成
```

共享常量（项目 ID、何斐 ID、节假日日历）可引用本 Skill 的 `assets/` 短路径，勿加载整份对方规则。

测试 Skill 另开；本契约不覆盖提测/缺陷。
