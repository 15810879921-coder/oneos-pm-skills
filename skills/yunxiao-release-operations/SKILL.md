---
name: yunxiao-release-operations
description: >-
  Manage Alibaba Cloud Yunxiao release operations through seven commands:
  准备发布, 执行测试流水线, 执行生产流水线, 执行发布, 执行回滚, 重新发布, and 查询发布.
  Classify exact iteration scope, create/reuse release tasks, run and diagnose pipelines,
  verify production, preserve attempt evidence, and perform one gated rollback or authorized
  re-release. Every Projex, Flow, Codeup, and AppStack read/write uses the official aliyun devops
  CLI with guarded preflight, drift detection, one write pass, targeted read-back, and idempotent
  receipts. Browser, visual, DOM, Cookie, connector, and webpage-internal API fallbacks are forbidden.
  Never treat pipeline success alone as release success, expose secrets, or change pipeline definitions.
---

# Yunxiao Release Operations

Operate deployment and release evidence while keeping test, production verification, rollback, and product acceptance separate. Suite version: `9.8.0`.

## Load the required references

Read each selected file completely before acting:

- Release task, pipeline, stage-task and OneOS controls: [references/controls.md](references/controls.md).
- Short Chinese commands and expected actions: [references/commands.md](references/commands.md).
- Release-batch creation and A/B/C/D scope rules: [references/release-batch.md](references/release-batch.md).
- Changed-code component discovery, merge evidence, and multi-service production matrix: [references/release-assets.md](references/release-assets.md).
- PC single-end and shared-service dual-end topology classification: [references/release-topology.md](references/release-topology.md).
- Business-readable release-task descriptions and hidden managed data: [references/release-description.md](references/release-description.md).
- Runtime write order and callback verification: [references/execution-runtime.md](references/execution-runtime.md).
- Official CLI environment, guarded transactions, pipeline monitoring, idempotency, and performance: [references/yunxiao-cli-runtime.md](references/yunxiao-cli-runtime.md).
- Cross-platform bundled-script launcher: [references/runtime-launcher.md](references/runtime-launcher.md).
- Callback, evidence, authorization, live-change safety, and cross-skill handoff: [references/safety-handoff.md](references/safety-handoff.md).

## Own only the operations boundary

Own these outcomes:

1. Directly start one uniquely resolved test or production pipeline when the matching explicit execution command is given, monitor it to a terminal state, and collect failed-step logs when it fails.
2. Record test deployment evidence without promoting release state.
3. From one exact iteration, automatically derive all test-complete release candidates, classify A/B/C/D scope, and freeze the derived release batch directly inside one `【发版】` task. Accept explicit requirement IDs only for an exceptional partial release.
4. Create or reuse that exact top-level release task, formally relate it to the iteration, A-class requirements, their source delivery tasks, and qualifying same-iteration completed Bugs with no formal work-item relation of any kind; render a business-readable update log before hidden managed data; freeze the changed-code component release matrix and record approval, window, rollback, and production-verification readiness.
5. Verify test completion, scope, each changed component's merge evidence and production-pipeline mapping; approval and rollback metadata remain optional records.
6. Start every exact authorized production execution in the frozen component matrix, in its declared dependency order.
7. After technical production success, run any available production checks and record unavailable checks as `未自动验证`; missing optional checks do not block technical release completion.
8. Verify the live CLI execution ID, logical production environment, frozen scope, terminal status, and idempotency. Validate callback signatures only when a callback is actually used.
9. Move the release task and requirements to `发布完成` only after every required component execution succeeds and each environment and scope read back correctly; keep business acceptance separate.
10. When `执行发布` reaches either a verified terminal production failure or an explicit production-verification failure, preserve evidence and automatically execute the exact stored rollback once.
11. On `执行回滚`, handle an evidenced post-release defect or business-verification failure before product acceptance closes the lifecycle, using the same stored rollback and idempotency gates.
12. Record and return the problem symptom, failure point, impact, diagnosis confidence, original and rollback executions, recovery result, residual risk, owner, and next action.
13. Hand only a verified `发布完成` to `YunxiaoPM` for acceptance.
14. After a release or product-acceptance failure, emit the formal QA repair intake; accept `重新发布` after the affected scope is repaired, affected Bugs are closed, current regression evidence is supplied, and the user explicitly authorizes re-release.

