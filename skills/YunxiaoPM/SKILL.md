---
name: YunxiaoPM
description: >-
  产品经理云效（Projex）自动化：记录需求（压缩点选 1a2b3a4d：类型仅新增/优化、项目、优先级、标签）、
  实时点选云效项目、推进 待处理→已确认→分析中→设计中→设计完成→待开发、开发后受控取消需求，
  交付树【交付】ASSOCIATED /【分析】【设计】TASK_SUB，无单快轨与编号直推交棒到已明确且官方回读唯一的交付负责人，
  创建迭代并挂【交付】（不挂需求）。用户说 YunxiaoPM、需求任务、记录需求、受理确认、开始分析、
  开始设计、设计完成、交棒开发、快轨待开发、编号直推、创建迭代、关闭迭代、取消需求、拉取待验收需求、验收通过、验收不通过、验收续跑 时使用。
  全部云效读取和写入优先走官方 aliyun devops CLI/PAT；仅“关闭迭代”在已核实 CLI 缺少对应状态动作时，允许按受控视觉流程兜底，不依赖浏览器 Cookie。 不建【开发】/【测试】。
  新建或扩大范围的写入先 Plan 再 apply；明确编号的同批幂等刷新、续跑和补回读不重复确认；禁止对齐 yunxiao-requirement-lifecycle。
  交棒后开发 Skill：仅【优化】类从需求 MD 精炼写「修改前规则」；PM 修改 PRD/原型后生成并回读产品交棒快照。
---

# 需求任务（YunxiaoPM）

## 每日首次自动更新（强制，先于其他动作）

每个本地自然日首次触发本 Skill 时，先执行：

```text
node <本 Skill 目录>/scripts/ensure-daily-skill-update.mjs --current-skill YunxiaoPM
```

- `updated`：五个云效生命周期 Skill 已统一更新；必须重新完整读取本 `SKILL.md` 及本次所需引用后再继续。
- `skipped-today`：当天已经成功更新，直接继续。
- `in-progress`：另一个相关 Skill 正在执行同一更新，直接继续，不并发重复更新。
- `failed` / `unavailable` / `cooldown`：只给一条简短提示，继续当前任务；更新失败不得阻断云效工作。
- 共用更新范围固定为 `YunxiaoPM`、`yunxiao-development-delivery`、`development-brain`、`YunxiaoQA`、`yunxiao-release-operations` 的用户级全局安装；不得借此修改项目级 Skill、业务仓、云效数据、流水线或生产环境。不得手工伪造或提前写入每日成功状态。

产品部云效自动化。正式 Skill 名 **`YunxiaoPM`**，选择器 **`$YunxiaoPM`**；对外中文名 **需求任务**。
云效生命周期套件版本：`10.1.0`。

**自洽成篇**；**禁止** fork / include / 「对齐」已下架的旧 lifecycle。  
产品经理会话**不要**同时挂载旧 lifecycle Skill。

> **已定口径（优先读）** → [references/settled-rules.md](references/settled-rules.md)

## 0. 本轮组装要点（速记）

1. **类型只有** `【新增】` / `【优化】`（无【修复】前缀）
2. **本 Skill 不建**【开发】/【测试】；交棒终点 = 待开发 +【交付】负责人已由命令或项目配置明确并官方回读
3. **生成【交付】非占位描述**：必须 **`$AutoRDO`** → 单独一章「规则对照」含 **修改前规则 + 修改后规则**（见 AutoRDO `delivery-rules-chapter.md`）
4. **开发 Skill**【开发】描述：仅【优化】精炼写「修改前规则」（见 [dev-task-description.md](references/dev-task-description.md)）
5. 碎片入库先 **`$AutoRDO`**；设计完成灌 PRD 用 **`$oneos-autoprd`**
6. **产品交棒快照**：PRD/原型修改确认后生成；需求和【交付】都写入并回读同一快照编号/哈希；后续修改用`刷新产品快照`，不重推状态
7. 写云效分级：建需求、批量推进、取消、验收、创建迭代仍须 **Plan → 确认 → apply**；同一已授权批次中，明确编号且不扩范围的幂等刷新、续跑、补回读不重复确认
8. 云效执行只允许官方 `aliyun devops` CLI 与本 Skill 的 `yunxiao_cli_pm.py`；禁止 Cookie、XSRF、DOM 或网页内部接口回退。唯一例外为“关闭迭代”：先按 [iteration-close.md](references/iteration-close.md) 核验官方 CLI 与页面完整交互；CLI 缺少状态动作时才允许受控视觉兜底

## 官方 CLI 运行时（强制）

1. 运行 `skill-run yunxiao_cli_pm.py doctor`，认证只读取本机环境变量中的 PAT、组织ID或 Region API 地址
2. 写入前按命令分别预检：标准流程由 `preflight-standard` 冻结原有范围；产品快照由 `preflight-product-snapshot` 单独冻结快照哈希及目标需求/交付
3. 需确认的事务在用户通过 Plan 门禁后运行 apply；同一已授权批次的幂等刷新、续跑、补回读可直接续行。两类 apply 都必须重新读取守卫，发生漂移时零写入
4. 写入后按工作项内部ID回读状态、负责人、正式关系、迭代和文档；不得按标题猜测成功
5. 旧 `list_projects.py`、`list_tags.py`、`live_create_fast.py` 和 Cookie API 仅属历史实现，不得执行

