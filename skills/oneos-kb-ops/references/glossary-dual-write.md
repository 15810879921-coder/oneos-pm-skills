# 术语双写清册

> **进化任务**：`evo-kb-glossary-drift-sweep`  
> **版本**：v1.0.0 · 2026-08-21  
> **硬闸**：卡内重复写定义 = 漂移；回收方向 = **只留 glossary + termRefs/metricRef**，正文改引用。本表只登记，**不等于已回收**。

## 0. 扫描范围与方法

| 项 | 说明 |
|----|------|
| 扫描日 | 2026-08-21 |
| 范围 | `machine/glossary.json` · `machine/rules/*.json` 的 `rules[].text` · `metrics[].definition` · `modules/*.md` 散句 |
| 方法 | 人工对照 glossary `terms[].id` 与卡内是否重写同义定义 |
| 未映射 | 概念在卡内出现但 glossary 无 id → 标 **unmapped**，不编新义 |

## 1. 双写清册（≥8 行）

| # | 术语 id / 概念 | 出现卡（锚点） | 双写形态（摘要） | 建议单源 | 状态 |
|---|----------------|----------------|------------------|----------|------|
| G1 | `grace-period` | `biz-finance-integration` → metric `grace-days` | metric 内 `definition` + `formula` 重写宽限与逾期判定 | `glossary.json#grace-period` + metric 只留 formula/values | **待回收** |
| G2 | `h2-fee-check` | `document-numbering` rules「核对≠财务套账对账」 | 卡内复述核对与对账边界 | `glossary.json#h2-fee-check` + `termRefs` | **待回收** |
| G3 | `reconciliation` | `vehicle-h2-fee-ledger` · `ledger-h2-procurement-summary` | 「已对账」「进入账户对账单」与核对混写 | `glossary.json#reconciliation` + 卡内只写流程 | **待回收** |
| G4 | `contract-as-rule` | `lease-contract-management` rules[0] | 「合同即规则一对一锁死…驱动提车/账单/还车/里程」整段定义式叙述 | `glossary.json#contract-as-rule` + `termRefs` | **待回收** |
| G5 | `actual-delivery-date` | `biz-finance-integration` rules「计费起算归业务确认…不取运维交车日」 | 与 glossary `disambiguation` 重复 | `glossary.json#actual-delivery-date` | **待回收** |
| G6 | `non-standard-review` | `lease-contract-management` · `customer-management` · `contract-template-management` | 多处「改红线→非标审核/审批」流程句含定义口吻 | `glossary.json#non-standard-review`（若缺则先补 glossary 再回收） | **unmapped**（glossary 有 id 但卡未挂 termRefs） |
| G7 | 审核 vs 审批（文案口径） | `vehicle-pickup-receivable` · `lease-contract-management` validity.note | supersedes 行内再解释「产品叙事用审核」 | Rule `oneos-copy-shenhe` + glossary 不重复；卡内只 `supersedes` 指针 | **待回收**（文案层，非业务定义） |
| G8 | `ops-delivery-date` | `ops-vehicle-prepare` · 多卡 forward「交车前置」 | 「交车前置」未引用 glossary，易与 `actual-delivery-date` 混 | `glossary.json#ops-delivery-date` + 备车卡补 `termRefs` | **待回收** |
| G9 | 核对 ≠ 对账（V2） | `oneos-h5-h2-order` · `biz-finance-integration` rules | 英文括号 `verify vs reconcile` 与中文定义双轨 | `glossary.json#h2-fee-check` + `#reconciliation` | **待回收** |
| G10 | `false-closure` | `biz-finance-integration` forbidden / 业财红牌散句 | 「假性闭环」「无关联结清」未统一 termRefs | `glossary.json#false-closure` | **unmapped**（glossary 有 term，卡内未挂 ref） |

**本波结论**：清册 **10 行**；**0 行已回收**。回收执行另波（改 JSON + 跑 retrieval-eval W11/W13–W15）。

## 2. 回收优先级

```text
P0：G1/G9（法眼高频 · W1/W6/W13 评测题）
P1：G4/G5/G8（租赁主链）
P2：G2/G3/G7/G10（能源/文案层）
```

## 3. 交付自检

```text
✅ ≥8 行真实锚点，unmapped 诚实标注
✅ 未宣称「双写已清零」
❌ 为凑行数编不存在的卡
❌ 回收前删卡内业务约束只留空 termRefs
```
