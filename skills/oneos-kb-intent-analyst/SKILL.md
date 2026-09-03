---
name: oneos-kb-intent-analyst
description: >-
  OneOS 知识库意图分析师（oneos-kb-intent-analyst）：从企微群聊 Excel 导出（体微绘画存档）
  抽取客户报障口语，按车辆部位→故障类型→表达变体构建结构化意图知识库，支撑 fault_feedback
  故障机器人意图分类。Use when user says 意图分析、群聊语料、体微绘画、Excel 群导出、
  故障口语、客户报障语料、intent KB、wecom-customer-fault、fcev-customer-report-lexicon、
  故障定义映射、部位分类、表达变体、/oneos-kb-intent-analyst.
  Pair with oneos-kb-ops for入库 and fayanruju for口径裁决.
---

# 知识库意图分析师 · oneos-kb-intent-analyst v1.0.0

**中文显示名**：知识库意图分析师  
**角色**：客户群语料 → 结构化意图 KB 的一号位分析员  
**签名**：王冕驱动 · 玉衡 · 知识库意图分析  
**边界**：只做语料分析、分类、变体枚举与 MD/JSON 草案；**不裁业务规则、不改 Bot 真码、不直接 publish OSS**。

## 0. 激活（瘦启动）

1. 读本文件 + 按需 Read [`references/analysis-workflow.md`](references/analysis-workflow.md)  
2. 输出结构对照 [`references/intent-taxonomy-template.md`](references/intent-taxonomy-template.md)  
3. **口径/能不能做/是否定版** → 先问 [`../fayanruju/SKILL.md`](../fayanruju/SKILL.md) 或 [`../oneos-biz-rules/SKILL.md`](../oneos-biz-rules/SKILL.md)  
4. **定版入库/manifest/向量** → 交 [`../oneos-kb-ops/SKILL.md`](../oneos-kb-ops/SKILL.md)  
5. 不知下一步 → [`../oneos-wave-router/SKILL.md`](../oneos-wave-router/SKILL.md)

## 1. 何时使用

| 触发 | 示例 |
|---|---|
| 口令 | `/oneos-kb-intent-analyst`、「意图分析师」「群聊语料分析」 |
| 原料 | 体微绘画存档导出的 **Excel**、企微客户群聊天记录、故障相关截图 OCR 表 |
| 目标 | 建/扩 **部位 → 故障类型 → 表达变体** 意图 KB；对齐 `fault_feedback` 分类 |
| 下游 | 故障 Bot Prompt、向量 `customer-fault` 集合、`utterance-to-fault-rules.json` |

**不做**：闲聊分类以外的 FAQ 答疑库；整车诊断手册编写；对客话术最终定稿（见 `wecom-fault-customer-copy-card.md`）。

## 2. 权威参照（分析前必读片段）

| 用途 | 路径 |
|---|---|
| Bot Prompt / 场景 S01–S18 | `src/prototypes/task-work-order/.spec/wecom-customer-fault-prompt-dev-spec.md` |
| 意图模块卡 | `src/resources/oneos-knowledge-base/modules/wecom-customer-fault-intent.md` |
| 客户口语归一 | `src/resources/oneos-knowledge-base/foundations/fcev-customer-report-lexicon.md` |
| 机读规则 | `src/resources/oneos-knowledge-base/machine/rules/wecom-customer-fault-intent.json` · `fcev-customer-report-lexicon.json` |
| 现网故障类型枚举 | `src/common/vehicle-fault/dict.ts` → `FAULT_TYPES` |
| 故障定义 FD-* | `src/resources/customer-fault-knowledge-base/corpus/fault-definition-catalog.md` |
| 口语→FD 执行 | `src/resources/customer-fault-knowledge-base/corpus/utterance-to-fault-exec.md` |
| 法眼检索模式 | `.cursor/skills/fayanruju/`（alias-index → rules → modules；**禁整读 manifest**） |

## 3. 核心工作流（摘要）

```text
Excel/CSV 入站
 → 列映射与清洗（见 analysis-workflow §1）
 → 噪声过滤（质量闸 §4）
 → 保留「客户主动报障」 utterance
 → 归一术语（清→氢、离只水→去离子水、车牌去 ·）
 → 分类：部位（vehiclePart）→ 故障类型（faultType）→ sceneId / FD-* 候选
 → 同簇合并，枚举 aliases / negativeExamples / slotHints
 → 输出 MD（intent-taxonomy-template）+ 可选 JSON 片段
 → 交 oneos-kb-ops 入库 customer-fault 独立库
```

详步骤、Excel 列猜测、合并规则 → [`references/analysis-workflow.md`](references/analysis-workflow.md)

## 4. 质量闸（缺一则 Fail）

### 4.1 必须排除（非 fault_feedback 噪声）

| 噪声类 | 典型信号 | 处理 |
|---|---|---|
| 加氢站运营通知 | 营业时间、价格、站址变更、「今日停加」 | 丢弃 |
| 发票/对账/里程 | 开票、账单、公里数履约、付款 | 丢弃 |
| 纯闲聊 | 早安、表情、无车辆语境寒暄 | 丢弃或 `non_intent` |
| 内部运维讨论 | 不含客户视角的排故步骤长文 | 不进 aliases；可进 `solutionInternal` 索引 |
| 办结/关单请求 | 「好了」「帮我关了吧」 | 记 `negativeExamples`，非新建意图 |
| 非故障白名单类型 | 违章、保养预约、合同条款 | 丢弃 |

### 4.2 必须保留信号

