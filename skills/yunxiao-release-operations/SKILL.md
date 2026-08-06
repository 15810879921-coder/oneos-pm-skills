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

Operate deployment and release evidence while keeping test, production verification, rollback, and product acceptance separate. Suite version: `9.3.1`.

## Load the required references

Read each selected file completely before acting:

- Release task, pipeline, stage-task and OneOS controls: [references/controls.md](references/controls.md).
- Short Chinese commands and expected actions: [references/commands.md](references/commands.md).
- Release-batch creation and A/B/C/D scope rules: [references/release-batch.md](references/release-batch.md).
- Runtime write order and callback verification: [references/execution-runtime.md](references/execution-runtime.md).
- Official CLI environment, guarded transactions, pipeline monitoring, idempotency, and performance: [references/yunxiao-cli-runtime.md](references/yunxiao-cli-runtime.md).
- Cross-platform bundled-script launcher: [references/runtime-launcher.md](references/runtime-launcher.md).
- Callback, evidence, authorization, live-change safety, and cross-skill handoff: [references/safety-handoff.md](references/safety-handoff.md).

## Own only the operations boundary

Own these outcomes:

1. Directly start one uniquely resolved test or production pipeline when the matching explicit execution command is given, monitor it to a terminal state, and collect failed-step logs when it fails.
2. Record test deployment evidence without promoting release state.
3. From one exact iteration, automatically derive all test-complete release candidates, classify A/B/C/D scope, and freeze the derived release batch directly inside one `【发版】` task. Accept explicit requirement IDs only for an exceptional partial release.
4. Create or reuse that exact release task, formally relate it to the iteration and A-class requirements, and freeze production pipelines, approvals, window, rollback, and production verification.
5. Verify test completion, approval, scope, production pipeline, and rollback plan.
6. Start the exact authorized production execution.
7. After technical production success, run the frozen production-verification plan and keep the release in progress until every required health, smoke, business, and observation-window check passes.
8. Verify signed, timestamped, idempotent pipeline and production-verification evidence.
9. Move the release task and requirements to `发布完成` only after technical production and production verification both pass; otherwise write the real `发布失败`.
10. When `执行发布` reaches either a verified terminal production failure or an explicit production-verification failure, preserve evidence and automatically execute the exact stored rollback once.
11. On `执行回滚`, handle an evidenced post-release defect or business-verification failure before product acceptance closes the lifecycle, using the same stored rollback and idempotency gates.
12. Record and return the problem symptom, failure point, impact, diagnosis confidence, original and rollback executions, recovery result, residual risk, owner, and next action.
13. Hand only a verified `发布完成` to `YunxiaoPM` for acceptance.
14. After a release or product-acceptance failure, emit the formal QA repair intake; accept `重新发布` only after a verified repair batch, test deployment, per-Bug retest, regression evidence, rollback/fix-forward disposition, and renewed approval.

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

`执行发布：发版任务=ID` is the initial-attempt command and same-attempt continuation. After all gates pass, create or reuse exactly one persisted `releaseAttemptId` with `attemptNo=1` and `attemptType=initial`; start at most one production execution for that attempt, or resume its existing execution, verification, or automatic rollback. A repeated `执行发布` may continue the same nonterminal attempt after an interruption, but it never creates a second production attempt. Once that attempt reaches verified success or failure, it is terminal: success is returned idempotently, while failure may only finish/return the stored rollback and repair handoff. Any new production execution after a failed release requires `重新发布`. It does not authorize changing pipeline definitions or validation thresholds, bypassing an approval stage, guessing a rollback target, deleting tags or evidence, or closing product acceptance.

`执行回滚：发版任务=ID 原因=<问题> 证据=<ID或URL>` is an explicit active-rollback authorization for a uniquely resolved release that technically deployed or reached `发布完成` but has not been closed by product acceptance. Re-read and verify the supplied incident evidence, current production version, affected scope, stored stable target, rollback mechanism, artifact, permission, and idempotency before running exactly one rollback. Do not accept it as authority to reopen an `已完成/已关闭` lifecycle, invent an incident, change the rollback plan, or modify unrelated scope.