## Plan 模式门禁（按写入风险分级）

1. **必须 Plan 并再次确认**：创建需求/任务树、批量推进、取消需求、产品验收、创建或关闭迭代，以及任何新增对象、扩大范围或改变既定责任人的动作。
2. **项目选择分级**：命令明确给出项目 ID，且官方 `projex-get-project` 唯一回读同一 ID 与项目名时，直接锁定项目，不再人工点选；未给 ID、ID 无法唯一回读或存在多个候选时，按 [project-selection.md](references/project-selection.md) 实时点选（PJ）。禁止静默使用缓存默认值。
3. Plan 写清：项目名+spaceId、需求/任务编号、将改状态、负责人及来源、交付·分析·设计编号策略、产品快照编号/哈希或占位缺失风险、迭代类型（若有）、**不会做的事**（不建【开发】/【测试】、不按标题查重）。记录需求仅对尚未由明确参数唯一锁定的项目/类型/优先级/标签展示 [compact-select.md](references/compact-select.md) 选择题。
4. 用户确认 / 批准 / 「执行」前禁止执行第 1 类 apply；压缩串先解析回显再等「执行」。
5. **无需重复确认**：同一已确认计划或同一幂等键下，目标项目和工作项编号均明确、操作只是在原范围内刷新产品快照、续跑未完成动作或补官方回读时，可重新预检后直接续行；任何对象、关系、负责人、状态边界或动作范围漂移，立即停止并重新 Plan。
6. 执行后按内部 ID 回读项目、编号、状态、负责人和正式关系，再校验回报。

**只读例外：** 仅查状态 / 解释 / 给方案不进 Plan。
**禁止：** 把“参数已齐”泛化成免确认；免确认只适用于上述明确编号、同范围、同幂等事务。

## 真相源模型