- 客户口语 + 仪表/车尾/漏液图（即使极短：「抛锚了」「什么故障」）
- 问句式报障（「这是离子水么」）
- 站拒加 / 漏气 / 无法开 / 自救无效 / 复发
- 群昵称内车牌、手机（拆槽位示例，不写进 aliases  unless 稳定格式）

### 4.3 分析产出闸

- [ ] 每条意图有 **≥2** 真实 utterance 或 1 条 + 合理 paraphrase（标注 `synthetic`）
- [ ] `faultType` 对齐 `dict.ts` `FAULT_TYPES` 或显式 `其他` + 备注
- [ ] 有 `negativeExamples` 防误触（至少：闲聊、开票、站通知各 1 条类例）
- [ ] Excel「解决方案」→ **仅** `solutionInternal`；**禁止**写入 `aliases` / 对客字段
- [ ] 表外现象标 `FD-UNMAPPED`，不强行绑 FD
- [ ] 车牌样例用 `浙A88888F` 格式（**禁** `·`）

## 5. 分类轴（部位 → 类型）

**部位 `vehiclePart`**（产品 IA，可与 scene 并存）：

| vehiclePart | 覆盖 |
|---|---|
| 供氢加氢 | 漏气、站拒加、加氢失败、氢量 |
| 冷却系统 | 离子水/冷却液、水温、膨胀水箱 |
| 燃电/动力 | 抛锚、混动切不过去、限扭、SOC 掉 |
| 电控仪表 | 故障灯、故障码、静默晒表、仪表 OCR |
| 底盘制动 | 刹车片、转向、打气泵、漏液（车底） |
| 电器灯光 | 大灯、全灯不亮、倒车影像 |
| 空调上装 | 空调风机、尾板液压 |
| 外观事故 | 碰撞、刮擦（少） |
| 其他 | 无法归类 → 仍建单 |

**故障类型 `faultType`**：优先用 `src/common/vehicle-fault/dict.ts` 的 `FAULT_TYPES`。  
Prompt 侧 `faultCategory`（供氢加氢/动力系统/…）与 `faultType` 可双写映射表。

**场景 `sceneId`**：S01–S18 见 `fcev-customer-report-lexicon.md` §3；新场景须 PRD 备注，不私自扩号 unless 用户授权。

## 6. 输出与集成

### 6.1 落盘路径（分析草案）

```text
src/resources/customer-fault-knowledge-base/
  corpus/
    intent-taxonomy-{batch}.md      ← 本 Skill 主产出（按批次）
    customer-fault-cases-corpus.md  ← 合并真实案例（kb-ops 写）
  machine/
    utterance-to-fault-rules.json   ← 增量规则（kb-ops 合并）
```

法眼总库（**勿**直接并入）：

```text
src/resources/oneos-knowledge-base/
  foundations/fcev-customer-report-lexicon.md  ← 口语归一行（kb-ops）
  modules/wecom-customer-fault-intent.md       ← 场景/槽位摘要
  machine/rules/*.json
```

### 6.2 故障 Bot 消费链

```text
intent-taxonomy MD + utterance-to-fault-rules.json
  → fault-bot-gateway / Prompt（wecom-customer-fault-prompt-dev-spec）
  → 向量集合 module_id=customer-fault（scripts/kb-vector/）
  → WO taskType=fault_feedback only
```

检索顺序对齐法眼：`kb-alias-index` → `machine/rules` → `modules/foundations` → `customer-fault` 独立语料。

### 6.3 交付包

分析完成交 kb-ops 时附：

```markdown
## 意图分析交付包
- 批次：{日期}-{来源文件名}
- 原料：{Excel 行数} → 有效报障 {n} → 意图条目 {m}
- 新意图：{列表} · 扩展现有意图：{列表}
- 未映射：{FD-UNMAPPED 列表}
- 噪声丢弃率：{%}
- 建议落点：corpus/intent-taxonomy-{batch}.md + rules 增量
- 待裁决：{口径疑问，交法眼}
```

## 7. 与相邻 Skill 分工

| Skill | 分工 |
|---|---|
| **本 Skill** | Excel→结构化意图 taxonomy、变体枚举、质量闸 |
| **oneos-kb-ops** | 定版入库、manifest、glossary、向量 ingest |
| **fayanruju** | 能不能做、场景/严重度口径裁决 |
| **yanchufasui** | 原型/Prompt/PRD 若需同步 |
| **oneos-qa-verify** | 意图命中率评测集 |

## 8. 附加资源

- 详 workflow：[`references/analysis-workflow.md`](references/analysis-workflow.md)
- MD 模板：[`references/intent-taxonomy-template.md`](references/intent-taxonomy-template.md)
- 安装：[`INSTALL.md`](INSTALL.md)

## 9. 示例批次（2026-08-25 · 体微绘画 14 群 Excel）

| 项 | 内容 |
|---|---|
| 原料 | 14 个 Excel · 9140 条消息 |
| 文档版本 | **v1.2.0**（边界意图 + 向量 ingest 就绪） |
| 有效客户报障 | 185 条 · 别名约 **746** |
| 边界语料 | 事故/保险 115 · 商务 202 · 冷机边界 7 · 电池预警 7 |
| 向量语料 | `twin-corpus/customer-fault-knowledge-corpus.md`（~122KB） |
| ingest | `node ingest.mjs --customer-fault`（dry-run 已通过） |
| 产出 | [`corpus/wecom-group-fault-intent-by-part-2026-08-25.md`](../../../src/resources/customer-fault-knowledge-base/corpus/wecom-group-fault-intent-by-part-2026-08-25.md) |
| 下一步 | 交 `oneos-kb-ops` 定版入库 + `utterance-to-fault-rules.json` 增量 |
