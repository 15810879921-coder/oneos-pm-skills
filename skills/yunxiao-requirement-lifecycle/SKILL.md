---
name: yunxiao-requirement-lifecycle
description: >-
  Audit, design, configure, migrate, test, troubleshoot, and document Alibaba Cloud
  Yunxiao/Projex requirement lifecycle automation. Use for short conversational Chinese
  commands such as 记录需求、确认需求、需求定稿、开始分析、开始开发、提交测试、测试完成、
  发布成功 and 验收通过; OneOS delivery or legacy stage-task model. When creating or
  refreshing OneOS product requirements, first call oneos-autoprd for 需求说明 and
  更新内容 (functional changelog since last 定稿), then write Yunxiao description.
  Also covers role handoffs, Codeup, Testhub, pipelines, release acceptance, migration,
  and Chinese runbooks without exposing credentials or changing production pipelines unexpectedly.
---

# Yunxiao Requirement Lifecycle

Use this as the single entry skill. Load only the internal modules needed for the request. Installing the skill does not change Yunxiao; live transitions start only after an authorized `apply` and verified `test` run.

## Route to modules

Read each selected file completely before acting:

| Request scope | Required module |
|---|---|
| OneOS终态模型、`【交付】`主任务、多开发子任务、迭代测试/发版、Y01–Y40、A01–A10、旧规则迁移 | [references/oneos-terminal-flow.md](references/oneos-terminal-flow.md) |
| Lifecycle statuses, requirement labels, related tasks, R01–R12, stage entry/completion | [references/lifecycle-rules.md](references/lifecycle-rules.md) |
| Design/development/test task creation, task states, rollups, TK01–TK08 | [references/task-lifecycle.md](references/task-lifecycle.md) |
| Test plans, case results, failed cases, bugs, retest, TC01–TC03, DF01–DF03 | [references/test-defect-closure.md](references/test-defect-closure.md) |
| Repositories, `dev`/`develop`, branches, commits, MRs, multi-repository gate, CI01 | [references/codeup-integration.md](references/codeup-integration.md) |
| test/prod pipelines, Docker callback, release changes, acceptance, CI02–CI03, L01–L02 | [references/pipeline-release.md](references/pipeline-release.md) |
| Live audit/apply/test, browser execution, evidence, diagnosis, rollback, governance | [references/live-operations.md](references/live-operations.md) |
| 日常口语化操作，使用“记录需求、开始分析、安排开发、提交测试、复测通过、发布成功”等短口令 | [references/simple-role-commands.md](references/simple-role-commands.md) |
| **统一运营管理平台**日常「记录需求」加速执行（已验证 ID / API / 状态三跳） | [references/oneos-pc-fast-path.md](references/oneos-pc-fast-path.md) + [assets/oneos-pc-runtime-ids.json](assets/oneos-pc-runtime-ids.json) |
| **统一运营管理平台**「记录需求到云效」完整可复制提示词（A/B/C 门禁 + 30 标签） | [references/oneos-pc-record-requirement-prompt.md](references/oneos-pc-record-requirement-prompt.md) |
| 需求进入分析中/设计中/待开发时自动建同名任务、关联需求、负责人与时间沿用 | [references/auto-stage-task.md](references/auto-stage-task.md) |
| 产品、分析、设计、开发、评审、测试、缺陷、运维、验收等角色的节点沟通话术和交接回报 | [references/role-trigger-prompts.md](references/role-trigger-prompts.md) |
| Final Chinese report | [references/report-template.md](references/report-template.md) |

## 记录需求 · 参数门禁与加速（强制）

当口令为「记录需求」且项目为统一运营管理平台（含 PC 端别名）时：

