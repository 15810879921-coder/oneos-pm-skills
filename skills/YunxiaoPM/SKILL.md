---
name: YunxiaoPM
description: >-
  产品经理云效（Projex）自动化：记录需求（压缩点选 1a2b3a4d：类型/项目/优先级/标签）、
  实时点选云效项目、推进 待处理→已确认→分析中→设计中→设计完成→待开发，
  交付树【交付】ASSOCIATED /【分析】【设计】TASK_SUB，无单快轨与编号直推交棒何斐，
  创建迭代并挂【交付】（不挂需求）。用户说 YunxiaoPM、需求任务、记录需求、受理确认、开始分析、
  开始设计、设计完成、交棒开发、快轨待开发、编号直推、创建迭代 时使用。
  不建【开发】/【测试】。凡写云效先 Plan 确认再一口气 apply；禁止对齐
  yunxiao-requirement-lifecycle。
---

# 需求任务（YunxiaoPM）

产品部云效自动化。斜杠调起 **`/YunxiaoPM`**；对外中文名 **需求任务**。本 Skill **自洽成篇**；**禁止** fork / include / 「对齐」`yunxiao-requirement-lifecycle`。

安装名 **`YunxiaoPM`**（`npx skills add … --skill YunxiaoPM`）；斜杠 **`/YunxiaoPM`**；对外中文名 **需求任务**。

产品经理会话**不要**同时挂载旧 lifecycle Skill，避免双建任务。

## Plan 模式门禁（强制 · 凡写云效）

凡会改云效的操作（建单、改状态、建/改任务、打标、传附件、改负责人、建迭代等），Agent **第一步**必须：

1. `SwitchMode` → **plan**（说明：先对齐参数与执行清单，确认后再一口气 apply）。
2. **新建**依赖项目空间时：先按 [references/project-selection.md](references/project-selection.md) **实时拉项目列表并点选（门禁 PJ）**；禁止静默使用 `runtime-ids.json` 默认 `spaceIdentifier`。口令/选项**无法对应**时：**自动重拉项目列表一次**再匹配；仍失败则停请用户重选（禁止第 3 次空转拉取）。
3. Plan 写清：**已选项目名 + spaceId**、目标需求/任务**编号**、将改状态、将建/复用的交付·分析·设计编号策略、迭代版本类型（若适用）、§0.1① 占位风险勾选（若适用）、**不会做的事**（不建【开发】/【测试】、不按标题查重）。**记录需求**须按 [compact-select.md](references/compact-select.md) 给出 1–4 题字母表，接受压缩答复如 `1a2b3a4d`。
4. **用户确认 / 批准 Plan / 「执行」之前**：禁止 apply；项目未点选同禁。压缩串须先解析回显，再等「执行」。
5. 确认后切回 Agent，**同一轮按清单一口气执行到底**，再一次性校验回报；中途缺参才停下。

**例外（可读可不进 Plan）：** 仅查状态 / 为什么没流转 / 给我方案。

**禁止：** 以「参数已齐」「速度路径」「用户很熟」跳过 Plan；「批准计划」若清单未点齐关键参数（含 **PJ 项目**），仍视为未完成门禁。

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
| 人员 / 状态 / 字段 ID；项目 catalog 仅缓存 | [assets/runtime-ids.json](assets/runtime-ids.json) |
| **PJ 云效项目点选**（新建必选；实时列表） | [references/project-selection.md](references/project-selection.md) · [scripts/list_projects.py](scripts/list_projects.py) |
| **压缩点选 `1a2b3a4d`**（类型/项目/优先级/标签） | [references/compact-select.md](references/compact-select.md) · [scripts/list_tags.py](scripts/list_tags.py) |
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
| 创建迭代 · V主.副.子 · 只挂交付 | [references/sprint.md](references/sprint.md) |
| 口令面 | [references/commands.md](references/commands.md) |
| 记录需求元字段（优先级/标签/提交部门/提交人） | [references/record-meta-fields.md](references/record-meta-fields.md) |
| 云效项目点选 PJ | [references/project-selection.md](references/project-selection.md) |
| 验收清单 · 回报模板 | [references/acceptance.md](references/acceptance.md) |
| 交接契约（开发 Skill 入口） | [references/handoff-contract.md](references/handoff-contract.md) |
| 已验证实写 API · 极速建单 | [references/live-api.md](references/live-api.md) · [scripts/live_create_fast.py](scripts/live_create_fast.py) |
| 2026-07-23 复盘与耗时对比 | [references/live-perf-2026-07-23.md](references/live-perf-2026-07-23.md) |

## 口令速查

```text
记录需求：…；项目=（Plan 点选，勿默认）；优先级=紧急|高|中|低；标签=…；提交部门=…；提交人=…；推进至=暂不推进|已确认|分析中|设计中|设计完成|待开发|待开发(快轨)
受理确认：ONEOS-xx
开始分析：ONEOS-xx
开始设计：ONEOS-xx；交付任务=…；分析任务=…
设计完成：ONEOS-xx；设计任务=…；原型=…
交棒开发：ONEOS-xx；交付任务=…
快轨待开发：ONEOS-xx
编号直推：分析任务=ONEOS-b / 设计任务=ONEOS-c / 交付任务=ONEOS-a
创建迭代：版本类型=主|副|子；交付任务=ONEOS-a,ONEOS-b,…；名称前缀=…
```

**PJ 项目**：新建前必须从云效实时列表点选（见 [project-selection.md](references/project-selection.md)）；口令带项目名仅作预填建议。  
**压缩点选**：记录需求 Plan 展示 `1.类型 2.项目 3.优先级 4.标签` 字母表；你可回 `1a2b3a4d`（见 [compact-select.md](references/compact-select.md)）。标签未命中会自动重拉一次标签候选并重生选项。  
**记录需求**元字段（优先级/标签/提交部门/提交人）：与压缩点选并用；缺项用字母表补齐。见 [references/record-meta-fields.md](references/record-meta-fields.md)。

后续口令**优先带任务编号**；未带则读「工作项编号（系统）」；仍无则询问；**禁止按标题补全**。

## 本 Skill 终点

交棒完成（需求=待开发；【交付】负责人=何斐）后结束。可一句：「请技术经理使用开发 Skill」。  
例外：交棒后「创建迭代并关联交付」仍属 YunxiaoPM。

**明确不做：** 创建【开发】/【测试】、挂仓库、开分支、提测、写用例。

## §0.1 五条补齐（摘要）

1. **交棒占位**：标准路径下交付仍为 `等待设计任务完成后自动填入` 时**允许**交棒，但 Plan 必须勾选风险，回报首行标红。**快轨**有手工/原型时禁止占位（见 [fast-track.md](references/fast-track.md)）。
2. **预计工时**：标准路径 = **阶段日历工时**（工作日×8）；**快轨待开发**需求默认预计/实际各 **2**。
3. **编号真相源**在需求「工作项编号（系统）」；新建后立即 PATCH 该区块。
4. **无单快轨**：【设计】描述同步需求；计划起止=当日；TASK_SUB→交付后补 ASSOCIATED→需求；【交付】描述手工同步或 AutoPRD；交付/设计与需求同标签；设计当日完成态。
5. **描述双段**不互相覆盖；迭代**只挂【交付】**（需求不挂迭代）；回退重做设计则**新开设计编号**，交付计划开始不改。

细则见各 references。