Do not execute test cases, edit application code, or close a requirement after release success.

## Cross-Skill logical handoff

- Accept and emit only formal Skill names, exact requirement/test/release/execution task IDs, live states, formal relations, frozen batch scope, and necessary pipeline, deployment, verification, rollback, evidence, or idempotency identifiers.
- Never discover, read, copy, or require another Skill's installation directory. Resolve missing facts from the explicit handoff IDs and live Yunxiao services; keep all bundled rules local to this Skill.
- Test intake uses `/skill YunxiaoQA`, development return uses `/skill yunxiao-development-delivery`, and production-acceptance handoff uses `/skill YunxiaoPM`. Never emit a legacy alias or filesystem path as a command.

## Classify authority

- `audit`: inspect pipelines, executions, callbacks, rules, and evidence only.
- `plan`: prepare release scope or rollback plan only.
- `apply`: create/update exact release tasks and authorized states.
- `execute`: run the exact named test or production pipeline, run the exact release production execution and frozen production-verification plan, or execute the exact stored rollback.
- `document`: produce release notes or evidence reports.

`执行测试流水线：流水线=名称` and `执行生产流水线：流水线=名称` each authorize one immediate execution of the uniquely resolved existing pipeline. Do not ask for a second confirmation. A repeated command in a new user message is a new execution authorization. The command does not authorize changing the pipeline definition, bypassing a pipeline approval stage, or writing release status.

Every command that runs or monitors a pipeline must automatically collect and output the first failed stage, job, task, step, redacted log evidence, diagnosis confidence, impact, and next action when it ends unsuccessfully. Do not require or generate a separate failure-analysis command.

`执行发布：发版任务=ID` branches by source-delivery end tags (`Web` / `小程序`; `PC` aliases to `Web`; mixed ends block). **小程序** skips cloud production pipelines and external evidence, records a successful `miniprogram_skip_pipeline` attempt, writes `发布完成` on the release task and in-scope requirements, then emits the same YunxiaoPM acceptance handoff. **Web** uses the frozen changed-code component matrix: after each required component is proven merged to `master` and uniquely mapped to its production pipeline, create or reuse exactly one persisted `releaseAttemptId` with `attemptNo=1` and `attemptType=initial`; start at most one production execution per required component, or resume its existing execution, verification, or automatic rollback. A repeated `执行发布` may continue the same nonterminal attempt after an interruption, but never creates a duplicate component execution. Once that attempt reaches verified success or failure, it is terminal: success is returned idempotently, while failure may only finish/return the stored rollback and repair handoff. Any new production execution after a failed release requires `重新发布`. It does not authorize changing pipeline definitions, bypassing an approval stage, guessing a rollback target, deleting tags or evidence, or closing product acceptance.

`执行回滚：发版任务=ID 原因=<问题> 证据=<ID或URL>` is an explicit active-rollback authorization for a uniquely resolved release that technically deployed or reached `发布完成` but has not been closed by product acceptance. Re-read and verify the supplied incident evidence, current production version, affected scope, stored stable target, rollback mechanism, artifact, permission, and idempotency before running exactly one rollback. Do not accept it as authority to reopen an `已完成/已关闭` lifecycle, invent an incident, change the rollback plan, or modify unrelated scope.

