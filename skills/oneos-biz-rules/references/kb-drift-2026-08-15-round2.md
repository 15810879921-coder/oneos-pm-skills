# 法眼 · KB↔AutoPRD 漂移对表 · 第二轮（2026-08-15）

> 进化任务 `evo-fy-kb-round2` · 抽检：氢费账户/明细 · 任务工单 · 工作台待办。  
> 口径：KB 模块卡 / foundations vs 最新 AutoPRD / 原型 `.spec`；漂移须回写 KB 或标待同步。  
> 禁写云效 · 禁合 Master。

## 抽样

| # | 模块 | KB | AutoPRD / 权威 | 结论 |
|---|------|-----|----------------|------|
| 1 | 氢费账户 / 明细 | `payment-records` + `vehicle-h2-fee-ledger` | 中期架构 + `00-*` 冲突裁决 · 氢费核对≠对账 | **有漂移 → 已补** |
| 2 | 任务工单 | `modules/task-work-order.md` | 原型 `.spec` **prdVersion 1.5.0** + `prd/task-work-order-autoprd.md` | **有漂移 → 已补版本指针**；主规则对齐 |
| 3 | 工作台待办 | `foundations/workbench-todo-rules.md` + `modules/oneos-web-workbench-new.md` | 原型 `.spec`（董事长 116 / 催办白名单）· Autoprd 偏旧 | **规则卡对齐**；模块卡/Autoprd **已补指针与用词** |

## 1. 氢费（账户 + 车辆明细）

| 点 | KB 旧状 | 权威 | 处置 |
|----|---------|------|------|
| 核对 ≠ 对账 | `vehicle-h2-fee-ledger` 写「标记已对账 / 对账标记是核销前置」 | `00-digital-employee-voice` / `00-meeting`：**氢费核对 ≠ 对账** | **已改**产品叙事为「核对」；结清单据名可双写「对账单」 |
| 预付扣款门禁 | `payment-records`「已核对后扣费」 | 会议：核对 OCR/照片/台账一致后才扣款 | **保持**；显式钉死≠财务对账结清 |
| 置信度 | `architecture` | 尚无独立氢费 AutoPRD 定稿 | 保持 architecture；素材指针已补 |

## 2. 任务工单

| 点 | KB 旧状 | 权威 | 处置 |
|----|---------|------|------|
| 版本指针 | 「主 PRD 1.3.0」 | 原型 **1.5.0** | **已改** 1.5.0 |
| 首响仅故障反馈（客户） | 已有 | AutoPRD / `.spec` 一致 | 对齐 · 无改 |
| 聊天不可办结 | 已有 | 一致 | 对齐 |
| 一期大类 / 内部协同吞并 | 已有 | 一致 | 对齐 |
| 真企微 OpenAPI | 非本期接通 · WO-06 | 一致 | 对齐 |

## 3. 工作台待办

| 点 | KB / Autoprd 旧状 | 权威 | 处置 |
|----|-------------------|------|------|
| 董事长仅 `116` | foundations **已写**；模块卡未强调 | 原型 `.spec` + dual-track 探针 | **模块卡已补**总闸一句 |
| 催办白名单 / 超管不可催 | foundations **v1.0.6**；Autoprd 仍写「采购无催办」「总经理高风险催办」 | foundations §0.4 + 原型 | Autoprd **已加黄条**：催办/董事长以 foundations 为准 |
| 产品用词「审批」 | 模块卡「待办、审批」 | copy-lexicon · 审核 | **已改**审核；现网可双写 |
| 待办生成禁「仅查询权」 | foundations 已写 | 原型对齐 | 对齐 · 无改 |

## 下轮例行

双周评测日可再抽：消息中心、故障处置、加氢订单 H5。  
配对：`references/eval-mini.md` §0；首轮报告 `kb-drift-2026-08-14.md`。
