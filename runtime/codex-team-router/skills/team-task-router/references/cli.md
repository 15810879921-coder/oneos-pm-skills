# CLI reference

`router.py` is a local Python 3.10+ reference runtime. It records caller-supplied decisions and receipts; it does not invoke models, prove sandbox enforcement, or report billed charges.

## Invocation and state

```bash
python3 skills/team-task-router/scripts/router.py \
  --state-dir /tmp/team-router-state --profile local \
  route --dry-run --input skills/team-task-router/templates/decision-card.json
```

Global `--state-dir` and `--profile` precede the command. Each command accepts `--input FILE`; use `--input -` for stdin. State defaults to `$CODEX_HOME/state/team-task-router`, or `~/.codex/state/team-task-router` when `CODEX_HOME` is unset. `local` names the OS-account namespace and does not assert a human identity. Shared OS accounts should use separate profiles.

Successful stdout is one JSON object. Validation errors use exit code 2 and concise stderr. SQLite errors use exit code 3. Fields outside the schemas below are rejected.

## `route`

The input is a decision card. A complete synthetic card is in `templates/decision-card.json`.

Required fields:

| Field | Schema |
|---|---|
| `task_id`, `phase_id`, `input_revision`, `rules_revision`, `scope`, `pattern` | non-empty string |
| `domain` | `product`, `development`, `testing`, or `general` |
| `kind` | `mechanical`, `implementation`, `analysis`, `review`, or `coordination` |
| `clarity` | `clear`, `partial`, or `unclear` |
| `judgment` | `low`, `routine`, `complex`, or `exceptional` |
| `impact` | `local`, `cross_module`, or `cross_service` |
| `risk` | `low`, `medium`, or `high` |
| `verifiability` | `deterministic`, `testable`, or `uncertain` |
| `execution_size` | `tiny`, `normal`, or `large` |
| `constraints_ready`, `authorized`, `independent`, `parent_has_work` | boolean |
| `current` | `{"model": MODEL, "effort": EFFORT}` |
| `available` | observed list of `{"model": MODEL, "efforts": [EFFORT, ...]}`; duplicates are invalid |

Optional fields:

| Field | Schema |
|---|---|
| `requested` | explicit `model` and `effort` pair |
| `estimates` | `direct_credits` and `delegated_credits`; each is finite nonnegative number or null and covers the complete path |
| `approved_fallbacks` | list of `model`, `effort`, and `estimated_credits` objects |
| `budget_credits` | finite nonnegative number or null |
| `capability_failure` | `model`, `effort`, and opaque `evidence_ref` |

Models are exactly `gpt-5.6-luna`, `gpt-5.6-terra`, `gpt-5.6-sol`, and `gpt-6-astra`. Luna supports low through max; the other models also support ultra. Automatic executor selection never adds max or ultra. Coordination on an already selected Astra retains its observed effort, including an explicitly chosen max or ultra.

The result keeps `desired`, `selected`, and `actual` separate. `status` is `planned`, `blocked`, or `unavailable`; a planned decision has `execution_kind` `self` or `delegate`. Replaying the same phase key and card returns `replayed: true` and its current `phase_status`. A changed card on the same key is a conflict; use `replan` only for observed runtime-condition changes.

## `replan`

Input fields are the original phase key (`scope`, `task_id`, `phase_id`, `input_revision`, `rules_revision`), a complete updated `card`, and an opaque `evidence_ref`. The card key must match. Replan may only change `current`, `available`, `requested`, `estimates`, `approved_fallbacks`, `budget_credits`, `capability_failure`, `authorized`, `constraints_ready`, `independent`, and `parent_has_work`.

```json
{
  "scope": "synthetic-local-demo",
  "task_id": "synthetic-task-001",
  "phase_id": "implementation",
  "input_revision": "input-v1",
  "rules_revision": "rules-v1",
  "card": {"complete": "decision card with only runtime-condition changes"},
  "evidence_ref": "runtime:availability-observed"
}
```

The placeholder under `card` must be replaced by the complete card schema above. Replan is rejected while any run is dispatching, running, verifying, or completed. Failed, blocked, or cancelled runs remain immutable; their usage and feedback stay in the ledger. A later `start` still needs explicit retry authorization. Identical replans are idempotent.

## Lifecycle commands

`start` atomically claims a planned phase. Its input is the five phase-key strings plus `run_id`, `execution_kind` (`self` or `delegate`), `evidence_ref`, and optional `retry_authorized` boolean. It returns `dispatching`; native execution and SQLite are not one transaction.

```json
{"scope":"synthetic-local-demo","task_id":"synthetic-task-001","phase_id":"implementation","input_revision":"input-v1","rules_revision":"rules-v1","run_id":"run-001","execution_kind":"delegate","evidence_ref":"runtime:start"}
```

