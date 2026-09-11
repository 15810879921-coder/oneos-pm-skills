---
name: YunxiaoQA
description: >-
  测试人员云效（Projex）自动化：接收并开始【测试】任务，推进需求待测试→测试中，
  从可核验测试证据清单记录计划、用例执行、报告和test部署证据，诊断查重后一键发起缺陷；
  独立建缺陷和测试用例建缺陷均强制将验证者设置为当前登录测试用户并回读，
  （本期交付绑定开发负责人 / 非本期自指定负责人），拉取已修复|暂不修复待验清单，
  仅在每个Bug具有独立复测通过证据后批量关闭已修复、再次打开复现缺陷、已关闭并入当期迭代；普通完成路径维持原证据门禁，
  “完成测试”也可由测试人员显式给出“人工确认通过=是”进入审计放行分支；只有全部非取消开发任务均唯一映射测试任务且兄弟测试任务已完成时，才将当前【测试】标已完成并把需求推进测试完成，同时标记为非正式发布候选。
  用户说 YunxiaoQA、测试任务、拉取测试任务、发起缺陷、再次打开、批量关闭、并入迭代、
  开始测试、记录测试证据、完成测试、人工确认通过、闭环测试任务、接收发布回流、验证发布回流、交接发布 时使用。
  用户未写Skill名或标准口令，但自然语言明确表达查看本人测试任务、开始/继续/完成正式测试、记录证据、提Bug、复测关闭或重新打开时也主动调用；
  先通过官方CLI唯一定位【测试】任务或Bug，再规范化为现有命令。零候选或多候选只读返回，不按标题猜编号。
  仅运行本地代码测试、开发自测或修复代码而没有云效测试任务语境时不要触发。
  仅测试角色；不建【开发】/不创建迭代/不代开发改已修复。
  凡写云效先 Plan 确认再一口气 apply；禁止对齐 yunxiao-requirement-lifecycle。
---

# 测试任务（YunxiaoQA）

## 每日首次自动更新（强制，先于其他动作）

每个本地自然日首次触发本 Skill 时，先执行：

```text
node <本 Skill 目录>/scripts/ensure-daily-skill-update.mjs --current-skill YunxiaoQA
```

- `updated`：五个云效生命周期 Skill 已统一更新；必须重新完整读取本 `SKILL.md` 及本次所需引用后再继续。
- `skipped-today`：当天已经成功更新，直接继续。
- `in-progress`：另一个相关 Skill 正在执行同一更新，直接继续，不并发重复更新。
- `failed` / `unavailable` / `cooldown`：只给一条简短提示，继续当前任务；更新失败不得阻断云效工作。
- 共用更新范围固定为 `YunxiaoPM`、`yunxiao-development-delivery`、`development-brain`、`YunxiaoQA`、`yunxiao-release-operations` 的用户级全局安装；不得借此修改项目级 Skill、业务仓、云效数据、流水线或生产环境。不得手工伪造或提前写入每日成功状态。

> **客户端**：同一业务规则支持 Codex 与 Cursor；安装器负责选择客户端目录，生命周期交接不得依赖安装路径。

测试人员云效自动化。正式 Skill 名 **`YunxiaoQA`**，选择器 **`$YunxiaoQA`**；对外中文名 **测试任务**。本 Skill **自洽成篇**；**禁止** fork / include / 「对齐」`yunxiao-requirement-lifecycle`。

与 **YunxiaoPM（需求任务）**、开发交付 Skill 分工：本 Skill **只做测试侧**读写。

云效生命周期套件版本：`10.1.0`。

## Plan 模式门禁（强制 · 凡写云效）

凡会改云效的操作（建缺陷、改状态、闭环任务、挂迭代、改负责人/验证者等），Agent **第一步**必须：

1. `SwitchMode` → **plan**（说明：先对齐参数与执行清单，确认后再一口气 apply）。
2. **切换项目**时：口令带 `项目=` 或 Plan 点选；有 YunxiaoPM 时可复用其 PJ。禁止静默用错误 `spaceIdentifier`；确认后写入 `assets/runtime-ids.json` → `project.last_selected`。
3. Plan 写清：项目名 + spaceId、口令类型、涉及编号、目标状态、负责人/验证者、关联对象、**不会做的事**。
4. **用户确认 / 「执行」之前**：禁止 apply。
5. 确认后切回 Agent，**同一轮按清单一口气执行到底**，再一次性校验回报。

