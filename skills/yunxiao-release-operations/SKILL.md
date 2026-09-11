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

## 每日首次自动更新（强制，先于其他动作）

每个本地自然日首次触发本 Skill 时，先执行：

```text
node <本 Skill 目录>/scripts/ensure-daily-skill-update.mjs --current-skill yunxiao-release-operations
```

- `updated`：五个云效生命周期 Skill 已统一更新；必须重新完整读取本 `SKILL.md` 及本次所需引用后再继续。
- `skipped-today`：当天已经成功更新，直接继续。
- `in-progress`：另一个相关 Skill 正在执行同一更新，直接继续，不并发重复更新。
- `failed` / `unavailable` / `cooldown`：只给一条简短提示，继续当前任务；更新失败不得阻断云效工作。
- 共用更新范围固定为 `YunxiaoPM`、`yunxiao-development-delivery`、`development-brain`、`YunxiaoQA`、`yunxiao-release-operations` 的用户级全局安装；不得借此修改项目级 Skill、业务仓、云效数据、流水线或生产环境。不得手工伪造或提前写入每日成功状态。

Operate deployment and release evidence while keeping test, production verification, rollback, and product acceptance separate. Suite version: `10.1.0`.

## Load the required references

Read each selected file completely before acting:

- Release task, pipeline, stage-task and OneOS controls: [references/controls.md](references/controls.md).
- Short Chinese commands and expected actions: [references/commands.md](references/commands.md).
- Release-batch creation and A/B/C/D scope rules: [references/release-batch.md](references/release-batch.md).
- Existing delivery-comment validation, official Codeup backfill, and frozen `【发布代码清单】`: [references/release-code-ledger.md](references/release-code-ledger.md).
- Build dependency groups with `scripts/resolve_release_dependency_groups.py`, freeze exact repository actions with `scripts/build_release_merge_plan.py`, and persist partial target-merge/deployment continuation with `scripts/execute_release_merge_plan.py`.
- For both preparation and execution, follow [references/change-coverage.md](references/change-coverage.md): collect pinned official histories with `validate_release_change_coverage.py collect`, distinguish branch owners from delivery scope, and verify candidate and resulting target trees with `verify-tree`. Boolean declarations and MR endpoint SHAs alone are not completeness evidence.
- Business-readable release-task descriptions and append-only managed comment ledgers: [references/release-description.md](references/release-description.md).
- Runtime write order and callback verification: [references/execution-runtime.md](references/execution-runtime.md).
- Official CLI environment, guarded transactions, pipeline monitoring, idempotency, and performance: [references/yunxiao-cli-runtime.md](references/yunxiao-cli-runtime.md).
- Cross-platform bundled-script launcher: [references/runtime-launcher.md](references/runtime-launcher.md).
- Callback, evidence, authorization, live-change safety, and cross-skill handoff: [references/safety-handoff.md](references/safety-handoff.md).

## Own only the operations boundary

Own these outcomes:

