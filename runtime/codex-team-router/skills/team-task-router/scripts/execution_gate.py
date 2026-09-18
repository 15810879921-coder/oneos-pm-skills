#!/usr/bin/env python3
"""Native hook routing gate. No model calls, no hook trust writes.

This is a workflow guard for covered native tool paths, not a security boundary.
Classification is supplied by the coordinator; dispatch/model proof is read back.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import sqlite3
import sys
import time

from python_runtime import reexec_if_needed

reexec_if_needed(__file__, sys.argv[1:])

import tomllib

import router
import job_roles as jobs

VERSION = "2.2.0"
SCRIPT = Path(__file__).resolve()
TASK_TYPES = {"requirement", "delivery", "development", "test"}
ROLE_PAIRS = {
    "team_luna_fast": ("gpt-5.6-luna", "low"),
    "team_luna_executor": ("gpt-5.6-luna", "medium"),
    "luna_worker": ("gpt-5.6-luna", "max"),
    "team_terra_specialist": ("gpt-5.6-terra", "medium"),
    "team_sol_expert": ("gpt-5.6-sol", "high"),
    "team_sol_reviewer": ("gpt-5.6-sol", "high"),
    "team_astra_expert": ("gpt-6-astra", "high"),
}


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def transcript_info(path, turn_id=None):
    """Bounded metadata-only read. Missing/old contexts never inherit a model."""
    p = Path(path)
    meta, context = None, None
    with p.open("rb") as f:
        for _ in range(10):
            line = f.readline(1024 * 1024)
            if not line:
                break
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if row.get("type") == "session_meta":
                meta = row["payload"]
                break
        size = p.stat().st_size
        f.seek(max(0, size - 8 * 1024 * 1024))
        if f.tell():
            f.readline()
        for line in f:
            if b'"turn_context"' not in line:
                continue
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if row.get("type") == "turn_context":
                candidate = row["payload"]
                if turn_id is None or candidate.get("turn_id") == turn_id:
                    context = candidate
    if not meta:
        raise ValueError("native transcript identity unavailable")
    return meta, context


def identity(payload):
    # Native child hooks can share the root session_id. Prefer transcript identity.
    path = payload.get("transcript_path")
    if not path or not payload.get("turn_id"):
        raise ValueError("hook transcript_path/turn_id unavailable")
    meta, _ = transcript_info(path)
    source = meta.get("source")
    child = isinstance(source, dict) and "subagent" in source
    return str(meta["id"]), str(payload["turn_id"]), child


def deny(reason):
    return {"hookSpecificOutput": {"hookEventName": "PreToolUse",
            "permissionDecision": "deny", "permissionDecisionReason": reason}}


def context(event, message):
    return {"hookSpecificOutput": {"hookEventName": event, "additionalContext": message}}


def is_spawn(name):
    return name in {"Agent", "spawn_agent", "collaboration.spawn_agent"}


def bootstrap(payload):
    """Only a single, literal invocation of this CLI may pass before assessment."""
    name = payload.get("tool_name", "")
    inp = payload.get("tool_input") or {}
    if name not in {"Bash", "exec_command"} or not isinstance(inp, dict):
        return False
    command = inp.get("command", inp.get("cmd"))
    if not isinstance(command, str) or any(c in command for c in ("\n", "\r", "`", "$")):
        return False
    try:
        args = shlex.split(command)
    except ValueError:
        return False
    # All remaining parameters are consumed by argparse; shell syntax is forbidden.
    if any(c in command for c in (";", "|", "&", "<", ">")):
        return False
    if len(args) < 3 or Path(args[0]).name not in {"python3", "python3.12"}:
        return False
    if args[1] != str(SCRIPT) or args[2] not in {"describe", "assess", "status", "retry", "role-read",
                                                  "role-confirm", "role-status", "role-result", "role-handoff"}:
        return False
    return True


class Gate:
    def __init__(self, home):
        self.home = Path(home).resolve()
        self.directory = self.home / "state/team-task-router/execution-gate"
        self.directory.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.directory / "gate.sqlite3", timeout=3)
        self.db.row_factory = sqlite3.Row
        self.db.execute("CREATE TABLE IF NOT EXISTS turns(thread TEXT, turn TEXT, data TEXT, PRIMARY KEY(thread,turn))")

    def load(self, thread, turn):
        row = self.db.execute("SELECT data FROM turns WHERE thread=? AND turn=?", (thread, turn)).fetchone()
        return json.loads(row[0]) if row else None

    def save(self, thread, turn, state):
        self.db.execute("INSERT OR REPLACE INTO turns VALUES(?,?,?)", (thread, turn, encoded(state)))

    def initial(self, payload):
        return {"transcript_path": payload["transcript_path"], "model": payload.get("model"),
                "cwd": payload.get("cwd"), "user_prompt": payload.get("prompt"),
                "status": "unassessed", "observed_tool_calls": 0, "blocked_calls": 0,
                "started_at": time.time(), "hook_events": {}, "actual": None,
                "trust_status": "unknown", "attempts": [],
                "job_roles": {"required": [], "active": [], "records": {}, "prompt_source": None}}

    def role_state(self, state):
        value = state.get("job_roles")
        if not isinstance(value, dict):
            value = {"required": [], "active": [], "records": {}, "prompt_source": None}
            state["job_roles"] = value
        value.setdefault("required", [])
        value.setdefault("active", [])
        value.setdefault("records", {})
        value.setdefault("prompt_source", None)
        return value

    def assign_job_roles(self, state, required, active, requested_skills=None, phase="primary-execution"):
        role_state = self.role_state(state)
        requested_skills = requested_skills or {}
        for role in required:
            if role not in jobs.ROLE_ORDER:
                raise ValueError("unknown job role: " + str(role))
            if role not in role_state["required"]:
                role_state["required"].append(role)
            if role not in role_state["records"]:
                name, path, source = jobs.resolve_skill(self.home, role, state.get("cwd"), requested_skills.get(role))
                role_state["records"][role] = {
                    "status": "assigned", "skill": name, "skill_path": str(path),
                    "skill_source": source, "assigned_phase": phase, "assigned_at": time.time(),
                    "read": None, "involved": None, "result": None, "handoff": None,
                }
        role_state["required"] = [role for role in jobs.ROLE_ORDER if role in role_state["required"]]
        role_state["active"] = [role for role in jobs.ROLE_ORDER if role in active]

    def refresh_job_roles(self, state):
        role_state = self.role_state(state)
        transcripts = [state.get("transcript_path")]
        actual = state.get("actual")
        if isinstance(actual, dict):
            transcripts.append(actual.get("evidence_ref"))
        for role, record in role_state["records"].items():
            try:
                _, current_path, _ = jobs.resolve_skill(self.home, role, state.get("cwd"), record.get("skill"))
                current_hash = jobs.skill_digest(current_path)
            except (OSError, ValueError):
                current_path, current_hash = Path(record["skill_path"]), None
            previous_read = record.get("read")
            path_changed = str(current_path) != record.get("skill_path")
            hash_changed = bool(previous_read and previous_read.get("skill_sha256") != current_hash)
            if previous_read and (path_changed or hash_changed or current_hash is None):
                snapshot = {key: record.get(key) for key in ("read", "involved", "result", "handoff")}
                snapshot.update(invalidated_at=time.time(), reason=("skill_path_changed" if path_changed else
                                                                  ("skill_content_changed" if current_hash else "skill_unavailable")),
                                current_skill_sha256=current_hash, current_skill_path=str(current_path))
                record.setdefault("invalidated_history", []).append(snapshot)
                for key in ("read", "involved", "result", "handoff", "read_pending"):
                    record[key] = None
                record["status"] = "assigned"
            if current_hash is None:
                continue
            record["skill_path"] = str(current_path)
            if record.get("read"):
                continue
            skill_path = current_path
            for transcript in transcripts:
                if not transcript:
                    continue
                evidence = jobs.transcript_read_evidence(transcript, skill_path, record["skill"], role)
                if evidence:
                    record["read"] = dict(evidence, confirmed_at=time.time())
                    record["involved"] = {"phase": record.get("assigned_phase"),
                                          "evidence_ref": evidence["call_id"], "confirmed_at": time.time()}
                    record["status"] = "involved"
                    break
            if record.get("read") and record.get("involved"):
                record["status"] = "involved"
            else:
                record["status"] = "assigned"
            if record.get("involved") and record.get("result"):
                record["status"] = "result"
            if record.get("result") and record.get("handoff"):
                record["status"] = "handed_off"
        return role_state

    def role_gaps(self, state):
        role_state = self.refresh_job_roles(state)
        gaps = []
        for role in role_state["active"]:
            record = role_state["records"].get(role, {})
            if not record.get("read"):
                gaps.append({"role": role, "missing": "read"})
            elif not record.get("involved"):
                gaps.append({"role": role, "missing": "involved"})
        return gaps

    def completion_role_gaps(self, state):
        role_state = self.refresh_job_roles(state)
        gaps = []
        for role in role_state["required"]:
            record = role_state["records"].get(role, {})
            for field in ("read", "involved", "result", "handoff"):
                if not record.get(field):
                    gaps.append({"role": role, "missing": field})
                    break
        return gaps

    def public_job_roles(self, state):
        role_state = self.refresh_job_roles(state)
        execution_gaps = self.role_gaps(state)
        return {"required": role_state["required"], "active": role_state["active"],
                "records": role_state["records"], "gaps": execution_gaps,
                "execution_gaps": execution_gaps, "completion_gaps": self.completion_role_gaps(state),
                "prompt_source": role_state.get("prompt_source"),
                "inferred": role_state.get("inferred", []),
                "exclusions": role_state.get("exclusions", {})}

    def available(self, names):
        if not isinstance(names, list) or not names or len(names) != len(set(names)):
            raise ValueError("available_roles must be distinct names observed in the current spawn tool")
        installed = {}
        for p in (self.home / "agents").glob("*.toml"):
            try:
                obj = tomllib.loads(p.read_text())
                installed[obj.get("name")] = (obj.get("model"), obj.get("model_reasoning_effort"))
            except (ValueError, OSError):
                continue
        result = {}
        for name in names:
            pair = ROLE_PAIRS.get(name)
            if not pair or installed.get(name) != pair:
                raise ValueError(f"role unavailable or changed: {name}")
            result.setdefault(pair[0], []).append(pair[1])
        return [{"model": m, "efforts": sorted(set(es))} for m, es in result.items()]

    def assess(self, thread, turn, request):
        allowed = {"domain", "kind", "clarity", "judgment", "impact", "risk", "verifiability",
                   "execution_size", "constraints_ready", "authorized", "independent", "parent_work",
                   "reason", "available_roles", "requested", "estimates", "phase", "prompt",
                   "job_roles", "job_role_skills", "job_role_exclusions", "task_scope"}
        required = allowed - {"requested", "estimates", "phase", "prompt", "job_roles", "job_role_skills",
                              "job_role_exclusions", "task_scope"}
        if not isinstance(request, dict) or set(request) - allowed or required - set(request):
            raise ValueError("assessment fields missing or unknown; use describe")
        if not isinstance(request["reason"], str) or not request["reason"].strip():
            raise ValueError("reason required")
        if not isinstance(request["parent_work"], str):
            raise ValueError("parent_work must describe real independent work, or be empty")
        self.db.execute("BEGIN IMMEDIATE")
        try:
            state = self.load(thread, turn)
            if not state:
                # Allows a current task to use the gate before native hooks are enabled.
                db = sqlite3.connect((self.home / "state_5.sqlite").as_uri() + "?mode=ro", uri=True)
                try:
                    row = db.execute("SELECT rollout_path FROM threads WHERE id=?", (thread,)).fetchone()
                finally:
                    db.close()
                if not row:
                    raise ValueError("native thread unavailable")
                state = self.initial({"transcript_path": row[0]})
                state["activation"] = "manual_cli_only"
            meta, ctx = transcript_info(state["transcript_path"], turn)
            if meta["id"] != thread or not ctx:
                raise ValueError("exact current native thread/turn context unavailable")
            if isinstance(meta.get("source"), dict) and "subagent" in meta["source"]:
                raise ValueError("children execute their assigned scope; recursive assessment forbidden")
            if state.get("pending") or state.get("actual"):
                if state.get("request") == request:
                    return self.public(state)
                if (state.get("actual") and request.get("phase", "primary-execution")
                        != state["card"]["phase_id"]):
                    state.setdefault("prior_phases", []).append({k: state.get(k) for k in
                        ("card", "decision", "pending", "actual", "request", "status")})
                    state.pop("pending", None)
                    state["actual"] = None
                else:
                    raise ValueError("dispatch already attempted; reconcile it before any new allocation")
            pair = {"model": ctx["model"], "effort": ctx["effort"]}
            scope_decision = self.task_scope_decision(request.get("task_scope"), pair)
            if scope_decision["status"] != "planned":
                state.update(request=request, status="blocked", decision=scope_decision,
                             selected_role=None, task_name=None)
                self.save(thread, turn, state)
                self.db.commit()
                return self.public(state)
            if scope_decision["reason"] in {"legacy_task_bypass", "root_task_bypass"} or scope_decision["reason"].endswith("_allow"):
                state["scope_bypass"] = True
                state.update(request=request, status="planned", decision=scope_decision,
                             selected_role=None, task_name=None)
                state["task_scope_decision"] = scope_decision
                self.save(thread, turn, state)
                self.db.commit()
                return self.public(state)
            available = self.available(request["available_roles"])
            existing = next((v for v in available if v["model"] == pair["model"]), None)
            if existing:
                existing["efforts"] = sorted(set(existing["efforts"] + [pair["effort"]]))
            else:
                available.append({"model": pair["model"], "efforts": [pair["effort"]]})
            card = {k: request[k] for k in required - {"parent_work", "reason", "available_roles"}}
            card.update(task_id=thread, input_revision=turn, rules_revision=VERSION,
                        phase_id=request.get("phase", "primary-execution"), scope="native-execution-gate",
                        pattern="cost-first-execution", parent_has_work=bool(request["parent_work"].strip()),
                        current=pair, available=available)
            for key in ("requested", "estimates"):
                if key in request:
                    card[key] = request[key]
            decision = router.execute("route", card, self.home / "state/team-task-router", "local", False)
            selected = decision.get("selected")
            selected_role = next((n for n in request["available_roles"]
                                  if selected and ROLE_PAIRS[n] == (selected["model"], selected["effort"])), None)
            if decision.get("execution_kind") == "delegate" and not selected_role:
                raise ValueError("selected pair has no observed installed role; generic dispatch not supported by this gate")
            state.update(request=request, card=card, decision=decision, model=pair["model"],
                         status=decision["status"], selected_role=selected_role,
                         task_name="routed_" + hashlib.sha256((thread + turn + card["phase_id"]).encode()).hexdigest()[:12])
            state["task_scope_decision"] = scope_decision
            native_prompt = state.get("user_prompt")
            supplied_prompt = request.get("prompt")
            if native_prompt and supplied_prompt is not None and supplied_prompt != native_prompt:
                raise ValueError("assessment prompt differs from native UserPromptSubmit prompt")
            prompt = native_prompt or supplied_prompt or ""
            inferred = jobs.classify_prompt(prompt)
            explicit = request.get("job_roles", [])
            if not isinstance(explicit, list) or len(explicit) != len(set(explicit)) or any(r not in jobs.ROLE_ORDER for r in explicit):
                raise ValueError("job_roles must be a distinct list of product/ux/development/qa")
            skill_map = request.get("job_role_skills", {})
            if not isinstance(skill_map, dict) or set(skill_map) - set(jobs.ROLE_ORDER) or any(not isinstance(v, str) or not v for v in skill_map.values()):
                raise ValueError("job_role_skills must map job roles to installed skill names")
            exclusions = request.get("job_role_exclusions", {})
            if (not isinstance(exclusions, dict) or set(exclusions) - set(inferred)
                    or any(not isinstance(v, str) or not v.strip() for v in exclusions.values())):
                raise ValueError("job_role_exclusions may only explain inferred roles with non-empty reasons")
            required_roles = [r for r in jobs.ROLE_ORDER if r in explicit or (r in inferred and r not in exclusions)]
            if explicit:
                active_roles = explicit
            elif required_roles:
                # Mixed work advances role by role; later phases remain visible as assigned.
                active_roles = [next((r for r in required_roles
                                      if not self.role_state(state)["records"].get(r, {}).get("handoff")), required_roles[-1])]
            else:
                active_roles = []
            self.assign_job_roles(state, required_roles, active_roles, skill_map, card["phase_id"])
            role_state = self.role_state(state)
            role_state["prompt_source"] = ("native_user_prompt" if native_prompt else
                                           ("coordinator_supplied" if supplied_prompt else "none"))
            role_state["inferred"] = inferred
            role_state["exclusions"] = exclusions
            self.save(thread, turn, state)
            self.db.commit()
            return self.public(state)
        except Exception:
            self.db.rollback()
            raise
        finally:
            if self.db.in_transaction:
                self.db.rollback()

    @staticmethod
    def task_scope_decision(scope, current):
        """Return a deterministic scope gate before model routing.

        Missing or malformed metadata is explicitly allowed with a diagnostic.
        Legacy tasks and root requirement/delivery tasks are allowed through;
        only post-cutover development/test children of a post-cutover
        requirement/delivery task enter model routing.
        """
        base = {"status": "planned", "reason": "task_scope_metadata_missing_allow",
                "execution_kind": "blocked", "current": current, "selected": None}
        if not isinstance(scope, dict):
            return {**base, "execution_kind": "direct", "selected": current}
        required = {"task_type", "created_at", "gate_effective_at"}
        if required - set(scope) or set(scope) - {
                "task_type", "created_at", "gate_effective_at", "parent_task_id",
                "parent_task_type", "parent_created_at", "parent_updated_at"}:
            return {**base, "reason": "task_scope_metadata_invalid_allow", "execution_kind": "direct",
                    "selected": current}
        task_type = scope.get("task_type")
        if task_type not in TASK_TYPES:
            return {**base, "reason": "task_scope_metadata_invalid_allow", "execution_kind": "direct",
                    "selected": current}
        numeric = ("created_at", "gate_effective_at")
        if any(isinstance(scope.get(key), bool) or not isinstance(scope.get(key), (int, float))
               for key in numeric):
            return {**base, "reason": "task_scope_metadata_invalid_allow", "execution_kind": "direct",
                    "selected": current}
        created_at = float(scope["created_at"])
        effective_at = float(scope["gate_effective_at"])
        if created_at < effective_at:
            return {**base, "status": "planned", "reason": "legacy_task_bypass",
                    "execution_kind": "direct", "selected": current}
        if task_type in {"requirement", "delivery"}:
            return {**base, "status": "planned", "reason": "root_task_bypass",
                    "execution_kind": "direct", "selected": current}
        parent_type = scope.get("parent_task_type")
        parent_id = scope.get("parent_task_id")
        parent_created = scope.get("parent_created_at")
        if (task_type in {"development", "test"} and isinstance(parent_id, str) and parent_id
                and parent_type in {"requirement", "delivery"}
                and isinstance(parent_created, (int, float)) and not isinstance(parent_created, bool)
                and float(parent_created) >= effective_at):
            return {"status": "planned", "reason": "derived_task_gate", "execution_kind": None,
                    "current": current, "selected": None}
        return {**base, "reason": "task_scope_non_target_allow", "execution_kind": "direct",
                "selected": current}

    def public(self, state):
        result = {k: state.get(k) for k in ("status", "decision", "selected_role", "task_name", "actual",
                                        "observed_tool_calls", "blocked_calls", "hook_events", "activation",
                                        "receipt_status", "trust_status")}
        result["job_roles"] = self.public_job_roles(state)
        return result

    def retry(self, thread, turn):
        with self.db:
            state = self.load(thread, turn)
            pending = state.get("pending") if state else None
            if not pending or not pending.get("native_failure") or pending.get("native_result"):
                raise ValueError("retry requires an explicit native failed-dispatch result; unknown outcomes must be reconciled")
            if len(state["attempts"]) >= 1:
                raise ValueError("same dispatch failed twice; stop and report evidence")
            state["attempts"].append(pending)
            del state["pending"]
            state["status"] = "planned"
            self.save(thread, turn, state)
            return self.public(state)

    def load_or_native(self, thread, turn):
        state = self.load(thread, turn)
        if state:
            return state
        db = sqlite3.connect((self.home / "state_5.sqlite").as_uri() + "?mode=ro", uri=True)
        try:
            row = db.execute("SELECT rollout_path FROM threads WHERE id=?", (thread,)).fetchone()
        finally:
            db.close()
        if not row:
            raise ValueError("native thread unavailable")
        meta, ctx = transcript_info(row[0], turn)
        if meta.get("id") != thread or not ctx:
            raise ValueError("exact current native thread/turn context unavailable")
        state = self.initial({"transcript_path": row[0]})
        state["activation"] = "manual_cli_only"
        return state

    def role_read(self, thread, turn, role, requested_skill=None):
        with self.db:
            state = self.load_or_native(thread, turn)
            self.assign_job_roles(state, [role], [role], {role: requested_skill} if requested_skill else {},
                                  state.get("card", {}).get("phase_id", "role-bootstrap"))
            record = self.role_state(state)["records"][role]
            path = Path(record["skill_path"])
            content = path.read_text()
            receipt = hashlib.sha256((thread + turn + role + jobs.skill_digest(path)).encode()).hexdigest()[:24]
            record["read_pending"] = {"receipt": receipt, "skill_sha256": jobs.skill_digest(path),
                                      "requested_at": time.time()}
            self.save(thread, turn, state)
            return {"job_role_read_receipt": receipt, "role": role, "skill": record["skill"],
                    "skill_path": str(path), "skill_sha256": jobs.skill_digest(path), "content": content,
                    "next": "role-confirm is optional; status and the next protected tool auto-check the transcript"}

    def role_confirm(self, thread, turn, role):
        with self.db:
            state = self.load_or_native(thread, turn)
            if role not in self.role_state(state)["records"]:
                raise ValueError("job role is not assigned")
            self.refresh_job_roles(state)
            record = self.role_state(state)["records"][role]
            if not record.get("read"):
                raise ValueError("no paired assistant read call and successful result found in the transcript")
            self.save(thread, turn, state)
            return {"role": role, "status": record["status"], "read": record["read"],
                    "involved": record["involved"]}

    def role_result(self, thread, turn, value):
        allowed = {"role", "summary", "evidence"}
        if not isinstance(value, dict) or set(value) != allowed:
            raise ValueError("role-result requires role, summary, and evidence")
        role, summary = value["role"], value["summary"]
        if role not in jobs.ROLE_ORDER or not isinstance(summary, str) or not summary.strip():
            raise ValueError("role-result requires a valid role and non-empty summary")
        evidence = jobs.validate_result_evidence(value["evidence"])
        with self.db:
            state = self.load_or_native(thread, turn)
            self.refresh_job_roles(state)
            record = self.role_state(state)["records"].get(role)
            if not record or not record.get("involved"):
                raise ValueError("job role needs verified skill read/involvement before recording a result")
            record["result"] = {"summary": summary.strip(), "evidence": evidence, "recorded_at": time.time()}
            record["status"] = "result"
            self.save(thread, turn, state)
            return {"role": role, "status": record["status"], "result": record["result"]}

    def role_handoff(self, thread, turn, value):
        allowed = {"role", "disposition", "next_role", "boundary", "artifacts", "unresolved", "acceptance"}
        if not isinstance(value, dict) or set(value) - allowed or {"role", "disposition", "boundary", "artifacts", "unresolved", "acceptance"} - set(value):
            raise ValueError("role-handoff fields missing or unknown")
        role, disposition = value["role"], value["disposition"]
        next_role = value.get("next_role")
        if role not in jobs.ROLE_ORDER or disposition not in {"handed_off", "closed"}:
            raise ValueError("invalid role or handoff disposition")
        if disposition == "handed_off" and next_role not in jobs.ROLE_ORDER:
            raise ValueError("handed_off disposition requires next_role")
        if disposition == "closed" and next_role is not None:
            raise ValueError("closed disposition cannot set next_role")
        if not isinstance(value["boundary"], str) or not value["boundary"].strip():
            raise ValueError("handoff boundary required")
        for key in ("unresolved", "acceptance"):
            if not isinstance(value[key], list) or any(not isinstance(v, str) or not v.strip() for v in value[key]):
                raise ValueError(key + " must be a list of non-empty strings")
        if not value["acceptance"]:
            raise ValueError("acceptance must contain at least one explicit acceptance point")
        artifacts = jobs.validate_result_evidence(value["artifacts"])
        with self.db:
            state = self.load_or_native(thread, turn)
            record = self.role_state(state)["records"].get(role)
            if not record or not record.get("result"):
                raise ValueError("job role result must be recorded before handoff/closure")
            record["handoff"] = {"disposition": disposition, "next_role": next_role,
                                 "boundary": value["boundary"].strip(), "artifacts": artifacts,
                                 "unresolved": value["unresolved"], "acceptance": value["acceptance"],
                                 "recorded_at": time.time()}
            record["status"] = "handed_off"
            if next_role:
                self.assign_job_roles(state, [next_role], [next_role], {}, "handoff-from-" + role)
            else:
                self.role_state(state)["active"] = []
            self.save(thread, turn, state)
            return {"role": role, "status": record["status"], "handoff": record["handoff"],
                    "next_active": self.role_state(state)["active"]}

    def recover_manual_dispatch(self, state, thread):
        """Recover a real manual-CLI dispatch from native parent/child records."""
        if (state.get("activation") not in {"manual_cli_only", "hook_payload_received"} or state.get("actual")
                or state.get("decision", {}).get("execution_kind") != "delegate"):
            return
        task_name, turn = state.get("task_name"), state.get("card", {}).get("input_revision")
        if not task_name or not turn:
            return
        calls, started, outputs = {}, {}, set()
        try:
            lines = Path(state["transcript_path"]).open(errors="replace")
        except OSError:
            return
        with lines:
            for line in lines:
                try:
                    row = json.loads(line)
                except ValueError:
                    continue
                payload = row.get("payload", {})
                if row.get("type") == "response_item" and payload.get("type") == "function_call" and payload.get("name") == "spawn_agent":
                    try:
                        args = json.loads(payload.get("arguments", "{}"))
                    except ValueError:
                        continue
                    meta_turn = payload.get("internal_chat_message_metadata_passthrough", {}).get("turn_id")
                    if (meta_turn == turn and args.get("task_name") == task_name
                            and args.get("agent_type") == state.get("selected_role") and args.get("fork_turns") == "none"
                            and "model" not in args and "reasoning_effort" not in args):
                        calls[payload.get("call_id")] = args
                elif row.get("type") == "event_msg" and payload.get("type") == "item_completed":
                    item = payload.get("item", {})
                    if (payload.get("turn_id") == turn and item.get("type") == "SubAgentActivity"
                            and item.get("kind") == "started"):
                        started[item.get("id")] = item
                elif row.get("type") == "response_item" and payload.get("type") == "function_call_output":
                    if payload.get("internal_chat_message_metadata_passthrough", {}).get("turn_id") == turn:
                        outputs.add(payload.get("call_id"))
        matches = [(call_id, started[call_id]) for call_id in calls if call_id in started and call_id in outputs]
        if len(matches) != 1:
            if matches:
                state["receipt_status"] = "manual_transcript_ambiguous"
            return
        call_id, activity = matches[0]
        child_id, agent_path = activity.get("agent_thread_id"), activity.get("agent_path")
        db = sqlite3.connect((self.home / "state_5.sqlite").as_uri() + "?mode=ro", uri=True)
        db.row_factory = sqlite3.Row
        try:
            rows = db.execute("SELECT id,rollout_path,source,agent_path,created_at FROM threads WHERE id=? AND agent_path=?",
                              (child_id, agent_path)).fetchall()
        finally:
            db.close()
        if len(rows) != 1:
            state["receipt_status"] = "manual_child_identity_unknown"
            return
        row = rows[0]
        try:
            source = json.loads(row["source"])
        except (TypeError, ValueError):
            return
        spawn = source.get("subagent", {}).get("thread_spawn", {}) if isinstance(source, dict) else {}
        if spawn.get("parent_thread_id") != thread or row["created_at"] < int(state.get("started_at", 0)):
            state["receipt_status"] = "manual_child_parent_mismatch"
            return
        _, ctx = transcript_info(row["rollout_path"])
        pair = {"model": ctx.get("model"), "effort": ctx.get("effort")} if ctx else None
        if pair != state["decision"].get("selected"):
            state["status"] = "blocked_model_mismatch"
            state["receipt_status"] = "model_mismatch"
            return
        state["actual"] = dict(pair, agent_id=row["id"], agent_path=row["agent_path"], turn_id=ctx["turn_id"],
                               evidence_ref=row["rollout_path"], parent_call_id=call_id,
                               evidence_mode="transcript_recovered_manual_cli")
        state["status"] = "delegation_observed"
        state["receipt_status"] = "verified_native_transcript_manual_cli"

    def refresh(self, state, thread):
        self.recover_manual_dispatch(state, thread)
        pending = state.get("pending")
        if not pending or not pending.get("native_result") or state.get("actual"):
            return
        result = pending["native_result"]
        db = sqlite3.connect((self.home / "state_5.sqlite").as_uri() + "?mode=ro", uri=True)
        db.row_factory = sqlite3.Row
        try:
            rows = db.execute("SELECT id,rollout_path,source,agent_path,created_at FROM threads WHERE id=? OR agent_path=?",
                              (result.get("agent_id", ""), result.get("task_name", ""))).fetchall()
        finally:
            db.close()
        candidates = []
        for row in rows:
            source = json.loads(row["source"])
            spawn = source.get("subagent", {}).get("thread_spawn", {}) if isinstance(source, dict) else {}
            if spawn.get("parent_thread_id") == thread and row["created_at"] >= int(pending["started_at"]):
                candidates.append(row)
        if len(candidates) != 1:
            state["receipt_status"] = "unknown_identity"
            return
        row = candidates[0]
        _, ctx = transcript_info(row["rollout_path"])
        if not ctx:
            state["receipt_status"] = "waiting_for_context"
            return
        pair = {"model": ctx["model"], "effort": ctx["effort"]}
        if pair != state["decision"]["selected"]:
            state["status"] = "blocked_model_mismatch"
            state["receipt_status"] = "model_mismatch"
            return
        state["actual"] = dict(pair, agent_id=row["id"], agent_path=row["agent_path"],
                               turn_id=ctx["turn_id"], evidence_ref=row["rollout_path"])
        state["status"] = "delegation_observed"
        state["receipt_status"] = "verified_native_context"

    def hook(self, payload):
        event = payload.get("hook_event_name")
        thread, turn, child = identity(payload)
        name = payload.get("tool_name", "")
        if child:
            if event == "PreToolUse" and (is_spawn(name) or "followup_task" in name):
                return deny("子代理仅执行已分配范围，禁止递归派工。")
            return {}
        self.db.execute("BEGIN IMMEDIATE")
        try:
            state = self.load(thread, turn) or self.initial(payload)
            state["hook_events"][event] = state["hook_events"].get(event, 0) + 1
            # Payload reception alone is not native trust or a full activation proof.
            state["activation"] = "hook_payload_received"
            if event == "UserPromptSubmit":
                prompt = payload.get("prompt")
                if isinstance(prompt, str):
                    state["user_prompt"] = prompt
                    role_state = self.role_state(state)
                    role_state["inferred"] = jobs.classify_prompt(prompt)
                    role_state["prompt_source"] = "native_user_prompt"
                suggested = self.role_state(state).get("inferred", [])
                result = context(event, f"Team Router {VERSION}：本轮先按工作阶段确认岗位，再独立评估执行模型。建议岗位 {suggested or ['none']}；岗位技能须有真实读取和结果/交接记录。调用工具前运行 {SCRIPT} describe；按其说明 assess。正常明确执行优先 Luna，常规判断 Terra，复杂 Sol，Astra 统筹。必须实际派工并核对回执，不能静默回退 Astra。短答无需工具无需派工。线程 {thread}，轮次 {turn}。")
            elif event == "PreToolUse":
                result = self.pre(state, payload, thread)
                if result.get("hookSpecificOutput", {}).get("permissionDecision") == "deny":
                    state["blocked_calls"] += 1
            elif event == "PostToolUse" and is_spawn(name):
                pending = state.get("pending")
                if pending and pending["tool_use_id"] == payload.get("tool_use_id"):
                    response = payload.get("tool_response")
                    if isinstance(response, str):
                        try:
                            response = json.loads(response)
                        except ValueError:
                            response = None
                    if isinstance(response, dict) and (response.get("error") or response.get("isError")):
                        pending["native_failure"] = True
                        state["status"] = "dispatch_failed"
                    elif isinstance(response, dict):
                        receipt = {k: response[k] for k in ("agent_id", "task_name") if isinstance(response.get(k), str)}
                        if receipt:
                            pending["native_result"] = receipt
                    self.refresh(state, thread)
                result = {}
            elif event == "Stop":
                if state.get("pending"):
                    self.refresh(state, thread)
                self.refresh_job_roles(state)
                delegated = state.get("decision", {}).get("execution_kind") == "delegate"
                gap = delegated and not state.get("actual")
                role_gaps = self.completion_role_gaps(state)
                state["audit_status"] = "missing_dispatch_receipt" if gap else ("observed" if state.get("actual") else "no_delegation_observed")
                state["job_role_audit_status"] = "incomplete" if role_gaps else "observed_or_not_required"
                # Never create another billed model turn just to enforce an audit.
                messages = []
                if gap:
                    messages.append("路由未验收：已选择委派，但尚无匹配的原生模型回执。不能声称自动派工已生效。")
                if role_gaps:
                    messages.append("岗位未验收：" + encoded(role_gaps) + "；Stop 仅记录缺口，不自动续跑。")
                result = {"systemMessage": " ".join(messages)} if messages else {}
            else:
                result = {}
            self.save(thread, turn, state)
            self.db.commit()
            return result
        except Exception:
            self.db.rollback()
            raise

    def pre(self, state, payload, thread):
        if bootstrap(payload):
            return {}
        # Let the user clarify/interrupt and let the agent reconcile existing work.
        name = payload.get("tool_name", "")
        if name in {"request_user_input", "request_user_input_async", "interrupt_agent", "list_agents", "wait_agent", "send_message",
                    "functions.request_user_input_async", "collaboration.interrupt_agent", "collaboration.list_agents",
                    "collaboration.wait_agent", "collaboration.send_message"}:
            return {}
        decision = state.get("decision")
        if not decision:
            return deny(f"尚未评估本轮岗位和执行模型。线程 {thread}，轮次 {payload.get('turn_id')}。先使用 Python 运行 {SCRIPT} describe，再 assess；明确的 role-read 只读入口可先读取技能。")
        if state.get("scope_bypass"):
            return {}
        if decision["status"] != "planned":
            return deny("路由阻塞：" + decision["reason"] + "。先解决已记录原因；不可静默回退高价主模型。")
        if decision["execution_kind"] == "delegate":
            if is_spawn(name):
                if state.get("pending") or state.get("actual"):
                    return deny("该阶段已发起委派。读取 status 核对原调用；禁止重复派工。")
                args = payload.get("tool_input") or {}
                if (args.get("agent_type") != state["selected_role"] or args.get("fork_turns") != "none"
                        or "model" in args or "reasoning_effort" in args or args.get("task_name") != state["task_name"]):
                    return deny(f"本阶段须使用角色 {state['selected_role']}，task_name={state['task_name']}，fork_turns=none；不要覆盖固定角色模型。")
                if not payload.get("tool_use_id"):
                    return deny("缺少原生 tool_use_id，无法防止重复委派。")
                state["pending"] = {"tool_use_id": payload["tool_use_id"], "started_at": time.time()}
                return {}
            self.refresh(state, thread)
            if not state.get("actual"):
                return deny("应委派的执行尚无匹配原生回执。请实际调用选定子代理，随后运行 execution_gate.py status 核验；不要由主模型接手执行。")
        elif is_spawn(name):
            return deny("当前阶段路由为直接执行；新增委派应另建有范围和模型选择的阶段。")
        gaps = self.role_gaps(state)
        if gaps:
            return deny("本阶段岗位技能尚无真实读取/介入证据：" + encoded(gaps)
                        + f"。运行 {SCRIPT} role-read --thread-id {thread} --turn-id {payload.get('turn_id')} --role ROLE；随后 status 会自动核对 transcript。")
        if decision.get("reason") == "tiny_direct" and state["observed_tool_calls"] >= 2:
            return deny("小任务直接执行已达到 2 次工具调用；任务超出微小操作范围，请重新评估正常执行阶段。")
        state["observed_tool_calls"] += 1
        return {}


def describe():
    return {"version": VERSION, "commands": ["assess --thread-id ID --turn-id ID --json 'JSON'", "status --thread-id ID --turn-id ID",
                                              "role-read --thread-id ID --turn-id ID --role development [--skill oneos-dev-delivery]",
                                              "role-confirm --thread-id ID --turn-id ID --role development",
                                              "role-status --thread-id ID --turn-id ID",
                                              "role-result --thread-id ID --turn-id ID --json 'JSON'",
                                              "role-handoff --thread-id ID --turn-id ID --json 'JSON'",
                                              "retry --thread-id ID --turn-id ID (only after explicit native dispatch failure; once)"],
            "assessment": {"domain": "development", "kind": "implementation", "clarity": "clear", "judgment": "low",
                           "impact": "local", "risk": "low", "verifiability": "testable", "execution_size": "normal",
                           "constraints_ready": True, "authorized": True, "independent": True,
                           "parent_work": "填写同时可完成的真实独立工作；没有则留空，不可编造",
                           "reason": "填写本阶段目标及验收；不能把业务执行笼统归为统筹",
                           "available_roles": ["team_luna_executor"],
                           "prompt": "可选；原生 UserPromptSubmit 已记录时必须完全相同",
                           "job_roles": ["development"],
                           "job_role_skills": {"development": "oneos-dev-delivery"},
                           "job_role_exclusions": {},
                           "task_scope": {"task_type": "development", "created_at": 0,
                                          "gate_effective_at": 0, "parent_task_id": "root-id",
                                          "parent_task_type": "requirement", "parent_created_at": 0}},
            "role_result_example": {"role": "development", "summary": "完成运行时修复并通过回归",
                                    "evidence": [{"kind": "file", "path": "/absolute/path/to/result-or-test-log"}]},
            "role_handoff_example": {"role": "development", "disposition": "handed_off", "next_role": "qa",
                                     "boundary": "只验证本次路由运行时改动", "artifacts": [{"kind": "file", "path": "/absolute/path/to/artifact"}],
                                     "unresolved": [], "acceptance": ["四类、混合、否定和文档对照通过"]},
            "instructions": "先按阶段确定 product/ux/development/qa，再独立选择模型。原生 prompt 只作建议；job_roles 可补齐，job_role_exclusions 必须逐项说明语义误判，不能静默漏岗。真实读取可由 role-read 完成，后续 status/pre 自动从 transcript 配对确认；role-confirm 是修复入口。只列出当前工具可用模型角色。Astra/max 是统筹模型，不等于岗位或执行也用 Astra。委派按返回角色和 task_name 使用 fork_turns=none；父任务同时做 parent_work，验收子代理产物。小于等于 2 次工具调用的微小工作可选 tiny。CLI 不调用模型；Stop 只审计，不续跑。缺少 hooks 信任时仅 CLI 生效，不能声称原生门禁已启用。"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["hook", "describe", "assess", "status", "retry", "role-read",
                                                   "role-confirm", "role-status", "role-result", "role-handoff"])
    parser.add_argument("--codex-home", default=os.environ.get("CODEX_HOME", str(Path.home() / ".codex")))
    parser.add_argument("--thread-id")
    parser.add_argument("--turn-id")
    parser.add_argument("--json")
    parser.add_argument("--role", choices=jobs.ROLE_ORDER)
    parser.add_argument("--skill")
    args = parser.parse_args()
    if args.command == "describe":
        print(encoded(describe()))
        return
    payload = {}
    try:
        gate = Gate(args.codex_home)
        if args.command == "hook":
            payload = json.load(sys.stdin)
            result = gate.hook(payload)
        elif not args.thread_id or not args.turn_id:
            raise ValueError("--thread-id and --turn-id required")
        elif args.command == "assess":
            result = gate.assess(args.thread_id, args.turn_id, json.loads(args.json or "{}"))
        elif args.command == "retry":
            result = gate.retry(args.thread_id, args.turn_id)
        elif args.command == "role-read":
            if not args.role:
                raise ValueError("--role required")
            result = gate.role_read(args.thread_id, args.turn_id, args.role, args.skill)
        elif args.command == "role-confirm":
            if not args.role:
                raise ValueError("--role required")
            result = gate.role_confirm(args.thread_id, args.turn_id, args.role)
        elif args.command == "role-result":
            result = gate.role_result(args.thread_id, args.turn_id, json.loads(args.json or "{}"))
        elif args.command == "role-handoff":
            result = gate.role_handoff(args.thread_id, args.turn_id, json.loads(args.json or "{}"))
        elif args.command == "role-status":
            with gate.db:
                state = gate.load_or_native(args.thread_id, args.turn_id)
                gate.refresh(state, args.thread_id)
                gate.refresh_job_roles(state)
                gate.save(args.thread_id, args.turn_id, state)
                result = gate.public_job_roles(state)
        else:
            with gate.db:
                state = gate.load(args.thread_id, args.turn_id)
                if not state:
                    raise ValueError("no assessment for this exact turn")
                gate.refresh(state, args.thread_id)
                gate.refresh_job_roles(state)
                gate.save(args.thread_id, args.turn_id, state)
                result = gate.public(state)
        print(encoded(result))
    except (ValueError, OSError, sqlite3.Error, router.RouterError, KeyError) as exc:
        message = "路由门禁无法核验：" + str(exc)[:220]
        if args.command == "hook":
            print(encoded(deny(message) if payload.get("hook_event_name") == "PreToolUse" else {"systemMessage": message}))
        else:
            print(message, file=sys.stderr)
            raise SystemExit(2)


if __name__ == "__main__":
    main()