`重新发布：发版任务=ID 回归证据=<ID或URL>` is the only command that may create a production attempt after a terminal failed attempt or failed product acceptance. Require the existing failure evidence, the unchanged original scope, affected Bugs closed, current regression evidence, and an explicit re-release command. Record available test-deployment, QA, rollback, fix-forward, approval, and window information without requiring a particular custom JSON schema. Create `attemptNo=previous+1`, `attemptType=re_release`, a new `releaseAttemptId`, and `previousAttemptId`; never treat a repeated `执行发布` as repair authorization.

`查询发布：发版任务=ID` is always read-only and uses only one exact release-task ID to consolidate scope, state, execution, callback, failure, and auto-close diagnostics. Do not accept requirement IDs or pipeline execution IDs as query entry points.

`准备发布：迭代=<名称>` authorizes automatic discovery from that exact iteration. An iteration formally contains `【交付】`; every requirement formally `ASSOCIATED` to one of those deliveries is equivalent to an iteration requirement and need not carry a direct sprint field. Resolve end channel from delivery tags (`Web` / `小程序`; `PC` aliases to `Web`; mixed ends block). It selects every non-deferred requirement at `测试完成`, validates scope/relationship/state A/B/C/D rules, then creates or reuses one exact top-level `【发版】` task only when A is non-empty and C/D are empty. **Web** classifies the formal scope as `pc_single` or `shared_service_dual`, derives the changed-code component matrix from the formal delivery chain, and freezes only each changed component's `master` merge evidence and active production-pipeline mapping; components with no code change are recorded as `无需部署`. **小程序** does not require or freeze a cloud production pipeline (`releaseChannel=miniprogram_skip_pipeline`). Automatically synthesize the selected requirements and qualifying same-iteration Bugs into a business update log under [references/release-description.md](references/release-description.md) and write it into the release-task description; source-ID traceability, scope, hashes, idempotency, relations, channel, topology, and component matrix remain in hidden HTML comments. Test deployment, QA evidence, case execution, defect-closure records, release approver, release window, rollback plan, and production-verification plan are retained when readable but never block `准备发布` or `执行发布`; missing fields are recorded as `未配置` or `未自动验证`. The release task formally associates the iteration, every A-class requirement, the one-to-many source `【交付】` tasks derived from that iteration and A scope, plus every same-iteration Bug that is `已完成`/`已关闭` and has no formal association with any delivery task. `需求=<ID,...>` is optional and reserved for an explicit partial release. Repeating the command with the same scope regenerates and replaces only the visible iteration update log and owned managed comments; it does not create a second task or change scope. The command does not authorize production execution or release-state changes.

### Explicit simulated-production exception

Only when the user explicitly authorizes a simulated-production smoke test may the Skill set up a disposable Flow definition through `flow-create-smoke-pipeline`. This is not a normal release command and never changes the real production definition:

- The source must be one existing `test` pipeline in the daily environment; the target name must contain both `smoke` and `prod`, and must not equal any real `prod` pipeline name.
- The copy may reuse exactly one already-accessible Codeup service connection and the source pipeline's existing build-group identifier. It must never create a service connection, runner, host group, container, deployment target, secret, or webhook.
- Remove notification plugins, use only a manual run, record `releaseMode=smoke` and `isRealProduction=false`, and run only in the daily/test environment.
- If Flow does not expose the source build group to YAML creation, stop the copy attempt without retrying through a browser or another channel. An existing test pipeline may then be run once as a clearly labelled simulated-production execution.
- A successful simulation may close only its `【发版】【模拟生产】` evidence task. It never writes `发布完成`, never closes a requirement, and never substitutes product acceptance or real production verification.

## Execute

All Yunxiao Projex, Flow, Codeup, and AppStack discovery, state reads, relations, task writes, pipeline/deployment actions, logs, callbacks, and read-back must use `yunxiao_cli_gateway.py` through the official `aliyun devops` CLI. Never use a browser, screenshot/OCR, semantic DOM, Cookie, connector, or webpage-internal API, including as a fallback after CLI failure.