1. Directly start one uniquely resolved test or production pipeline when the matching explicit execution command is given, monitor it to a terminal state, and collect failed-step logs when it fails.
2. Record test deployment evidence without promoting release state.
3. From one exact iteration, automatically derive all test-complete release candidates, classify A/B/C/D scope, and freeze the derived release batch directly inside one `【发版】` task. Accept an exact requirement or source-delivery ID plus an explicit exceptional-release reason for hotfix, gray, or partial release without requiring iteration membership.
4. Create or reuse that exact top-level release task. Its direct formal relations are limited to source `【交付】` tasks in the frozen scope and qualifying completed Bugs with no formal work-item relation. Never write or change the task's sprint/iteration field; if an existing release task already has one, record it as historical metadata and continue when the frozen project/scope is still consistent. Iteration or exceptional-scope identity, A-class requirements, test/development tasks and all gate evidence are validated and retained only in append-only comments. Read `oneos.delivery-ledger/v1` first and old `【代码交付记录】` second; actively backfill missing branch/MR/commit anchors through formal relations and official Codeup CLI. Adopt uniquely matched TEMPDEV, aggregate independent Bug branches under a later development task, build verified dependency groups, then freeze the component matrix and per-repository `mergePlan` in the release task. Before freezing, read every source branch's complete commit history relative to the frozen production target baseline and classify every commit with evidence; silently omitted intermediate commits make the plan `BLOCKED`. The description remains business-readable and contains no machine JSON.
5. Verify test completion and scope for every channel. For **Web**, also verify each changed component's merge evidence and production-pipeline mapping; for **小程序**, do not require cloud-visible code evidence, production-pipeline mapping, execution, production verification, or external evidence. Preserve only the skip attempt and state-transition receipt.
6. Execute the frozen `mergePlan` with one `releaseMergeAttemptId`. Preflight every repository before the first merge; if any later merge fails, enter `PARTIAL_TARGET_MERGE`, mark already merged target commits as occupied-but-not-deployed, and never start production until all targets are ready or the successful merges are reverted through new MRs.
7. Start only the exact authorized production execution for the resolved Web release task. After every target merge succeeds, state is `TARGETS_READY`; starting the pipeline changes it to `MERGED_NOT_DEPLOYED` until immutable deployment evidence proves success.
8. After technical production success, run any available production checks and record unavailable checks as `未自动验证`; missing optional checks do not block technical release completion.
9. Verify the live CLI execution ID, logical production environment, frozen scope, terminal status, and idempotency. Validate callback signatures only when a callback is actually used.
10. For **Web**, move the release task and requirements to `发布完成` only after every required component execution succeeds and each environment and scope read back correctly. For **小程序**, move them after channel/scope/current-state/idempotency checks and a successful `miniprogram_skip_pipeline` attempt; keep business acceptance separate.
11. When `执行发布` reaches either a verified terminal production failure or an explicit production-verification failure, preserve evidence and automatically execute the exact stored rollback once.
12. On `执行回滚`, handle an evidenced post-release defect or business-verification failure before product acceptance closes the lifecycle, using the same stored rollback and idempotency gates.
13. Record and return the problem symptom, failure point, impact, diagnosis confidence, original and rollback executions, recovery result, residual risk, owner, and next action.
14. Hand only a verified `发布完成` to `YunxiaoPM` for acceptance.
15. After a release or product-acceptance failure, emit the formal QA repair intake; accept `重新发布` after the affected scope is repaired, affected Bugs are closed, current regression evidence is supplied, and the user explicitly authorizes re-release.

Do not execute test cases, edit application code, or close a requirement after release success.

## Cross-Skill logical handoff

- Accept and emit only formal Skill names, exact requirement/test/release/execution task IDs, live states, formal relations, frozen batch scope, and necessary pipeline, deployment, verification, rollback, evidence, or idempotency identifiers.
- Never discover, read, copy, or require another Skill's installation directory. Resolve missing facts from the explicit handoff IDs and live Yunxiao services; keep all bundled rules local to this Skill.
- Test intake uses `$YunxiaoQA`, development return uses `$yunxiao-development-delivery`, and production-acceptance handoff uses `$YunxiaoPM`. Never emit a legacy alias or filesystem path as a command.

## Classify authority

- `audit`: inspect pipelines, executions, callbacks, rules, and evidence only.
- `plan`: prepare release scope or rollback plan only.
- `apply`: create/update exact release tasks and authorized states.
- `execute`: run the exact named test or production pipeline, run the exact release production execution and frozen production-verification plan, or execute the exact stored rollback.
- `document`: produce release notes or evidence reports.

`执行测试流水线：流水线=名称` and `执行生产流水线：流水线=名称` each authorize one immediate execution of the uniquely resolved existing pipeline. Do not ask for a second confirmation. A repeated command in a new user message is a new execution authorization. The command does not authorize changing the pipeline definition, bypassing a pipeline approval stage, or writing release status.

Every command that runs or monitors a pipeline must automatically collect and output the first failed stage, job, task, step, redacted log evidence, diagnosis confidence, impact, and next action when it ends unsuccessfully. Do not require or generate a separate failure-analysis command.

