# 交接契约（开发 Skill 入口）

YunxiaoPM 与开发 Skill **不要**互相 include 全文；仅认下列契约。口径见 [settled-rules.md](settled-rules.md)。

```text
PM 完成交棒 → 需求=待开发；【交付】=ONEOS-xx；负责人=命令或项目配置的唯一解析结果；ASSOCIATED→需求
正式交棒 → 需求与全部当前端侧【交付】含同版产品快照与 manifest，apply-handoff 回读 formal:true
若交付仍占位 → 仅调查/补录，formal:false，不推进待开发
开发 Skill 入口 → 按精确编号和 scopeId 回读同版合同、验收、工程清单，提交理解回执后通过自身实时校验
原始诉求、历史PRD和原型建议不能替代冻结合同

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
- 负责人用户 ID、负责人来源（命令/项目配置）、PRD/附件版本、证据 ID/URL/哈希和幂等键。
- 产品交棒快照编号、manifest/scopeId/SHA-256、资料来源和页面/交互索引；占位仅报缺失，不称正式交棒。

禁止把安装目录、其他 Skill 的 `assets/`/`references/`/`scripts/` 路径或客户端目录作为契约字段。开发 Skill 必须使用自己的资源；常量缺失时按上述编号实时查询云效。

开发侧正式目标：**yunxiao-development-delivery**。测试侧正式目标：**YunxiaoQA**；本契约不覆盖提测/缺陷。
