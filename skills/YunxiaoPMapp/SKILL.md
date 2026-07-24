---
name: YunxiaoPMapp
description: >-
  OneOS product-manager Yunxiao (云效) automation: record requirements, advance
  待处理→已确认→分析中→设计中→设计完成→待开发 handoff, delivery-tree tasks
  【交付】/【分析】/【设计】, fast-track and number-push handoff to 何斐, create
  sprints with V主.副.子 versioning. Use when PM says YunxiaoPMapp, 记录需求,
  受理确认, 开始分析, 开始设计, 设计完成, 交棒开发, 快轨待开发, 编号直推,
  创建迭代, or product-side Yunxiao writes. Does NOT create 【开发】/【测试】.
  On any write to Yunxiao, switch to Cursor Plan mode, confirm checklist, then
  apply in one shot. Never include or align with yunxiao-requirement-lifecycle.
---

# YunxiaoPMapp

产品部云效自动化（正式定名 **YunxiaoPMapp**）。本 Skill **自洽成篇**；**禁止** fork / include / 「对齐」`yunxiao-requirement-lifecycle`。

产品经理会话**不要**同时挂载旧 lifecycle Skill，避免双建任务。

## Plan 模式门禁（强制 · 凡写云效）

凡会改云效的操作（建单、改状态、建/改任务、打标、传附件、改负责人、建迭代等），Agent **第一步**必须：

1. `SwitchMode` → **plan**（说明：先对齐参数与执行清单，确认后再一口气 apply）。
2. Plan 写清：目标需求/任务**编号**、将改状态、将建/复用的交付·分析·设计编号策略、迭代版本类型（若适用）、§0.1① 占位风险勾选（若适用）、**不会做的事**（不建【开发】/【测试】、不按标题查重）。
3. **用户确认 / 批准 Plan / 「执行」之前**：禁止 apply。
4. 确认后切回 Agent，**同一轮按清单一口气执行到底**，再一次性校验回报；中途缺参才停下。

**例外（可读可不进 Plan）：** 仅查状态 / 为什么没流转 / 给我方案。

**禁止：** 以「参数已齐」「速度路径」「用户很熟」跳过 Plan；「批准计划」若清单未点齐关键参数，仍视为未完成门禁。

## 真相源模型

```text
需求状态 = 阶段看板唯一真相
【交付】 = 每需求最多 1 条容器（ASSOCIATED→需求）
【分析】/【设计】 = TASK_SUB→交付（交付「子项」必可见；与 ASSOCIATED 同 create 互斥）
【开发】/【测试】 = 不进本 Skill
查重/复用唯一渠道 = 任务编号（ONEOS-xx）；禁止按标题
```

编号权威：需求描述 `## 工作项编号（系统）`（见 [references/workitem-ids.md](references/workitem-ids.md)）。  
操作顺序：口令显式编号 > 读该区块 > ASSOCIATED/SUB 校验；冲突则停。

## 外置调用（禁止本 Skill 内嵌对方全文）

| 时机 | 调用 |
|---|---|
| 入库清洗聊天/录音 | **`$AutoRDO`**（独立 Skill；路径 `AutoRDO/SKILL.md`；不内嵌清洗细则） |
| 设计完成 PRD + 对象存储链接 + 回填【交付】 | **`$oneos-autoprd`（AutoPRD）**；创建【交付】仍占位，设计完成才灌 MD |
| 项目 ID / 何斐 ID / 字段 ID | [assets/runtime-ids.json](assets/runtime-ids.json) |
| 阶段日历工时 | [references/work-hours.md](references/work-hours.md) + [assets/cn-workday-calendar.json](assets/cn-workday-calendar.json) + [scripts/workday_hours.py](scripts/workday_hours.py) |

## 路由（按需完整阅读）

| 场景 | 模块 |
|---|---|
| 交付树、关联约定、禁止项 | [references/model.md](references/model.md) |
| 描述双段 · AutoRDO / 占位 / AutoPRD | [references/description-split.md](references/description-split.md) |
| 步骤 0–5 标准路径 | [references/stage-flow.md](references/stage-flow.md) |
| 无单快轨到待开发 | [references/fast-track.md](references/fast-track.md) |
| 编号直推交棒 | [references/number-push.md](references/number-push.md) |
| 交棒门禁 · 回退最小集 | [references/handoff-and-rollback.md](references/handoff-and-rollback.md) |
| 计划开始/完成 · 阶段日历工时 | [references/work-hours.md](references/work-hours.md) |
| Make 导出 ZIP + 复制截图 | [references/make-export-attach.md](references/make-export-attach.md) |
| 创建迭代 · V主.副.子 · 双挂 | [references/sprint.md](references/sprint.md) |
| 口令面 | [references/commands.md](references/commands.md) |
| 验收清单 · 回报模板 | [references/acceptance.md](references/acceptance.md) |
| 交接契约（开发 Skill 入口） | [references/handoff-contract.md](references/handoff-contract.md) |
| 已验证实写 API · 极速建单 | [references/live-api.md](references/live-api.md) · [scripts/live_create_fast.py](scripts/live_create_fast.py) |
| 2026-07-23 复盘与耗时对比 | [references/live-perf-2026-07-23.md](references/live-perf-2026-07-23.md) |

## 口令速查

```text
记录需求：…；推进至=暂不推进|已确认|分析中|设计中|设计完成|待开发|待开发(快轨)
受理确认：ONEOS-xx
开始分析：ONEOS-xx
开始设计：ONEOS-xx；交付任务=…；分析任务=…
设计完成：ONEOS-xx；设计任务=…；原型=…
交棒开发：ONEOS-xx；交付任务=…
快轨待开发：ONEOS-xx
编号直推：分析任务=ONEOS-b / 设计任务=ONEOS-c / 交付任务=ONEOS-a
创建迭代：版本类型=主|副|子；交付任务=ONEOS-a,ONEOS-b,…；名称前缀=…
```

后续口令**优先带任务编号**；未带则读「工作项编号（系统）」；仍无则询问；**禁止按标题补全**。

## 本 Skill 终点

交棒完成（需求=待开发；【交付】负责人=何斐）后结束。可一句：「请技术经理使用开发 Skill」。  
例外：交棒后「创建迭代并关联交付」仍属 YunxiaoPMapp。

**明确不做：** 创建【开发】/【测试】、挂仓库、开分支、提测、写用例。

## §0.1 五条补齐（摘要）

1. **交棒占位**：交付描述仍为 `等待设计任务完成后自动填入` 时**允许**交棒，但 Plan 必须勾选风险，回报首行标红；禁止假装材料齐全。
2. **预计工时** = **阶段日历工时**（工作日×8，非人力投入）；脚注与回报必须标明。
3. **编号真相源**在需求「工作项编号（系统）」；新建后立即 PATCH 该区块。
4. **无单快轨**【设计】须**当日收口**（计划完成=当日 + 工时 + 完成态）；不自动 AutoPRD。
5. **描述双段**不互相覆盖；迭代**交付+需求双挂**；回退重做设计则**新开设计编号**，交付计划开始不改。

细则见各 references。