`bind` records the actual runtime receipt. Required fields are `run_id`, `actual_agent_id`, `actual_session_id`, `model`, `effort`, `role` (`coordinator`, `executor`, or `reviewer`), `evidence_ref`, and `sandbox` (string or null). The observed pair must exactly match the route selection. A mismatch is stored as an immutable caller-supplied audit receipt and remains `dispatching` with `reconciliation_required`; reconcile the original run instead of creating a replacement.

```json
{"run_id":"run-001","actual_agent_id":"agent-001","actual_session_id":"session-001","model":"gpt-5.6-luna","effort":"medium","role":"executor","evidence_ref":"runtime:bind","sandbox":null}
```

`verify` requires a running bound run and accepts `run_id` plus verification `evidence_ref`. `finish` accepts `run_id`, `status` (`completed`, `failed`, `blocked`, or `cancelled`), `evidence_ref`, and optional nonnegative integer `elapsed_ms`. Completed requires prior verification; terminal outcomes cannot later change.

```json
{"run_id":"run-001","evidence_ref":"test:unit-suite"}
```

```json
{"run_id":"run-001","status":"completed","evidence_ref":"runtime:finish","elapsed_ms":1200}
```

## `usage` and `summary`

`usage` requires `run_id`, globally unique `sample_id`, `includes_child_usage`, `rate_version`, and `speed_mode`. Optional counters are `input_tokens`, `cached_input_tokens`, `output_tokens`, and `reasoning_tokens`; missing values stay null. Optional `elapsed_ms` is a nonnegative integer, `parent_run_id` links a child run, and `coverage_complete` defaults to false.

Use the runtime's stable usage-event identifier as `sample_id`. Do not generate a new ID for a replay. The ledger detects an identical replay and a conflicting reuse of one ID, but it cannot detect an omitted event or the same event submitted under a different ID.

```json
{"run_id":"run-001","sample_id":"usage-event-001","input_tokens":1000,"cached_input_tokens":200,"output_tokens":100,"reasoning_tokens":25,"includes_child_usage":false,"rate_version":"codex-standard-2026-09-10","speed_mode":"standard","elapsed_ms":1200,"coverage_complete":true}
```

Set `coverage_complete: true` only on a terminal run after every delta is recorded. That sample closes the run to further samples. Counters that include child usage are rejected. Input includes cached input; output already includes runtime-reported reasoning, so reasoning is not added again. Supported rates in credits per million `[new input, cached input, output]` are Luna `[5,0.5,30]`, Terra `[50,5,300]`, Sol `[100,10,500]`, and Astra `[250,25,1250]`. Astra `fast` is 2.5x only when reported explicitly. Unsupported speed/rate combinations return unknown cost.

`summary` input is `scope` and `task_id`.

```json
{"scope":"synthetic-local-demo","task_id":"synthetic-task-001"}
```

The result separates `coordinator`, `executors`, `retries`, and `reviewers`. `known_credits_subtotal` is only the known estimate. `total_task_credits` remains null unless required roles are covered and every run is terminal with complete closed usage. `savings_percentage` is always null because the runtime has no billed baseline.

## `feedback` and `history`

`feedback` requires `event_id`, bound `run_id`, opaque `evidence_ref`, `cause`, `source`, and booleans `user_correction`, `accepted`, and `verified`. Causes are `wrong_result`, `missed_constraint`, `capability`, `requirement_change`, `preference_change`, `environment`, `tool_failure`, or `unknown`. Only `source: user` may mark `user_correction` or `accepted`; verification is separate.

```json
{"event_id":"feedback-001","run_id":"run-001","evidence_ref":"user:correction-001","cause":"missed_constraint","source":"user","user_correction":true,"accepted":false,"verified":false}
```

`history` requires `scope`, `pattern`, `rules_revision`, `model`, and `effort`.

```json
{"scope":"synthetic-local-demo","pattern":"frozen-local-change","rules_revision":"rules-v1","model":"gpt-5.6-luna","effort":"medium"}
```

History is scoped to the exact scope, pattern, rules revision, actual model, and actual effort. Any explicit quality correction within one task counts once. Two independently corrected tasks among the latest five feedback-bearing tasks set `reassessment_required: true`; this is a review signal, not a permanent model floor.

## End-to-end command pattern

Write each JSON object above to a file, then call the lifecycle in order:

```bash
python3 skills/team-task-router/scripts/router.py --state-dir /tmp/router --profile demo route --input card.json
python3 skills/team-task-router/scripts/router.py --state-dir /tmp/router --profile demo start --input start.json
python3 skills/team-task-router/scripts/router.py --state-dir /tmp/router --profile demo bind --input bind.json
python3 skills/team-task-router/scripts/router.py --state-dir /tmp/router --profile demo verify --input verify.json
python3 skills/team-task-router/scripts/router.py --state-dir /tmp/router --profile demo finish --input finish.json
python3 skills/team-task-router/scripts/router.py --state-dir /tmp/router --profile demo usage --input usage.json
python3 skills/team-task-router/scripts/router.py --state-dir /tmp/router --profile demo summary --input summary.json
```

Use `replan` only to record changed runtime conditions on an eligible phase. It does not dispatch, resume, retry, or switch a model by itself.