`重新发布：发版任务=ID 回归证据=<ID或URL>` is the only command that may create a production attempt after a terminal failed attempt or failed product acceptance. Require the existing incident or product-acceptance-failure evidence, exact original iteration/scope, a successful repair test deployment, `oneos.release-repair-qa/v1`, every affected Bug closed with its own `oneos.bug-retest/v1`, successful rollback or an explicitly approved fix-forward disposition, and renewed release approval. Create `attemptNo=previous+1`, `attemptType=re_release`, a new `releaseAttemptId`, and `previousAttemptId`; never treat a repeated `执行发布` as repair authorization.

`查询发布：发版任务=ID` is always read-only and uses only one exact release-task ID to consolidate scope, state, execution, callback, failure, and auto-close diagnostics. Do not accept requirement IDs or pipeline execution IDs as query entry points.

`准备发布：迭代=<名称>` authorizes automatic discovery from that exact iteration. An iteration formally contains `【交付】`; every requirement formally `ASSOCIATED` to one of those deliveries is equivalent to an iteration requirement and need not carry a direct sprint field. It selects every non-deferred requirement at `测试完成`, validates scope/relationship/state A/B/C/D rules, then creates or reuses one exact top-level `【发版】` task only when A is non-empty and C/D are empty. Test deployment, QA evidence, case execution, and defect-closure records are retained when readable but do not block `准备发布`. The release task formally associates the iteration, every A-class requirement, the one-to-many source `【交付】` tasks derived from that iteration and A scope, plus every same-iteration Bug that is `已完成`/`已关闭` and has no formal association with any delivery task. `需求=<ID,...>` is optional and reserved for an explicit partial release. The command does not authorize production execution or release-state changes.

### Explicit simulated-production exception

Only when the user explicitly authorizes a simulated-production smoke test may the Skill set up a disposable Flow definition through `flow-create-smoke-pipeline`. This is not a normal release command and never changes the real production definition:

- The source must be one existing `test` pipeline in the daily environment; the target name must contain both `smoke` and `prod`, and must not equal any real `prod` pipeline name.
- The copy may reuse exactly one already-accessible Codeup service connection and the source pipeline's existing build-group identifier. It must never create a service connection, runner, host group, container, deployment target, secret, or webhook.
- Remove notification plugins, use only a manual run, record `releaseMode=smoke` and `isRealProduction=false`, and run only in the daily/test environment.
- If Flow does not expose the source build group to YAML creation, stop the copy attempt without retrying through a browser or another channel. An existing test pipeline may then be run once as a clearly labelled simulated-production execution.
- A successful simulation may close only its `【发版】【模拟生产】` evidence task. It never writes `发布完成`, never closes a requirement, and never substitutes product acceptance or real production verification.

## Execute

All Yunxiao Projex, Flow, Codeup, and AppStack discovery, state reads, relations, task writes, pipeline/deployment actions, logs, callbacks, and read-back must use `yunxiao_cli_gateway.py` through the official `aliyun devops` CLI. Never use a browser, screenshot/OCR, semantic DOM, Cookie, connector, or webpage-internal API, including as a fallback after CLI failure.