1. For a direct pipeline command, resolve the supplied name to one existing definition. `准备发布`、`执行发布`、`执行回滚`、`重新发布`和`查询发布`只读取并选择生产流水线：名称/代码源/部署目标必须共同指向`prod/生产`，测试流水线不得进入候选、组件矩阵、描述或回读。只有用户明确输入`执行测试流水线`时，才按名称读取并执行测试流水线。对发布命令，从正式范围导出 changed-code component matrix，按精确 repository、`master` and deploy target resolve production Flow definitions. Before uniqueness checking, exclude disabled/archived definitions and names marked retired by `-old`, `_old`, `-legacy`, `_legacy`, `旧`, `停用`, `废弃`, or `归档`; for example, `oneos-web-prod-old` never competes with `oneos-web-prod`. Require one active match per changed component and deduplicate a genuinely shared pipeline. Treat Flow's generic `envName=日常环境` as a container label, not as a production conflict, when the active definition's name, exact Codeup source/branch, and deployment target all identify production; record both the raw Flow environment and `logicalReleaseEnvironment=prod`. Never create, copy, update, rename, or delete a pipeline.
2. Start the exact matched pipeline immediately, submit only once for the current user message, and return the new execution ID, environment, start time, URL, and initial status.
3. Follow the execution to a terminal state. While it is running, send concise progress updates at intervals no longer than 60 seconds rather than using one long blocking wait.
4. If it fails, identify the first failed stage, job, task, and step; retrieve the failed-step log plus enough adjacent context to diagnose it; redact credentials and return the evidence and diagnosis.
5. If the log is unavailable, expired, truncated, or forbidden, report that exact limitation with the execution URL and do not invent a root cause.
6. If the pipeline requires parameters without defaults, login/OTP, permission elevation, or an internal approval stage, stop at that required boundary and report it; never invent parameters or bypass approval.
7. For `准备发布`, accept `迭代=<迭代名称>` and an exceptional optional `需求=<ID,...>` partial-release selector. Resolve the iteration uniquely, freeze formal `【交付】` entries and their `ASSOCIATED` requirements, resolve end tags (`Web`/`小程序`; `PC` aliases to `Web`; mixed ends block), automatically select non-deferred items at `测试完成` unless an explicit partial scope is supplied, run `skill-run classify_release_scope.py ...` through [references/runtime-launcher.md](references/runtime-launcher.md), and require A non-empty with C/D empty. Do not require a direct requirement-to-iteration relation.
8. **Web**: run `skill-run validate_release_topology.py --input <topology-json>` for the frozen scope, then create/reuse one exact top-level `【发版】` task from the project, iteration, sorted A-class requirements, qualifying Bugs, and scope hash. Write and read back the immutable A/B/C/D scope, end channel, topology, relation lists, available test-record summary and changed-code component matrix. **小程序**: create/reuse the same relation-scoped task and record `miniprogram_skip_pipeline`, without requiring a production pipeline. For both channels, generate the visible business update log and store managed traceability in hidden comments. Existing frozen scope drift blocks rather than being silently expanded.
9. Derive the project, A-class requirement batch, source deliveries, qualifying Bugs, test task state, end channel, component matrix or mini-program skip marker, and release scope directly from the iteration, A/B/C/D classifier and release task. B-class deferred requirements remain recorded but excluded and non-blocking; any C/D item blocks. A Web changed component without `master` merge evidence or a unique production mapping blocks execution but does not authorize guessing or restarting unrelated components. Test deployment, QA evidence, case execution, defect closure, release approver, release window, rollback plan, and production-verification plan are optional records, not release gates. Never substitute the full iteration or manually supplied scope.
10. For `执行发布`, read the real release-task state, end channel and persisted attempt ledger. **小程序**: skip production pipeline and external evidence; write a successful `miniprogram_skip_pipeline` attempt; move release task and requirements to `发布完成`; emit YunxiaoPM acceptance handoff; idempotent if already complete. **Web**: apply the state table in [references/controls.md](references/controls.md), starting or resuming one execution per required changed component only. With a terminal failed attempt, prohibit a new production execution and return the repair/`重新发布` path. Never choose an action from chat history alone.
11. Before any **Web** production execution, require only the explicit command, one exact release task and frozen scope, a complete component matrix in which every changed component has a tested release-candidate branch merged to `master`, one active production pipeline sourcing `master` with matching code source/deployment target, complete runtime parameters, and no duplicate active or successful component execution. Standard iteration release source is `release/<迭代名称>` created from the current `master`; it may contain only approved commits from this frozen scope. A `develop` or other unqualified branch source is a hard stop. Record approval, window, rollback, and production-verification information when available; rely on native pipeline approval stages and never bypass them. Mini-program path skips this gate.
12. Keep five evidence classes separate: test deployment, production pipeline, production verification, release change, and product acceptance.
13. For CLI polling, use live execution read-back and do not require callback evidence. Only callback-driven writes must pass `verify_release_callback.py` signature, timestamp, execution, scope, idempotency, and replay checks.
14. On technical production success, record any readable tag, commit, artifact, health, smoke, business, or observation evidence; mark unavailable items as `未自动验证` without inventing values.
15. When every required component execution has a unique ID, logical environment `prod`, matching frozen scope, and terminal success, write and read back technical production evidence, move the release task and requirements to `发布完成`, recheck erroneous auto-close, and emit the product-acceptance handoff. Optional production checks may add warnings but do not block this transition.
16. On a verified terminal production failure (`失败`、`已取消`、`超时` or an equivalent platform terminal state that cannot continue) or an explicit frozen production-check failure, collect logs/evidence, preserve the execution and validation record, and write the real `发布失败` state.
17. In the same `执行发布` goal, automatically roll back only when a stored rollback mechanism, unique stable target, usable artifact, permission, and idempotency record are all available. Otherwise keep the real failure, report `自动回滚=false`, and return the manual recovery boundary without blocking the original production attempt in advance.
18. Do not classify an approval wait, missing parameter, login/OTP boundary, temporary permission block, running job, observability outage, missing evidence, or unknown/stale status as failure. Stop and report the boundary without rolling back unless the frozen plan explicitly defines that observed condition as a rollback-triggering failure.
19. On `执行回滚`, require the exact release task plus a concrete reason and evidence, reject closed product lifecycles, and apply the same single-rollback gates before changing release state or executing recovery.
20. On rollback success, preserve production, verification, incident, and rollback evidence; record before/after versions; keep the release task in the real failed state; and hand defect repair/re-release disposition to product and development ownership.
21. On rollback failure, preserve logs and partial state and prohibit automatic retry until an authorized recovery plan exists.
22. If the task is already release-complete and there is no explicit `执行回滚`, do not rerun production; only reconcile status and evidence, then idempotently re-emit any missing product handoff.
23. After a stable rollback or evidenced product-acceptance failure, emit `/skill YunxiaoQA` plus `接收发布回流：发版任务=<ID>；触发=<发布失败|产品验收失败>；证据=<ID或URL>`.
24. On `重新发布`, verify the failure evidence, unchanged scope, affected Bugs closed, current regression evidence, and explicit authorization; increment the attempt number, create a new release-attempt ID/idempotency key linked to the previous terminal attempt, start one new execution per required component, preserve every previous attempt, record available production checks, and emit a fresh product-acceptance handoff after technical success.