1. **先读** [references/oneos-pc-fast-path.md](references/oneos-pc-fast-path.md) 与 [assets/oneos-pc-runtime-ids.json](assets/oneos-pc-runtime-ids.json)，按快路径执行，禁止重复探测 create URL / 优先级 ID。
2. 若用户要求 Plan/单选优先级、推进至与标签：必须先拿到明确 **A+B+C**；**禁止**未选时默认「中 + 分析中」并建单。「批准计划」≠ 已选 A+B+C。完整用户口令见 [references/oneos-pc-record-requirement-prompt.md](references/oneos-pc-record-requirement-prompt.md)。
3. 优先 API 建单（创建时写入 `document`）、同名任务与打标签（`PATCH` `propertyKey=tag`）；浏览器仅用于标签 API 失败或状态连跳兜底。统一运营管理平台标签从 `assets/oneos-pc-tag-catalog.md` 选择器点选，禁止按 `lines.ts` 自动映射。

## AutoPRD 组合（强制 · OneOS 产品需求）

当请求涉及**创建产品类需求、写入/刷新需求描述、快轨待开发、完善需求说明/更新内容**，或用户口令含「记录需求（带模块/原型）」「需求已经确定」「需求定稿」并要进云效时：

1. **先**加载并执行项目/全局的 **`oneos-autoprd`** skill（勿跳过）。
2. 用其产出填充云效需求描述：
   - **需求说明** ← AutoPRD 正文（产品语言；不写表结构/接口/代码）
   - **更新内容** ← AutoPRD 第 10 章「功能变更记录」中自上次定稿以来的条目；无则「首版定稿」或「本轮无功能/逻辑增量」
   - 已有「更新内容」时：旧段挪到 **更新内容·历史**（倒序追加，勿删）
3. 原型发版增量以 AutoPRD 功能变更记录为准；PC 整包发版公告仍可另用 `AutoVUL`。
4. 对象存储链接、主任务、状态推进等仍按 `oneos-terminal-flow.md` / `simple-role-commands.md`。

`A02` / `A02B` 在 OneOS 项目上的默认实现方式即为调用 AutoPRD，不得只写占位文案。

## 阶段同名任务（强制 · AI apply）

凡将需求推进到 **分析中 / 设计中 / 待开发**（含口令「开始分析」「开始设计」「快速开发」「需求已经确定…待开发」等），必须先读并执行 [references/auto-stage-task.md](references/auto-stage-task.md)：

| 状态 | 任务 | 负责人 |
|---|---|---|
| 分析中 | 与需求**同名**；标签`分析`；正式关联需求 | 需求**创建人** |
| 设计中 | 与需求**同名**；标签`设计`；正式关联需求 | 需求**创建人** |
| 待开发 | 与需求**同名**；标签`交付`（或阶段模型下`开发`）；正式关联需求 | 固定**何斐** |

时间：任务计划开始（及可写的创建时间）**沿用需求**的计划开始/创建时间。查重幂等，禁止同阶段重复建单。

First identify `flow_model`:

- `stage_tasks`: use R01–R12 and TK01–TK08; read the five domain modules plus `live-operations.md` for a full audit.
- `oneos_delivery`: read `oneos-terminal-flow.md`, `codeup-integration.md`, `test-defect-closure.md`, `pipeline-release.md`, and `live-operations.md`.

For a narrow diagnosis, read the relevant domain module plus `live-operations.md`. Do not blend both models in one project or load unrelated modules merely because they exist.

## Classify authority

- `audit`: inspect and report only.
- `plan`: prepare a project profile and change plan only.
- `apply`: create or modify only explicitly named projects, labels, rules, and test assets.
- `test`: exercise approved rules with isolated artifacts and collect evidence.
- `document`: produce a Chinese runbook from verified facts.

Treat ambiguous requests as `audit` or `plan`. Documentation never authorizes live changes.

When the user uses a write verb defined in `simple-role-commands.md`—for example `记录需求`、`确认需求`、`开始分析`、`开始设计`、`开始开发`、`提交测试`、`复测通过`、`发布成功` or `验收通过`—treat it as `apply` authorization only for the current exact project and named work item. If the project is not exact, ask only for the project before writing. Query verbs such as `查状态`、`为什么没流转`、`下一步` and `给我方案` remain `audit` or `plan`.

Whenever apply changes a requirement status to `分析中`、`设计中` or `待开发`, also apply [references/auto-stage-task.md](references/auto-stage-task.md) in the same turn (same-name task, formal link, assignee and time rules) before reporting success.