1. For a direct pipeline command, resolve the supplied name to one existing definition. For lifecycle-driven test or production execution, derive affected Codeup repositories from formal scope and resolve existing Flow definitions by exact code source and target branch: names must carry `test/测试` for test or `prod/生产` for production. Require one match per repository, deduplicate a shared pipeline, and verify the environment. Never create, copy, update, rename, or delete a pipeline.
2. Start the exact matched pipeline immediately, submit only once for the current user message, and return the new execution ID, environment, start time, URL, and initial status.
3. Follow the execution to a terminal state. While it is running, send concise progress updates at intervals no longer than 60 seconds rather than using one long blocking wait.
4. If it fails, identify the first failed stage, job, task, and step; retrieve the failed-step log plus enough adjacent context to diagnose it; redact credentials and return the evidence and diagnosis.
5. If the log is unavailable, expired, truncated, or forbidden, report that exact limitation with the execution URL and do not invent a root cause.
6. If the pipeline requires parameters without defaults, login/OTP, permission elevation, or an internal approval stage, stop at that required boundary and report it; never invent parameters or bypass approval.
7. For `准备发布`, accept `迭代=<迭代名称>` and an exceptional optional `需求=<ID,...>` partial-release selector. Resolve the iteration uniquely, freeze formal `【交付】` entries and their `ASSOCIATED` requirements, automatically select non-deferred items at `测试完成` unless an explicit partial scope is supplied, run `skill-run classify_release_scope.py ...` through [references/runtime-launcher.md](references/runtime-launcher.md), and require A non-empty with C/D empty. Do not require a direct requirement-to-iteration relation.
8. Create/reuse one exact top-level `【发版】` task directly from the project, iteration, sorted A-class requirements, same-iteration completed Bugs with no formal work-item relation of any kind, and scope hash. Formally relate it to the iteration, A-class requirements, their source delivery/test tasks and qualifying Bugs; write and read back the immutable A/B/C/D scope, relation lists, available test-record summary, production pipeline, owner, approver, window, rollback plan, and production-verification plan. Existing frozen scope drift blocks rather than being silently expanded.
9. Derive the project, A-class requirement batch, source deliveries, qualifying Bugs, test task state, production pipeline, owner, approver, window, rollback plan, and release scope directly from the iteration, A/B/C/D classifier and release task. B-class deferred requirements remain recorded but excluded and non-blocking; any C/D item blocks. Test deployment, QA evidence, case execution, and defect closure are not preparation gates. Never substitute the full iteration or manually supplied scope.
10. For `执行发布`, read the real release-task state and persisted attempt ledger, then apply the state table in [references/controls.md](references/controls.md). With no prior attempt and a ready state, create attempt 1 immediately before the production submission; with a nonterminal attempt, resume it without creating another; with a terminal failed attempt, prohibit a new production execution and return the repair/`重新发布` path. Never choose an action from chat history alone.
11. Before any production execution, require the stored approval, release window, rollback plan, production target, and frozen production-verification plan with explicit checks, thresholds, observation window, evidence sources, and rollback-trigger mapping.
12. Keep five evidence classes separate: test deployment, production pipeline, production verification, release change, and product acceptance.
13. Validate callback signature, timestamp, execution ID, environment, scope, current state, idempotency, and replay protection with `skill-run verify_release_callback.py ...` before any callback-driven state write.
14. On technical production success, preserve an immutable production tag or equivalent released-commit/artifact anchor, keep the release in progress, and execute every required item in the frozen production-verification plan.
15. Only when all required production checks pass for the full observation window, write and read back the structured production and validation evidence defined in `references/controls.md`, move the release task and requirements to release completion, recheck erroneous auto-close, and emit the product-acceptance handoff.
16. On a verified terminal production failure (`失败`、`已取消`、`超时` or an equivalent platform terminal state that cannot continue) or an explicit frozen production-check failure, collect logs/evidence, preserve the execution and validation record, and write the real `发布失败` state.
17. In the same `执行发布` goal, verify the failed/current production version, stored rollback target, rollback mechanism, artifact availability, permissions, and idempotency; then execute or continue exactly one rollback and monitor it to a terminal state.
18. Do not classify an approval wait, missing parameter, login/OTP boundary, temporary permission block, running job, observability outage, missing evidence, or unknown/stale status as failure. Stop and report the boundary without rolling back unless the frozen plan explicitly defines that observed condition as a rollback-triggering failure.
19. On `执行回滚`, require the exact release task plus a concrete reason and evidence, reject closed product lifecycles, and apply the same single-rollback gates before changing release state or executing recovery.
20. On rollback success, preserve production, verification, incident, and rollback evidence; record before/after versions; keep the release task in the real failed state; and hand defect repair/re-release disposition to product and development ownership.
21. On rollback failure, preserve logs and partial state and prohibit automatic retry until an authorized recovery plan exists.
22. If the task is already release-complete and there is no explicit `执行回滚`, do not rerun production; only reconcile status and evidence, then idempotently re-emit any missing product handoff.
23. After a stable rollback or evidenced product-acceptance failure, emit `/skill YunxiaoQA` plus `接收发布回流：发版任务=<ID>；触发=<发布失败|产品验收失败>；证据=<ID或URL>`.
24. On `重新发布`, verify the complete repair chain, increment the attempt number, create a new release-attempt ID/idempotency key linked to the previous terminal attempt, start one new production execution, preserve every previous attempt, rerun the frozen production-verification plan and then emit a fresh product-acceptance handoff.