**例外：** 仅 `拉取测试任务` / `拉取待验缺陷` 且不改状态时可不进 Plan。用户给出完整的
`完成测试：测试任务=...；需求=...；人工确认通过=是`，该命令本身就是本次写入授权；脚本仍须先做对象、关系、当前登录测试用户和状态边界预检，但不得再要求第二次确认。

**禁止：** 以「参数已齐」「速度路径」跳过 Plan。

细则见 [references/plan-gate.md](references/plan-gate.md)。

## 真相源模型

```text
【测试】= 交付子项（TASK_SUB→【交付】）；由开发 Skill 在提测时创建（本 Skill 不建）
缺陷     = Bug；**必须** ASSOCIATED→【测试】（关联项，非父子）；产品需求写入描述追溯（本期不做需求 ASSOCIATED API）
开发归属 = Bug 与【测试】的关系只证明测试范围，不决定代码分支。Bug 可先创建、后补【开发】；已唯一关联【开发】的 Bug 回到对应开发分支，无开发归属的 Bug 才由开发侧建立独立 `fix/<Bug编号>` 分支
验证者   = workitem.verifier；所有测试侧建单路径均=当前登录测试用户，禁止口令覆盖
本期负责人=同交付【开发】负责人
缺陷打开态 = 待确认（禁止再用「待处理」指缺陷）
查重/复用 = 优先编号；禁止只按模糊标题瞎改他人单
测试可改状态 = 已修复→已关闭 | 已修复→再次打开 |（闭环）【测试】→已完成
测试阶段状态 = 【测试】待处理→处理中→已完成；首个正式范围可使需求开发中/开发完成/待测试→测试中；只有需求范围聚合闭环才→测试完成
完成测试/人工确认通过 = “完成测试”内的测试人员显式特批分支；跳过部署/TestHub/QA manifest/未关闭缺陷/范围聚合业务门禁，但保留对象唯一、正式关系、当前用户、状态边界、活动缺陷快照、官方回读与幂等审计；不改任何Bug，不作为正式发布候选
测试不改     = 待确认/再次打开/处理中 → 已修复|暂不修复|处理中（开发侧）
【测试】任务打开态 = 待处理 / 处理中（任务状态名，与缺陷待确认不同）
产品不建迭代 = 本 Skill 只把已关闭缺陷挂到已有当期迭代；迭代按端分列，缺陷只并入与来源【交付】端侧标签一致的迭代
交付端       = 【交付】端侧标签 Web / 小程序（PC 视为 Web）；Web 走test流水线证据，小程序按 testPipeline=skipped 跳过流水线与自动化测试
发布候选真相 = 完成态【测试】+ 测试证据块 + 测试完成需求 + 正式关系
常量       = assets/runtime-ids.json（2026-07-27 01_ONEOS 已实网补齐）
```

## 外置调用（禁止本 Skill 内嵌对方全文）

| 时机 | 调用 |
|---|---|
| 人员 / 项目 catalog / 通用状态 | 只读本 Skill [assets/runtime-ids.json](assets/runtime-ids.json)；缺项按交接编号实时查询云效 |
| PJ 云效项目点选 | 按 Plan/口令实时查询云效项目并将选中结果写回本 Skill 运行时配置 |
| 缺陷描述模板 / 定位矩阵 | 本 Skill [references/bug-template.md](references/bug-template.md) · [references/diagnosis.md](references/diagnosis.md) |
| 挂载点选【测试】/需求 | [references/anchor-selection.md](references/anchor-selection.md) · `scripts/list_bug_anchors.py` |
| 实写 API | [references/live-api.md](references/live-api.md)（01_ONEOS 已验证） |
| 测试执行闭环 | [references/test-execution.md](references/test-execution.md) · `scripts/yunxiao_cli_test_lifecycle.py` · `scripts/yunxiao_cli_bug_retest.py` |
| TestHub计划/用例执行 | [references/yunxiao-cli-testhub.md](references/yunxiao-cli-testhub.md) · `scripts/yunxiao_cli_testhub.py` |
| 列表/建缺/流转脚本 | [scripts/README.md](scripts/README.md) · `check_auth.py` / `list_bug_anchors.py` / `list_test_tasks.py` / `list_bugs.py` / `create_bug.py` / `transit_bug.py` / `close_test_task.py` |
| 跨平台脚本启动 | [references/runtime-launcher.md](references/runtime-launcher.md) · `skill-run <script.py> [参数...]` |

日常测试**优先本 Skill**；不必再挂载英文 `yunxiao-bug-triage`（诊断要点已收入本 Skill）。