`执行发布：发版任务=ID` partitions each source delivery by its exact end tag (`Web` / `小程序`; `PC` aliases to `Web`). A batch containing both channels is valid when every source delivery is uniquely tagged: **Web** follows the complete component matrix, while **小程序** records a `miniprogram_skip_pipeline` component receipt and never queries or runs a cloud pipeline. Only an ambiguous or unsupported individual source-delivery tag blocks. Create or reuse one persisted `releaseAttemptId` with `attemptNo=1` and `attemptType=initial`; start or resume every distinct Web component pipeline concurrently and bind every small-program component to its skip receipt. When the user explicitly states `流水线发布已人工操作`, do not submit any pipeline: re-read every frozen component's existing execution, source commit, logical prod environment and terminal status, bind only matching unique successes to the same attempt, then perform the normal evidence/state-transition tail. A repeated `执行发布` may continue only the same nonterminal attempt and its missing/running/reconciled component executions, never create a second execution for any component. Once every component reaches verified success or one component reaches terminal failure, the attempt is terminal. Any new production execution after a failed release requires `重新发布`. It does not authorize changing pipeline definitions, bypassing an approval stage, guessing a rollback target, deleting tags or evidence, or closing product acceptance.

`执行回滚：发版任务=ID 原因=<问题> 证据=<ID或URL>` is an explicit active-rollback authorization for a uniquely resolved release that technically deployed or reached `发布完成` but has not been closed by product acceptance. Re-read and verify the supplied incident evidence, current production version, affected scope, stored stable target, rollback mechanism, artifact, permission, and idempotency before running exactly one rollback. Do not accept it as authority to reopen an `已完成/已关闭` lifecycle, invent an incident, change the rollback plan, or modify unrelated scope.

`重新发布：发版任务=ID 回归证据=<ID或URL>` is the only command that may create a production attempt after a terminal failed attempt or failed product acceptance. Require the existing failure evidence, the unchanged original scope, affected Bugs closed, current regression evidence, and an explicit re-release command. Record available test-deployment, QA, rollback, fix-forward, approval, and window information without requiring a particular custom JSON schema. Create `attemptNo=previous+1`, `attemptType=re_release`, a new `releaseAttemptId`, and `previousAttemptId`; never treat a repeated `执行发布` as repair authorization.

`查询发布：发版任务=ID` is always read-only and uses only one exact release-task ID to consolidate scope, state, execution, callback, failure, and auto-close diagnostics. Do not accept requirement IDs or pipeline execution IDs as query entry points.

`准备发布：迭代=<名称>` authorizes automatic discovery from that exact iteration. An iteration formally contains `【交付】`; every requirement formally `ASSOCIATED` to one of those deliveries is equivalent to an iteration requirement and need not carry a direct sprint field. `准备发布：需求=<ID,...> 原因=<热修复|灰度|局部发布说明>` or `准备发布：交付=<ID,...> 原因=<...>` is the exceptional entry and freezes scope from those exact official relations without requiring an iteration. Partition the batch by delivery tag (`Web` / `小程序`; `PC` aliases to `Web`): a Web+small-program batch is valid; only an unresolvable tag on an individual delivery blocks that component. It selects every non-deferred requirement at `测试完成` and validates A/B/C/D plus `testMode`: every non-cancelled development task requires exactly one mapped test task in `已完成`; `formal-plan`, `mandatory-test-task`, and legacy `qa-requested-exception` may qualify, while `lightweight-verification` is rejected. When project, exact source IDs and relation direction are unique, `准备发布` may create or update one draft release task and record C/D gaps; only A-nonempty/C-D-empty is marked `准备完成` and eligible for `执行发布`. Identity ambiguity, cross-project scope or conflicting source ownership remains zero-write. **Web** validates/backfills `【代码交付记录】` against Codeup and freezes a complete repository-to-component-to-production-pipeline matrix for a release-ready batch; unresolved code anchors or an unmapped changed repository block the affected Web component and execution. **小程序** records a per-delivery `miniprogram_skip_pipeline` release channel and does not require or query cloud production pipelines, Codeup code anchors, pipeline executions, production verification, monitoring, or external release evidence. Automatically synthesize selected requirements and qualifying Bugs into a business update log under [references/release-description.md](references/release-description.md); the description remains business-only, while source-ID traceability, scope, hashes, readiness gaps, idempotency, validation evidence and per-component channel are stored in the append-only `【发布受管数据】` comment ledger. `准备发布` never reads or starts a test pipeline. Test deployment and auxiliary QA records are retained when readable but do not replace the applicable testMode gate. Repeating the same scope updates only the visible log and appends a new managed record when the managed payload changes; it does not create a second task, change scope, execute production or change release state.