## Non-negotiable gates

- Test deployment is never production release evidence.
- 发布准备、执行、回滚、重发和查询均不得读取或列出测试流水线；测试流水线只属于显式`执行测试流水线`命令。
- Direct pipeline execution does not itself prove deployment success or authorize any work-item state change.
- Test and production pipelines are pre-created project configuration. Missing or ambiguous active repository-to-pipeline mapping blocks execution and must never trigger pipeline creation, copying, updating, renaming, or service-connection creation, except for the explicit simulated-production exception above. Retired/disabled definitions and names marked `-old`, `_old`, `-legacy`, `_legacy`, `旧`, `停用`, `废弃`, or `归档` are ignored before deciding ambiguity.
- Reject a direct execution when the active pipeline name has zero or multiple matches, the logical release environment conflicts with the command, or required runtime parameters are missing. A raw Flow `envName=日常环境` does not conflict by itself when the active pipeline name, Codeup source/branch, and deployment target consistently identify production.
- Redact passwords, tokens, cookies, access keys, private keys, authorization headers, and secret variable values before returning or saving logs.
- Distinguish an explicit log-confirmed cause from a likely inference and from a visible failure symptom.
- Pipeline success proves technical release only after the execution environment and frozen scope also read back correctly; it never proves product or business acceptance.
- `准备发布` defaults to automatic iteration scope: every non-deferred requirement at `测试完成` is selected and fully checked. A selected incomplete/evidence-defective item (C) or scope anomaly (D) blocks; formally deferred or not-yet-test-complete iteration items are B, recorded but not released. `需求=` is only an explicit partial-release override.
- QA evidence, test-deployment manifests, case execution, defect-closure manifests, approver fields, release windows, rollback plans, callback signatures, and production-verification plans are optional evidence for normal initial release. Missing or differently formatted optional evidence must never classify an otherwise test-complete item as C/D.
- `准备发布` requires one unique iteration and creates/reuses one top-level release task with a frozen scope, source delivery list, qualified Bug list, and changed-code component pipeline matrix. Missing, cross-project, title-only, ambiguous, delivery-child, or scope-drifting relations block writes. Missing optional release-control fields are recorded without blocking `准备发布` or `执行发布`.
- `查询发布` requires exactly one release-task ID. Requirement IDs and pipeline execution IDs may appear only in returned evidence, never as alternative query parameters.
- Never print or store Webhook secrets, cookies, tokens, or private keys.
- A repeated execution ID must not advance the requirement twice.
- An active or successful release execution must never be duplicated by `执行发布`.
- Every first and subsequent production attempt must have a persisted attempt number, type, ID, authorized command, component execution list, status, and idempotency key. A terminal failed attempt can never be replaced, cleared, or reused by `执行发布`.
- `执行发布` must not guess a rollback target, reuse a stale artifact, or start a second rollback while one is active or already successful.
- Automatic rollback requires a verified terminal production failure or an explicit failed production check plus a stored, uniquely resolvable rollback plan and stable version anchor. When these are absent, return `自动回滚=false` and manual recovery guidance; do not block the release attempt before production submission.
- Active rollback requires an explicit `执行回滚` command, a release not yet closed by product acceptance, verified incident evidence, and the same rollback target/artifact/permission/idempotency gates.
- `重新发布` requires current regression evidence and closed affected Bugs, but does not require custom QA or test-deployment JSON schemas.
- Never mark `发布完成` until every required component execution succeeds and its logical prod environment and frozen scope read back correctly. Record unavailable optional production checks as `未自动验证`.
- Release success must stop at `发布完成`; product or business acceptance owns final closure.
- Do not delete pipelines, rules, release tasks, MR records, tags, artifacts, or execution evidence without separate authorization.
- Missing CLI/plugin/PAT/organization-or-endpoint capability is a zero-write blocker and never authorizes another platform execution channel.

## Return

```text
项目/迭代：
发版任务/需求范围：
源交付/无关联单据已完成Bug正式关系：
触发口令：
流水线/环境/执行ID/执行URL：
最终状态/失败阶段：
失败日志/诊断结论：
生产验证计划/结果：
问题现象/影响范围/问题证据：
审批和回滚/回滚执行ID：
回滚前后版本/恢复结果：
修复回流批次/逐Bug复测/回归证据：
发布尝试序号/类型/ID/前次尝试ID：
状态变化：
回调与幂等证据：
生产版本锚点：
阻塞：
剩余风险/责任人：
下一责任角色：
下一条口令：
```