## Build the project profile

1. Choose exactly one template and copy it outside the skill:
   - `stage_tasks`: `assets/project-profile.template.json`.
   - `oneos_delivery`: `assets/oneos-project-profile.template.json`.
2. Keep one independent object in `projects` for every target project; duplicate the template object when needed.
3. Replace observed statuses, rule instances, repositories, branches, pipelines, test plans, defect workflows, release evidence, and control dispositions.
4. Never add usernames, passwords, cookies, tokens, OTPs, Webhook secrets, or private keys.
5. Validate before applying:

```text
python scripts/profile_tool.py validate <profile.json>
python scripts/profile_tool.py render <profile.json> --output <execution-plan.md>

python scripts/oneos_profile_tool.py validate <oneos-profile.json>
python scripts/oneos_profile_tool.py render <oneos-profile.json> --output <execution-plan.md>
```

Do not apply while placeholders remain or validation fails.

## Completeness contract

For `stage_tasks`, account for every control for every project independently:

- `R01`–`R12`: requirement lifecycle and manual gates.
- `TK01`–`TK08`: stage-task creation, task-state transitions, requirement rollups, and idempotency.
- `TC01`–`TC03`: test-case execution, failed-case/defect association, and retest result update.
- `DF01`–`DF03`: fixed handoff, tester-pass closure, and tester-fail reopen.
- `CI01`–`CI03`: multi-repository coverage, callback safeguards, and environment/release separation.
- `L01`–`L02`: legacy immediate-close rule disposition.

Record the actual R01–R12 `rule_instances`, TK01–TK08 `task_rule_instances`, and all 31 `control_coverage` entries. Valid modes are `manual`, `native_rule`, `integration_bridge`, `disabled_legacy`, and `not_supported`. `not_supported` needs an owner and fallback and is never equivalent to automated.

Completeness covers the requirement lifecycle, stage-task lifecycle and rollups, Testhub closure, Codeup assets, pipeline/release evidence, and legacy-close controls. Notifications, SLA reminders, generic automatic assignment, and unrelated custom-field synchronization remain outside scope unless explicitly added to `adjunct_automations`.

For `oneos_delivery`, account for all 48 controls independently:

- `Y01`–`Y16`, `Y20`–`Y22`, `Y30`–`Y35`, `Y40`: native/mirrored lifecycle controls.
- `A01`, `A02`, `A02B`, `A03`–`A10`: AI/Webhook bridge controls.
- `TC01`–`TC03`, `DF01`–`DF03`, `CI01`–`CI03`, `L01`–`L02`: test, defect, code/release separation, and legacy-close controls.

Do not disable the old stage rules until the OneOS migration readiness gate passes: required requirement statuses exist, the main-task identity is filterable or procedurally exclusive, task workflows are ready, bridge owners and idempotency exist, and rollback evidence is saved. `L01` and `L02` remain disabled because they bypass acceptance.

## Global safety rules

- Reuse the authenticated browser session or approved semantic connector.
- Preserve unrelated rules and user edits.
- Never modify an existing production pipeline unless the user authorizes that exact change.
- Clone a test pipeline before callback experiments and modify only the clone.
- Require the expected current state in every automatic transition.
- Separate observed evidence from proposals and inference.
- Wait 5–30 seconds for asynchronous events and inspect execution logs.
- Stop at CAPTCHA, OTP, login approval, permission elevation, protected-branch ambiguity, or indistinguishable similarly named resources.

## Required outputs

Return only the applicable artifacts:

1. Observed inventory and current-versus-target matrix.
2. Per-project R01–R12 and TK01–TK08 rule-instance inventory with a 31-control ledger.
3. Live change log with reopen verification.
4. Test result per transition: `通过`、`异步通过`、`未触发`、`误触发` or `阻塞`.
5. Remaining risks, manual gates, and rollback steps.
6. When requested, a role-and-trigger communication playbook with copyable prompts, required evidence, next owner, and stop conditions.
7. For daily commands, answer briefly with the work item, actual state change, created/linked asset, blocker if any, and the exact next short command.