### Explicit simulated-production exception

Only when the user explicitly authorizes a simulated-production smoke test may the Skill set up a disposable Flow definition through `flow-create-smoke-pipeline`. This is not a normal release command and never changes the real production definition:

- The source must be one existing `test` pipeline in the daily environment; the target name must contain both `smoke` and `prod`, and must not equal any real `prod` pipeline name.
- The copy may reuse exactly one already-accessible Codeup service connection and the source pipeline's existing build-group identifier. It must never create a service connection, runner, host group, container, deployment target, secret, or webhook.
- Remove notification plugins, use only a manual run, record `releaseMode=smoke` and `isRealProduction=false`, and run only in the daily/test environment.
- If Flow does not expose the source build group to YAML creation, stop the copy attempt without retrying through a browser or another channel. An existing test pipeline may then be run once as a clearly labelled simulated-production execution.
- A successful simulation may close only its `【发版】【模拟生产】` evidence task. It never writes `发布完成`, never closes a requirement, and never substitutes product acceptance or real production verification.

## Execute

All Yunxiao Projex, Flow, Codeup, and AppStack discovery, state reads, relations, task writes, pipeline/deployment actions, logs, callbacks, and read-back must use `yunxiao_cli_gateway.py` through the official `aliyun devops` CLI. Never use a browser, screenshot/OCR, semantic DOM, Cookie, connector, or webpage-internal API, including as a fallback after CLI failure.

