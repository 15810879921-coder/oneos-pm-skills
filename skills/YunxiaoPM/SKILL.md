---
name: YunxiaoPM
description: >-
  产品经理云效（Projex）自动化：记录需求（压缩点选 1a2b3a4d：类型仅新增/优化、项目、优先级、标签）、
  实时点选云效项目、推进 待处理→已确认→分析中→设计中→设计完成→待开发，
  交付树【交付】ASSOCIATED /【分析】【设计】TASK_SUB，无单快轨与编号直推交棒何斐，
  创建迭代并挂【交付】（不挂需求）。用户说 YunxiaoPM、YunxiaoPMapp、需求任务、记录需求、受理确认、开始分析、
  开始设计、设计完成、交棒开发、快轨待开发、编号直推、创建迭代 时使用。
  不建【开发】/【测试】。凡写云效先 Plan 再 apply；禁止对齐 yunxiao-requirement-lifecycle。
  交棒后开发 Skill：仅【优化】类从需求 MD 精炼写「修改前规则」。
---

# 需求任务（YunxiaoPM）

产品部云效自动化。斜杠 **`/YunxiaoPM`**；对外中文名 **需求任务**（旧名 YunxiaoPMapp 仍可触发）。

**自洽成篇**；**禁止** fork / include / 「对齐」`yunxiao-requirement-lifecycle`。  
产品经理会话**不要**同时挂载旧 lifecycle Skill。

> **已定口径（优先读）** → [references/settled-rules.md](references/settled-rules.md)

## 0. 本轮组装要点（速记）

1. **类型只有** `【新增】` / `【优化】`（无【修复】前缀）
2. **本 Skill 不建**【开发】/【测试】；交棒终点 = 待开发 +【交付】负责人何斐
3. **生成【交付】非占位描述**：必须 **`$AutoRDO`** → 单独一章「规则对照」含 **修改前规则 + 修改后规则**（见 AutoRDO `delivery-rules-chapter.md`）
4. **开发 Skill**【开发】描述：仅【优化】精炼写「修改前规则」（见 [dev-task-description.md](references/dev-task-description.md)）
5. 碎片入库先 **`$AutoRDO`**；设计完成灌 PRD 用 **`$oneos-autoprd`**
6. 凡写云效：**Plan → 确认 → 一口气 apply**；新建必 **PJ 点选项目**；记录需求默认 **`1a2b3a4d`**

## Plan 模式门禁（强制 · 凡写云效）

1. `SwitchMode` → **plan**
2. **新建**依赖项目空间：按 [project-selection.md](references/project-selection.md) **实时拉列表并点选（PJ）**；禁止静默用 `runtime-ids.json` 默认 `spaceIdentifier`；口令对不上则**自动重拉项目列表一次**，仍失败则停
3. Plan 写清：已选项目名+spaceId、需求/任务编号、将改状态、交付·分析·设计编号策略、迭代类型（若有）、§0.1① 占位风险（若有）、**不会做的事**（不建【开发】/【测试】、不按标题查重）。**记录需求**须给 [compact-select.md](references/compact-select.md) 1–4 题字母表，接受 `1a2b3a4d`
4. 用户确认 / 批准 / 「执行」前禁止 apply；压缩串先解析回显再等「执行」
5. 确认后切 Agent，**同一轮清单执行到底**，再校验回报

**例外（可读可不进 Plan）：** 仅查状态 / 解释 / 给方案。  
**禁止：** 以「参数已齐」跳过 Plan；关键参数（含 PJ）未点齐则「批准计划」仍不算过门禁。

## 真相源模型

```text
需求状态 = 阶段看板唯一真相
【交付】 = 每需求最多 1 条（ASSOCIATED→需求）
【分析】/【设计】 = TASK_SUB→交付（与 ASSOCIATED 同 create 互斥）
【开发】/【测试】 = 不进本 Skill
查重/复用 = 只认任务编号（ONEOS-xx）；禁止按标题
类型前缀 = 仅【新增】|【优化】
```

编号权威：需求描述 `## 工作项编号（系统）` → [workitem-ids.md](references/workitem-ids.md)。  
口令显式编号 > 读该区块 > ASSOCIATED/SUB 校验；冲突则停。

## 外置调用（禁止内嵌对方全文）