## 跨 Skill 逻辑交接（强制）

- 只接收/输出正式 Skill 名、需求/交付/开发/测试/发版任务编号、当前状态、正式 `ASSOCIATED`/`TASK_SUB` 关系，以及测试计划、用例、缺陷、流水线、报告和幂等证据标识。
- 禁止定位、读取、复制或要求用户提供其他 Skill 的安装目录。本 Skill 只读取自身包内资源；缺少人员、项目或状态信息时按交接编号实时查询云效。
- 上游开发正式名为 `yunxiao-development-delivery`，下游发布正式名为 `yunxiao-release-operations`，产品回退正式名为 `YunxiaoPM`；选择器必须使用 `$<正式名称>`。

## 写操作铁律（防编号误判 · 强制）

历史事故：浏览器点状态菜单把 **ONEOS-343** 错关成 **ONEOS-309**。故：

1. **禁止**用 `cursor-ide-browser` / DOM 点击 /「可交互节点」改云效状态、负责人、关联、迭代。
2. **唯一常规写路径**：本 Skill `scripts/*.py`。TestHub 计划/用例/结果优先走官方阿里云 CLI；当前CLI与公开OpenAPI均缺少“规划已有用例”写能力时先返回`CLI_CAPABILITY_GAP`并零写入。只有用户在Plan中明确确认“指定测试计划+指定既有用例”的一次性页面补齐，才允许在隔离测试计划中执行该单一动作；随后必须立即回到CLI回读计划内用例并更新结果。该例外禁止改工作项状态、禁止猜测接口、禁止扩展到其他计划。
3. **编号硬门禁**：口令 `ONEOS-xx` → 脚本 `--sn` → `serialNumber ==` 精确匹配 → apply → **回读** `serialNumber|subject|from→to`；任一不对立刻停。
4. **开始/记录/完成测试**：只用 `skill-run yunxiao_cli_test_lifecycle.py start|record|complete ...`；当“完成测试”显式携带`人工确认通过=是`时，内部转为该脚本的`manual-complete`；逐Bug复测关闭只用 `skill-run yunxiao_cli_bug_retest.py ...`。普通路径维持原官方 CLI 证据门禁；`manual-complete`只校验安全与审计边界并记录被跳过的业务门禁。所有写入均须官方回读。`skill-run` 按 [references/runtime-launcher.md](references/runtime-launcher.md) 解析。
5. **旧闭环入口**：`close_test_task.py`已停用并固定拒绝写入；`transit_test_lifecycle.py`保留为旧Cookie兼容实现但禁止用于新执行；`闭环测试任务`兼容口令必须转入`yunxiao_cli_test_lifecycle.py complete`完整门禁。
6. Projex与TestHub新闭环只许PAT/组织ID/官方CLI。旧Cookie脚本只可用于历史诊断，**禁止**改走浏览器点选「凑合关单」。

## 路由（按需完整阅读）

| 场景 | 模块 |
|---|---|
| 口令面 | [references/commands.md](references/commands.md) |
| 主动识别 / 自然语言命令 / 唯一测试任务定位 | [references/semantic-routing.md](references/semantic-routing.md) |
| 开始测试 / 证据 / 完成测试 / 发布交接 | [references/test-execution.md](references/test-execution.md) · [references/test-scope-aggregation.md](references/test-scope-aggregation.md) |
| 条线 1/2 · 状态机 · 再次打开 | [references/defect-flow.md](references/defect-flow.md) |
| 诊断 · 查重 · 分层初判 | [references/diagnosis.md](references/diagnosis.md) |
| 缺陷描述模板 | [references/bug-template.md](references/bug-template.md) |
| Plan 确认清单 | [references/plan-gate.md](references/plan-gate.md) |
| 挂载点选 | [references/anchor-selection.md](references/anchor-selection.md) |
| 实写 API | [references/live-api.md](references/live-api.md) |
| 跨平台脚本启动器 | [references/runtime-launcher.md](references/runtime-launcher.md) |

## 口令速查