1. For a direct pipeline command, use the supplied name to narrow existing definitions, then verify the exact Codeup source, branch, deployment target and logical environment before execution; the name itself is not environment proof. Before any release matrix selection, enumerate every page of `flow-list-pipelines` until its terminal page; never treat page 1 as the full pipeline inventory. `准备发布` never reads a test pipeline. `执行发布`、`执行回滚`、`重新发布`和`查询发布` only read production candidates whose code source, verified target branch, deployment target and logical environment consistently identify production. Only explicit `执行测试流水线` may read and run a test pipeline. Exclude disabled/archived and retired definitions before uniqueness checks. Treat Flow's generic `envName=日常环境` as a container label, not as production truth; record both the raw environment and derived logical environment. Never create, copy, update, rename, or delete a pipeline.
2. Start the exact matched pipeline immediately, submit only once for the current user message, and return the new execution ID, environment, start time, URL, and initial status.
3. Follow the execution to a terminal state. While it is running, send concise progress updates at intervals no longer than 60 seconds rather than using one long blocking wait.
4. If it fails, identify the first failed stage, job, task, and step; retrieve the failed-step log plus enough adjacent context to diagnose it; redact credentials and return the evidence and diagnosis.
5. If the log is unavailable, expired, truncated, or forbidden, report that exact limitation with the execution URL and do not invent a root cause.
6. If the pipeline requires parameters without defaults, login/OTP, permission elevation, or an internal approval stage, stop at that required boundary and report it; never invent parameters or bypass approval.
7. For `准备发布`, accept either standard `迭代=<精确名称>` or exceptional `需求=<ID,...>|交付=<ID,...> 原因=<说明>`. Resolve the selected source uniquely, freeze formal delivery-to-requirement relations, partition each delivery by `Web`/`小程序`, and run `skill-run classify_release_scope.py ...`. A non-empty/C-D-empty means release ready. With unique project and source identity, persist a draft and its gaps even when C/D exist; do not mark it ready or allow `执行发布`. Identity ambiguity, cross-project scope or conflicting source ownership is zero-write. Do not require a direct requirement-to-iteration relation, and never read or run a test pipeline here.
8. Create/reuse one exact top-level `【发版】` task from the project, standard iteration or exceptional source, sorted A-class requirements, qualifying Bugs and scope hash. Directly relate only frozen source deliveries and qualifying Bugs; write and read back immutable A/B/C/D scope, source/requirement/test validation evidence, per-delivery channel and relation lists. **Web** reads the append-only delivery ledger, validates/backfills old `【代码交付记录】` through Codeup commit-history and patch-tree discovery, resolves uniquely adopted TEMPDEV and later task-to-Bug aggregation, then writes/reads back `【发布代码清单】`. Build verified dependency groups with `resolve_release_dependency_groups.py`; freeze every repository action, exact commit set, target branch, component and pipeline in a versioned `mergePlan` with `build_release_merge_plan.py`. For every non-contained source, persist the complete unique-to-target commit history in oldest-to-newest order, a complete-history evidence ID, and an evidenced include/exclude decision for every commit. The exact commit set must equal all included history entries; a pure source must include every history entry. Every anchor must prove the repository's production target branch; every matrix row must prove the pipeline's repository, target branch, deployment target and logical prod environment exactly match that anchor. Run `validate_release_component_matrix.py`; only `status=passed` may be marked release ready. A missing work-item comment is never sufficient to report a Web item as unmapped. **小程序** records one skip receipt per delivery. Existing frozen scope drift blocks rather than being silently expanded.
9. Derive the project, A-class requirement batch, source deliveries, qualifying Bugs, test task state, end channel and release scope directly from the iteration, A/B/C/D classifier and release task. B-class deferred requirements remain recorded but excluded and non-blocking; any C/D item blocks. Test deployment, QA evidence, case execution, defect closure, release approver, release window, rollback plan, and production-verification plan are optional records, not release gates. Never substitute the full iteration or manually supplied scope.
10. For `执行发布`, require the release task to be uniquely read back and marked release ready, then read its persisted attempt ledger, frozen component matrix and latest `mergePlan`. Recompute the frozen Web `releaseCodeItems` coverage and run `validate_release_component_matrix.py` again before any merge or attempt creation. If scope and direct relations are unchanged, no attempt exists, and the matrix merely omitted a code-derived repository/component, automatically complete Codeup discovery and create a new `mergePlanVersion` with an explicit revision reason; never mutate an executed plan in place. For every Web component, derive and freeze the repository's verified production target branch from official Codeup/Flow configuration; never hardcode `master` or substitute repository `dev`. `MERGE_SOURCE_BRANCH` merges the verified source branch/MR; `BUILD_CLEAN_CANDIDATE` replays only the frozen exact commits; `ALREADY_CONTAINED` records target evidence without another merge. Inspect the candidate patch tree and map only frozen modules to component pipelines. An existing release task's sprint/iteration field is historical metadata: do not write or change it, and do not block execution when project and frozen scope are consistent. For every small-program component, write the skip receipt without querying a cloud pipeline. Manual-operation reconciliation requires one matching terminal-success production run per component. With a terminal failed attempt, prohibit a new production execution and return the repair/`重新发布` path.
11. Initialize one `releaseMergeAttemptId` from the frozen plan with `execute_release_merge_plan.py init`. Preflight every repository target HEAD, exact source commit set, MR state, mandatory checks, clean-candidate patch tree and pipeline mapping before the first merge. Persist each successful target merge immediately with its read-back target SHA. If a later repository fails, record `PARTIAL_TARGET_MERGE`; do not undo already merged commits silently, do not rebuild a new plan without a revision reason, and do not start production. Resume only the still-pending repositories after revalidating all target HEADs, or use separately reviewed revert MRs and record `REVERTED` after every occupied target is restored.
12. Before any **Web** production execution or manual-execution reconciliation, require the explicit command, one exact release task and frozen scope, a `validate_release_component_matrix.py` result of `passed`, the merge attempt state `TARGETS_READY`, a complete component matrix covering every changed repository, every exact commit present in its verified target branch, a patch-tree module map containing no out-of-scope paths, one active production pipeline per mapped component with matching source and deployment target, complete runtime parameters, and no duplicate active or successful execution for each component. The set of pipelines to submit is the distinct pipeline IDs from the validated matrix, never a single preferred frontend pipeline. For multi-module repositories, execute every and only the mapped component pipeline; never run all repository pipelines, and never omit a changed mapped module. Record `MERGED_NOT_DEPLOYED` before submitting pipelines, then submit independent mapped components concurrently; reconciliation never submits them. Record per-component execution IDs or small-program skip receipts. A named Bug-only exception may waive that Bug's code-anchor validation, but never waives repository discovery, exact-commit containment, patch-tree module mapping, component-matrix coverage, pipeline mapping, or another component's gates. Record approval, window, rollback, and production-verification information when available; rely on native pipeline approval stages and never bypass them.
13. Keep five evidence classes separate: test deployment, production pipeline, production verification, release change, and product acceptance.
14. For CLI polling, use live execution read-back and do not require callback evidence. Only callback-driven writes must pass `verify_release_callback.py` signature, timestamp, execution, scope, idempotency, and replay checks.
15. On technical production success, record any readable tag, commit, artifact, health, smoke, business, or observation evidence; mark unavailable items as `未自动验证` without inventing values.
16. For **Web**, when every required component execution has a unique ID, logical environment `prod`, matching frozen scope, and terminal success, record deployment success in the merge attempt, write and read back technical production evidence, move the release task and requirements to `发布完成`, recheck erroneous auto-close, and emit the product-acceptance handoff. **小程序** uses its successful `miniprogram_skip_pipeline` attempt instead; it never requires component execution, production evidence, monitoring, or external evidence.
17. On a verified terminal production failure (`失败`、`已取消`、`超时` or an equivalent platform terminal state that cannot continue) or an explicit frozen production-check failure, collect logs/evidence, preserve `MERGED_NOT_DEPLOYED` plus the execution and validation record, and write the real `发布失败` state.
18. In the same `执行发布` goal, automatically roll back only when a stored rollback mechanism, unique stable target, usable artifact, permission, and idempotency record are all available. Otherwise keep the real failure, report `自动回滚=false`, and return the manual recovery boundary without blocking the original production attempt in advance.
19. Do not classify an approval wait, missing parameter, login/OTP boundary, temporary permission block, running job, observability outage, missing evidence, or unknown/stale status as failure. Keep the merge attempt resumable and report the boundary without rolling back unless the frozen plan explicitly defines that observed condition as a rollback-triggering failure.
20. On `执行回滚`, require the exact release task plus a concrete reason and evidence, reject closed product lifecycles, and apply the same single-rollback gates before changing release state or executing recovery.
21. On rollback success, preserve production, verification, incident, rollback and merge-attempt evidence; record before/after versions; keep the release task in the real failed state; and hand defect repair/re-release disposition to product and development ownership.
22. On rollback failure, preserve logs and partial state and prohibit automatic retry until an authorized recovery plan exists.
23. If the task is already release-complete and there is no explicit `执行回滚`, do not rerun production; only reconcile status and evidence, then idempotently re-emit any missing product handoff.
24. After a stable rollback or evidenced product-acceptance failure, emit `$YunxiaoQA` plus `接收发布回流：发版任务=<ID>；触发=<发布失败|产品验收失败>；证据=<ID或URL>`.
25. On `重新发布`, verify the failure evidence, unchanged scope, affected Bugs closed, current regression evidence, and explicit authorization; increment the attempt number, create a new release-attempt ID/idempotency key linked to the previous terminal attempt, start one new execution per required component, preserve every previous attempt and merge attempt, record available production checks, and emit a fresh product-acceptance handoff after technical success.

