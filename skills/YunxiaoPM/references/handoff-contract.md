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

## 跨 Skill 交接载荷

交接只允许携带以下逻辑信息：

- 正式 Skill 名与选择器；
- 需求、【交付】及可选【分析】/【设计】任务编号；
- 当前状态与已回读的 `ASSOCIATED`、`TASK_SUB` 正式关系；
- 负责人用户 ID、PRD/附件版本、证据 ID/URL/哈希和幂等键。

禁止把安装目录、其他 Skill 的 `assets/`/`references/`/`scripts/` 路径或客户端目录作为契约字段。开发 Skill 必须使用自己的资源；常量缺失时按上述编号实时查询云效。

开发侧正式目标：**yunxiao-development-delivery**。测试侧正式目标：**YunxiaoQA**；本契约不覆盖提测/缺陷。