| 时机 | 调用 |
|---|---|
| 清洗聊天/录音/台账 | **`$AutoRDO`** |
| **生成/回填【交付】非占位描述** | **`$AutoRDO`** → 规则对照章（修改前+修改后）；见 AutoRDO `delivery-rules-chapter.md` |
| 设计完成 PRD + 原型链接 | **`$oneos-autoprd`**（创建【交付】仍可占位；回填时规则对照章仍走 AutoRDO） |
| 人员/状态/字段；项目 catalog 仅缓存 | [assets/runtime-ids.json](assets/runtime-ids.json) |
| PJ 项目点选 | [project-selection.md](references/project-selection.md) · [scripts/list_projects.py](scripts/list_projects.py) |
| 压缩点选 | [compact-select.md](references/compact-select.md) · [scripts/list_tags.py](scripts/list_tags.py) |
| 阶段日历工时 | [work-hours.md](references/work-hours.md) · [assets/cn-workday-calendar.json](assets/cn-workday-calendar.json) · [scripts/workday_hours.py](scripts/workday_hours.py) |

## 路由（按需阅读）

| 场景 | 模块 |
|---|---|
| **已定口径** | [settled-rules.md](references/settled-rules.md) |
| 交付树 / 禁止项 | [model.md](references/model.md) |
| 描述双段 AutoRDO / AutoPRD | [description-split.md](references/description-split.md) |
| 标准路径 0–5 | [stage-flow.md](references/stage-flow.md) |
| 无单快轨 | [fast-track.md](references/fast-track.md) |
| 编号直推交棒 | [number-push.md](references/number-push.md) |
| 交棒门禁 / 回退 | [handoff-and-rollback.md](references/handoff-and-rollback.md) |
| 计划工时 | [work-hours.md](references/work-hours.md) |
| Make 导出附件 | [make-export-attach.md](references/make-export-attach.md) |
| 创建迭代 | [sprint.md](references/sprint.md) |
| 口令面 | [commands.md](references/commands.md) |
| 记录需求元字段 | [record-meta-fields.md](references/record-meta-fields.md) |
| 验收 / 回报 | [acceptance.md](references/acceptance.md) |
| 交接契约（开发入口） | [handoff-contract.md](references/handoff-contract.md) |
| 【开发】描述（仅【优化】） | [dev-task-description.md](references/dev-task-description.md) |
| 实写 API | [live-api.md](references/live-api.md) · [scripts/live_create_fast.py](scripts/live_create_fast.py) |
| 耗时复盘 | [live-perf-2026-07-23.md](references/live-perf-2026-07-23.md) |

说明性长文（非执行必读）：根目录 `docs-*.md`。

## 口令速查

```text
记录需求：…；项目=（Plan 点选）；优先级=紧急|高|中|低；标签=…；提交部门=…；提交人=…；推进至=暂不推进|已确认|分析中|设计中|设计完成|待开发|待开发(快轨)
受理确认：ONEOS-xx
开始分析：ONEOS-xx
开始设计：ONEOS-xx；交付任务=…；分析任务=…
设计完成：ONEOS-xx；设计任务=…；原型=…
交棒开发：ONEOS-xx；交付任务=…
快轨待开发：ONEOS-xx
编号直推：分析任务=ONEOS-b / 设计任务=ONEOS-c / 交付任务=ONEOS-a
创建迭代：版本类型=主|副|子；交付任务=ONEOS-a,ONEOS-b,…；名称前缀=…
```

类型写入标题时只用 **【新增】** 或 **【优化】**。

## 本 Skill 终点

交棒完成（需求=待开发；【交付】负责人=何斐）→「请技术经理使用开发 Skill」。  
例外：交棒后「创建迭代并关联交付」仍属本 Skill。

## §0.1 五条补齐（摘要）

1. **交棒占位**：标准路径交付仍为 `等待设计任务完成后自动填入` 时允许交棒，Plan 勾风险、回报标红；快轨有正文/原型时禁止占位  
2. **预计工时**：标准路径=阶段日历工时；快轨待开发需求默认预计/实际各 2  
3. **编号真相源**在「工作项编号（系统）」；新建后立即 PATCH  
4. **无单快轨**：【设计】描述同步需求；计划起止=当日；SUB→交付后补 ASSOCIATED→需求；交付描述手工或 AutoPRD；同标签；设计当日完成态  
5. **描述双段**不互相覆盖；迭代只挂【交付】；回退重做设计则新开设计编号，交付计划开始不改  

细则见各 references。