## Non-negotiable gates

- Test deployment is never production release evidence.
- 发布准备、执行、回滚、重发和查询均不得读取或列出测试流水线；测试流水线只属于显式`执行测试流水线`命令。
- Direct pipeline execution does not itself prove deployment success or authorize any work-item state change.
- For **Web**, test and production pipelines are pre-created project configuration. Missing or ambiguous active repository-to-pipeline mapping blocks Web execution and must never trigger pipeline creation, copying, updating, renaming, or service-connection creation, except for the explicit simulated-production exception above. **小程序** does not require any cloud pipeline mapping. Retired/disabled definitions and names marked `-old`, `_old`, `-legacy`, `_legacy`, `旧`, `停用`, `废弃`, or `归档` are ignored before deciding Web ambiguity.
- Reject a direct execution when the active pipeline name has zero or multiple matches, the logical release environment conflicts with the command, or required runtime parameters are missing. A raw Flow `envName=日常环境` does not conflict by itself when the active pipeline name, Codeup source/branch, and deployment target consistently identify production.
- Redact passwords, tokens, cookies, access keys, private keys, authorization headers, and secret variable values before returning or saving logs.
- Distinguish an explicit log-confirmed cause from a likely inference and from a visible failure symptom.
- Pipeline success proves technical release only after the execution environment and frozen scope also read back correctly; it never proves product or business acceptance.
- `准备发布` defaults to automatic iteration scope: every non-deferred requirement at `测试完成` is selected and fully checked. A selected incomplete/evidence-defective item (C) or scope anomaly (D) blocks; formally deferred or not-yet-test-complete iteration items are B, recorded but not released. `需求=` is only an explicit partial-release override.
- QA evidence, test-deployment manifests, case execution, defect-closure manifests, approver fields, release windows, rollback plans, callback signatures, and production-verification plans are optional evidence for normal initial release. Missing or differently formatted optional evidence must never classify an otherwise test-complete item as C/D.
- `准备发布` requires one unique iteration and creates/reuses one top-level release task with a frozen scope, source delivery list and qualified Bug list. **Web** additionally requires its changed-code component/pipeline matrix; **小程序** requires no cloud code or pipeline matrix. Missing, cross-project, title-only, ambiguous, delivery-child, or scope-drifting relations block writes. Missing cloud-observability and optional release-control fields never block the small-program path.
- `查询发布` requires exactly one release-task ID. Requirement IDs and pipeline execution IDs may appear only in returned evidence, never as alternative query parameters.
- Never print or store Webhook secrets, cookies, tokens, or private keys.
- A repeated execution ID must not advance the requirement twice.
- An active or successful release execution must never be duplicated by `执行发布`.
- `PARTIAL_TARGET_MERGE` and `MERGED_NOT_DEPLOYED` are recoverable states, not proof of release success and not dead gates. Resume only pending repositories or missing deployment components after live read-back; never repeat a successful merge or pipeline execution.
- Until all five lifecycle Skills are officially read back at suite version `10.1.0`, release preparation reads new and legacy evidence but does not write a new-format delivery ledger or execute a new-format merge plan. Existing legacy release flow remains available; version skew must not create mixed evidence.
- No production pipeline may start while any repository in the frozen `mergePlan` is pending, failed, drifted, or reverted incompletely. A conflict creates a new plan version with a reason; it never authorizes a force merge.
- Every first and subsequent production attempt must have a persisted attempt number, type, ID, authorized command, component execution list, status, and idempotency key. A terminal failed attempt can never be replaced, cleared, or reused by `执行发布`.
- `执行发布` must not guess a rollback target, reuse a stale artifact, or start a second rollback while one is active or already successful.
- Automatic rollback requires a verified terminal production failure or an explicit failed production check plus a stored, uniquely resolvable rollback plan and stable version anchor. When these are absent, return `自动回滚=false` and manual recovery guidance; do not block the release attempt before production submission.
- Active rollback requires an explicit `执行回滚` command, a release not yet closed by product acceptance, verified incident evidence, and the same rollback target/artifact/permission/idempotency gates.
- `重新发布` requires current regression evidence and closed affected Bugs, but does not require custom QA or test-deployment JSON schemas.
- Never mark a **Web** release `发布完成` until every required component execution succeeds and its logical prod environment and frozen scope read back correctly. Mark a **小程序** release `发布完成` after its channel/scope/idempotency checks and successful `miniprogram_skip_pipeline` attempt; do not require cloud execution, logical prod environment, monitoring, or external evidence.
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