```text
拉取测试任务：状态=待处理|处理中；[项目=…]
开始测试：测试任务=ONEOS-xx；[需求=ONEOS-yy]
记录测试证据：测试任务=ONEOS-xx；证据清单=<JSON文件>
发起缺陷：标题=…；描述=…；测试任务=ONEOS-xx；[需求=ONEOS-yy]；[开发任务=ONEOS-zz]；[交付单元=ID]；[负责人=…]；[证据=…]
从测试用例发起缺陷：测试用例=CASE-xx；标题=…；描述=…；测试任务=ONEOS-xx；[需求=ONEOS-yy]；[开发任务=ONEOS-zz]；[交付单元=ID]；[负责人=…]；[证据=…]
发起缺陷(非本期)：标题=…；描述=…；负责人=…；[测试任务=…]；[项目=…]
# 无测试任务的非本期须显式声明，默认仍要求挂测试子项+需求
拉取待验缺陷：状态=已修复|暂不修复；[测试任务=…]；[负责人=…]
批量关闭已修复：缺陷=ONEOS-a；复测用例=CASE-ID；复测执行=RUN-ID；test版本=VERSION；证据=ID或URL；验证人=当前用户
再次打开：缺陷=ONEOS-xx；[原因=复现说明]；[证据=…]
并入当期迭代：缺陷=… 或 范围=已关闭且未挂迭代；迭代=（当期/指定名）
完成测试：测试任务=ONEOS-xx；[需求=ONEOS-yy]；证据清单=<JSON文件>；[暂不修复批准=BUG-ID=批准人|证据]
完成测试：测试任务=ONEOS-xx；需求=ONEOS-yy；人工确认通过=是；[说明=测试人员确认通过]
接收发布回流：发版任务=TASK-900；触发=发布失败|产品验收失败；证据=ID或URL
验证发布回流：发版任务=TASK-900；缺陷=ONEOS-a,ONEOS-b；回归证据清单=<JSON文件>
闭环测试任务：测试任务=ONEOS-xx（兼容旧口令；按“完成测试”门禁执行）
```

**编号优先**：口令显式 `ONEOS-xx` > 当前上下文 > 询问；**禁止按标题猜编号后静默写云效**。

隐式调用或用户使用口语表达时，先完整读取[主动识别与语义路由](references/semantic-routing.md)，将原话规范化为本页已有口令；不得绕过Plan、编号、关系、证据和回读门禁。

## 发起缺陷流水线（强制 · 方案 B）

每次 `发起缺陷` / `从测试用例发起缺陷` / `发起缺陷(非本期)`：

1. **规范化证据**（环境、路径、角色、时间、步骤、实际/期望、截图；无秘密）
2. **查重**（活跃 + 近期关闭；同因则更新旧单并回报，不问则新建）
3. **分层初判**（前端/后端/数据/配置/环境；标「推断」）
4. **填模板** → 见 [bug-template.md](references/bug-template.md)
5. **字段**：验证者=当前登录测试用户，禁止口令覆盖；本期负责人=同交付【开发】负责人（多人 Plan 点选）；非本期负责人=口令必填
   - 独立创建：`create_bug.py --source standalone`
   - 测试用例创建：`create_bug.py --source test-case --test-case <用例编号/执行记录>`
   - 两条路径必须进入同一个建单处理器。apply 后以云效在新建 Bug 上记录的当前会话用户为真相，写入`workitem.verifier`并回读；不以固定姓名、负责人、开发人、测试主管或口令参数代替。
5b. **挂载点选**：口令未给出唯一 `测试任务=` 时，先跑 `list_bug_anchors.py`，用 **AskQuestion** 点选【测试】；需求可点选/追溯，写入描述作追溯（非关联项）。未点选【测试】禁止 create。详见 [anchor-selection.md](references/anchor-selection.md)。
6. **关联**：
   - **硬门禁**：缺陷 **create 时**挂 `ASSOCIATED→【测试】`（关联项；**禁止** TASK_SUB/父子）；回读 ASSOCIATED 校验，失败退出码 3。
   - **需求**：点选/追溯后写入描述「追溯需求」段；**不做** Cookie 事后 `ASSOCIATED→需求`（不告警、不伪造成功）。口令 `需求=` / `--req` 可覆盖。
   - **开发归属提示**：若已存在唯一【开发】任务，可把其编号和 `deliveryUnitId` 写入描述追溯段，供开发侧选分支；这不是正式关系，不存在时不阻止建 Bug。开发任务后置时由开发/产品侧补正式关系，再以交付台账回填 `DEVELOPMENT_TASK_AGGREGATED`。
7. Plan 回显 → 确认 → apply（`create_bug.py`）→ 回读当前用户=验证者及【测试】关联 → 回报；任一校验失败须停

## 测试完成硬门禁

执行`完成测试`前必须同时满足：