```text
需求状态 = 阶段看板唯一真相
【交付】 = 按交付端：Web|小程序→恰好1条；共用服务→恰好2条（Web+小程序，均 ASSOCIATED→需求）
【分析】/【设计】 = TASK_SUB→对应端侧交付（与 ASSOCIATED 同 create 互斥）
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
| 设计完成 PRD + 原型链接 | **`$oneos-autoprd`**；完成后按 [product-handoff-snapshot.md](references/product-handoff-snapshot.md) 生成产品快照（创建【交付】仍可占位；回填规则对照章仍走 AutoRDO） |
| 人员/状态/字段；项目 catalog 仅缓存 | [assets/runtime-ids.json](assets/runtime-ids.json) |
| PJ 项目点选 | [project-selection.md](references/project-selection.md) · 官方 `projex-search-projects` |
| 压缩点选 | [compact-select.md](references/compact-select.md) · 官方 `projex-list-labels` |
| 阶段日历工时 | [work-hours.md](references/work-hours.md) · [assets/cn-workday-calendar.json](assets/cn-workday-calendar.json) · [scripts/workday_hours.py](scripts/workday_hours.py) |
| 跨平台脚本启动 | [runtime-launcher.md](references/runtime-launcher.md) · `skill-run <script.py> [参数...]` |

## 跨 Skill 逻辑交接（强制）

- 上游/下游只传正式 Skill 名、需求/交付/开发/测试/发版任务编号、当前状态、`ASSOCIATED`/`TASK_SUB` 等正式关系，以及必要的附件、流水线、MR、版本或幂等证据标识。
- 禁止定位、读取、复制或要求用户提供其他 Skill 的安装目录；不同客户端之间不得通过物理文件路径共享常量、规则或运行时文件。
- 本 Skill 只读取自身包内资源；缺少人员、状态或项目常量时应实时查询云效，缺少交接编号时要求上游补齐，禁止跨 Skill 文件系统回退。
- 下一跳只输出正式选择器：开发用 `$yunxiao-development-delivery`，测试用 `$YunxiaoQA`，发布用 `$yunxiao-release-operations`。

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
| 关闭 / 归档迭代 | [iteration-close.md](references/iteration-close.md) |
| 生产后产品验收 | [release-acceptance.md](references/release-acceptance.md) · [scripts/accept_release.py](scripts/accept_release.py) |
| 口令面 | [commands.md](references/commands.md) |
| 记录需求元字段 | [record-meta-fields.md](references/record-meta-fields.md) |
| 验收 / 回报 | [acceptance.md](references/acceptance.md) |
| 交接契约（开发入口） | [handoff-contract.md](references/handoff-contract.md) |
| 产品修改后的交棒快照 | [product-handoff-snapshot.md](references/product-handoff-snapshot.md) |
| 【开发】描述（仅【优化】） | [dev-task-description.md](references/dev-task-description.md) |
| CLI 实写与回读 | [live-api.md](references/live-api.md) · [scripts/yunxiao_cli_pm.py](scripts/yunxiao_cli_pm.py) |
| 跨平台脚本启动器 | [runtime-launcher.md](references/runtime-launcher.md) |
| 耗时复盘 | [live-perf-2026-07-23.md](references/live-perf-2026-07-23.md) |

说明性长文（非执行必读）：根目录 `docs-*.md`。

## 口令速查

```text
记录需求：…；项目ID=…或项目=（未给ID时Plan点选）；交付端=Web|小程序|共用服务；优先级=紧急|高|中|低；标签=…；提交部门=…；提交人=…；交付负责人=姓名或userId；推进至=暂不推进|已确认|分析中|设计中|设计完成|待开发|待开发(快轨)
受理确认：ONEOS-xx
开始分析：ONEOS-xx
开始设计：ONEOS-xx；交付任务=…；分析任务=…
设计完成：ONEOS-xx；设计任务=…；原型=…
刷新产品快照：需求=ONEOS-xx；交付任务=ONEOS-a；快照文件=…
交棒开发：ONEOS-xx；交付任务=…；[交付负责人=姓名或userId]
快轨待开发：ONEOS-xx；[交付负责人=姓名或userId]
补建技术改进：标题=…；问题/目标=…；影响范围=…；验收口径=…；交付端=Web|小程序|共用服务；交付负责人=姓名或userId；来源交付单元=TEMPDEV-ID
编号直推：分析任务=ONEOS-b / 设计任务=ONEOS-c / 交付任务=ONEOS-a；[交付负责人=姓名或userId]
回退设计：需求=ONEOS-xx；交付=TASK-xx；原设计=TASK-xx；原因=…
创建迭代：交付端=Web|小程序；版本类型=主|副|子；交付任务=ONEOS-a,ONEOS-b,…；名称前缀=…
关闭迭代：迭代ID=…
取消需求：需求=ONEOS-xx；交付=TASK-xx；执行批次=TASK-xx；原因=…
拉取待验收需求：发版任务=TASK-900
验收通过：发版任务=TASK-900；验收人=…；证据=…
验收不通过：发版任务=TASK-900；验收人=…；原因=…；证据=…
```

类型写入标题时只用 **【新增】** 或 **【优化】**。

**交付端 → 交付条数：** `Web`/`小程序` → `开始分析`/`快轨待开发` 建 1 条【交付】；`共用服务` → 建 Web+小程序 共 2 条（均挂同一需求）。详见 [settled-rules.md](references/settled-rules.md)。  
**端侧标签：** 每条【交付】必打 `Web` 或 `小程序`（与模块标签并存），避免单端交付在列表中混淆。

## 本 Skill 的两个边界

1. 开发前：交棒完成（需求=待开发；【交付】负责人来自命令或项目配置且已官方回读；非占位交棒已回读产品快照编号/哈希）→「请技术经理使用开发 Skill」。
2. 生产后：按发版任务执行产品验收（**不以**发布生产证据区块为前置硬门；范围支持发版→需求或发版→【交付】→需求）。未指定子范围时验收冻结清单全部范围；指定组件/部署目标时只写该子范围验收事件，不关闭整批需求/交付/发版任务，并输出精确分支清理候选。全部范围通过后逐项、幂等地关闭需求、交付容器和发版任务；部分成功时重试只续跑未完成对象；不通过则记录统一证据、尝试将发版任务标为发布失败并正式交给测试侧发起修复回流。

例外：交棒后「创建迭代并关联交付」仍属本 Skill。

## §0.1 五条补齐（摘要）

1. **交棒占位**：标准路径交付仍为 `等待设计任务完成后自动填入` 时允许交棒，Plan 勾风险、回报标红；快轨有正文/原型时禁止占位  
2. **预计工时**：标准路径=阶段日历工时；快轨待开发需求默认预计/实际各 2  
3. **编号真相源**在「工作项编号（系统）」；新建后立即 PATCH  
4. **无单快轨**：【设计】描述同步需求；计划起止=当日；SUB→交付后补 ASSOCIATED→需求；交付描述手工或 AutoPRD；同标签；设计当日完成态  
5. **描述双段**不互相覆盖；迭代只挂【交付】；`共用服务` 双端交付分别挂入对应端侧迭代；回退重做设计则新开设计编号，交付计划开始不改  

## TEMPDEV补建正式技术改进

自然语言已表明代码先行且没有正式事项时，`补建技术改进`复用“记录优化需求 → 快轨待开发”的既有受控事务：创建一条中文优化需求及对应端侧【交付】，至少保存问题/目标、影响范围、负责人、验收口径和`sourceDeliveryUnitId`。不创建或修改Git分支、提交、MR，也不伪造【开发】任务；随后把正式需求/交付编号交给`$yunxiao-development-delivery`，由开发侧创建/关联【开发】并追加同一`adoptionId`的`DELIVERY_ADOPTED`。接口暂不可用时输出同字段的最小补单材料；只阻止生产认领，不阻止TEMPDEV继续编码和test验证。

细则见各 references。