## Non-negotiable gates

- Test deployment is never production release evidence.
- Direct pipeline execution does not itself prove deployment success or authorize any work-item state change.
- Test and production pipelines are pre-created project configuration. Missing or ambiguous repository-to-pipeline mapping blocks execution and must never trigger pipeline creation, copying, updating, renaming, or service-connection creation, except for the explicit simulated-production exception above.
- Reject a direct execution when the pipeline name has zero or multiple matches, the resolved environment conflicts with the command, or required runtime parameters are missing.
- Redact passwords, tokens, cookies, access keys, private keys, authorization headers, and secret variable values before returning or saving logs.
- Distinguish an explicit log-confirmed cause from a likely inference and from a visible failure symptom.
- Pipeline success alone does not prove the intended requirement batch was released or that production is healthy.
- `准备发布` defaults to automatic iteration scope: every non-deferred requirement at `测试完成` is selected and fully checked. A selected incomplete/evidence-defective item (C) or scope anomaly (D) blocks; formally deferred or not-yet-test-complete iteration items are B, recorded but not released. `需求=` is only an explicit partial-release override.
- Every selected requirement must carry a QA evidence iteration and successful test-deployment iteration exactly equal to the command's resolved iteration; an absent or mismatched upstream iteration is C/D and cannot be supplied manually downstream.
- `准备发布` requires one unique iteration and creates/reuses one release task with a frozen scope. Missing, cross-project, title-only, ambiguous, or scope-drifting relations block all writes.
- `查询发布` requires exactly one release-task ID. Requirement IDs and pipeline execution IDs may appear only in returned evidence, never as alternative query parameters.
- Never print or store Webhook secrets, cookies, tokens, or private keys.
- A repeated execution ID must not advance the requirement twice.
- An active or successful release execution must never be duplicated by `执行发布`.
- Every first and subsequent production attempt must have a persisted attempt number, type, ID, authorized command, production execution ID, status, and idempotency key. A terminal failed attempt can never be replaced, cleared, or reused by `执行发布`.
- `执行发布` must not guess a rollback target, reuse a stale artifact, or start a second rollback while one is active or already successful.
- Automatic rollback requires either a verified terminal production failure or an explicit failure from a frozen production-verification check, plus a stored, uniquely resolvable rollback plan and stable version anchor. A blocked or indeterminate execution or observation is not sufficient.
- Active rollback requires an explicit `执行回滚` command, a release not yet closed by product acceptance, verified incident evidence, and the same rollback target/artifact/permission/idempotency gates.
- `重新发布` requires a new test deployment and QA repair evidence; old QA completion, old production success, rollback success, or a verbal “已修复” cannot substitute.
- Never mark `发布完成` until technical production execution and every required production-verification check have passed.
- Release success must stop at `发布完成`; product or business acceptance owns final closure.
- Do not delete pipelines, rules, release tasks, MR records, tags, artifacts, or execution evidence without separate authorization.
- Missing CLI/plugin/PAT/organization-or-endpoint capability is a zero-write blocker and never authorizes another platform execution channel.

## Return

```text
项目/迭代：
发版任务/需求范围：
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