1. 【测试】=`处理中`且正式`TASK_SUB→【交付】`、`ASSOCIATED→需求`。
2. 需求=`测试中`。
3. 开发交接中的`oneos.test-deployment/v1`区块按`deliveryEnd`分流：**Web**表明版本已成功部署到test，且项目、迭代、需求、测试任务、执行ID和部署版本均一致；**小程序**为`testPipeline=skipped`、`status=skipped`且含`reason`，项目、迭代、需求、测试任务一致，不要求test流水线与自动化测试证据。
4. `oneos.qa-evidence/v1`证据清单已从真实测试资产读取并校验，包含计划ID/URL、用例执行ID/URL、报告ID/URL、test部署执行和SHA-256；禁止用聊天参数、自填“0失败”或占位链接代替。
5. 当前测试范围所选用例无未执行、失败或阻塞，且范围计数闭合；不得使用整份需求计划总计数代替当前端范围。
6. 无`待确认/处理中/已修复/再次打开`缺陷；每条已关闭Bug均带独立`oneos.bug-retest/v1`复测通过证据。
7. 每条`暂不修复`缺陷都有明确批准人和证据；只有状态没有批准证据仍阻塞。
8. 证据块写入并回读后，先推进当前【测试】→`已完成`；仅`--aggregate-complete`且所有关联开发/测试范围已闭环时才推进需求→`测试完成`。
9. 输出项目、必填迭代、需求、交付、测试任务、部署版本、缺陷状态、证据清单哈希、完成时间和幂等键，交给`$yunxiao-release-operations`组建发布批次。

`完成测试`中显式的`人工确认通过=是`是上述证据门禁的唯一例外：可不要求部署证据、TestHub计划/用例、QA manifest或缺陷关闭，但不得跳过开发任务与测试任务的一一映射和需求范围聚合。全部非取消开发任务均有唯一测试任务、兄弟测试任务已完成后，才将当前【测试】推进`已完成`并把需求推进`测试完成`。必须把当前登录测试用户、时间、说明、幂等键、跳过项、范围聚合和关联缺陷快照写入`oneos.qa-manual-complete/v1`并回读；关联Bug保持原状，禁止伪造成普通测试证据，交接标记为非正式发布候选。

## 本 Skill 终点与明确不做

- **终点**：完成测试执行与缺陷闭环，推进需求到测试完成，并输出可机器校验的发布候选交接。
- **明确不做：** 创建【开发】/【测试】任务、代开发标「已修复/暂不修复」、创建迭代、改产品/开发阶段状态、挂仓库/开分支/提 MR。
- 本 Skill明确拥有且只拥有需求测试阶段`待测试→测试中→测试完成`。

缺陷回流交接：「开发侧请用开发 Skill 拉待确认/再次打开缺陷并标已修复|暂不修复。」
测试完成交接：「发布侧请用`$yunxiao-release-operations`组建发布批次。」

发布或产品验收失败后的正式回流按[release-repair-loop.md](references/release-repair-loop.md)执行；不得直接重跑生产或直接再次验收。

## 验收清单（回报自检）

- [ ] 拉【测试】：仅待处理/处理中（或口令指定）
- [ ] 开始测试：【测试】待处理→处理中；需求待测试→测试中；两侧均回读
- [ ] 发起缺陷（独立/测试用例）：验证者=当前登录用户且已回读；负责人/关联正确；走过查重+模板
- [ ] Bug 分支提示：测试关系未被误当作开发归属；有唯一开发任务则保留提示，无开发任务仍正常建 Bug
- [ ] 再次打开：仅自「已修复」且有复现说明；负责人未误改
- [ ] 批量关闭：逐Bug复测证据已写入并回读；仅「已修复」→「已关闭」
- [ ] 并入迭代：仅「已关闭」；迭代已存在（未新建）
- [ ] 完成测试：test部署与QA证据清单已校验，证据块已写并回读；关联缺陷全部闭环；暂不修复均有批准证据
- [ ] 完成测试/人工确认通过：当前测试用户、说明、跳过项、缺陷快照和幂等键已写入并回读；Bug未被修改；已标记非正式发布候选
- [ ] 状态闭环：【测试】处理中→已完成；需求测试中→测试完成；两侧均回读
- [ ] 发布交接：项目/迭代/需求/交付/测试证据/幂等键完整
- [ ] 每次写操作回报含一行：`serialNumber | subject | from→to`（与口令编号一致）
- [ ] 本轮无浏览器改状态；无建【开发】、无创建迭代、无代开发改状态
