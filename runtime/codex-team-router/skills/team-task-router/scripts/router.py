#!/usr/bin/env python3
"""Local decision, lifecycle, metering, and feedback ledger for team routing.

This module never invokes a model. Runtime receipts are caller supplied evidence.
"""

from __future__ import annotations

import argparse
from decimal import Decimal, InvalidOperation
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import sys
from typing import Any


MODELS = ("gpt-5.6-luna", "gpt-5.6-terra", "gpt-5.6-sol", "gpt-6-astra")
MODEL_RANK = {model: index for index, model in enumerate(MODELS)}
EFFORTS = {
    "gpt-5.6-luna": ("low", "medium", "high", "xhigh", "max"),
    "gpt-5.6-terra": ("low", "medium", "high", "xhigh", "max", "ultra"),
    "gpt-5.6-sol": ("low", "medium", "high", "xhigh", "max", "ultra"),
    "gpt-6-astra": ("low", "medium", "high", "xhigh", "max", "ultra"),
}
EFFORT_RANK = {name: index for index, name in enumerate(("low", "medium", "high", "xhigh", "max", "ultra"))}
RATE_VERSION = "codex-standard-2026-09-10"
RATES = {
    "gpt-5.6-luna": (Decimal("5"), Decimal("0.5"), Decimal("30")),
    "gpt-5.6-terra": (Decimal("50"), Decimal("5"), Decimal("300")),
    "gpt-5.6-sol": (Decimal("100"), Decimal("10"), Decimal("500")),
    "gpt-6-astra": (Decimal("250"), Decimal("25"), Decimal("1250")),
}

REQUIRED_CARD_FIELDS = {
    "task_id", "phase_id", "input_revision", "rules_revision", "scope", "pattern",
    "domain", "kind", "clarity", "judgment", "impact", "risk", "verifiability",
    "execution_size", "constraints_ready", "authorized", "independent", "parent_has_work",
    "current", "available",
}
OPTIONAL_CARD_FIELDS = {
    "requested", "estimates", "approved_fallbacks", "budget_credits", "capability_failure",
}
ENUMS = {
    "domain": {"product", "development", "testing", "general"},
    "kind": {"mechanical", "implementation", "analysis", "review", "coordination"},
    "clarity": {"clear", "partial", "unclear"},
    "judgment": {"low", "routine", "complex", "exceptional"},
    "impact": {"local", "cross_module", "cross_service"},
    "risk": {"low", "medium", "high"},
    "verifiability": {"deterministic", "testable", "uncertain"},
    "execution_size": {"tiny", "normal", "large"},
}
QUALITY_CAUSES = {"wrong_result", "missed_constraint", "capability"}
FEEDBACK_CAUSES = QUALITY_CAUSES | {
    "requirement_change", "preference_change", "environment", "tool_failure", "unknown",
}


class RouterError(Exception):
    def __init__(self, message: str, code: str = "invalid_request") -> None:
        super().__init__(message)
        self.code = code


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _fingerprint(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _id(prefix: str, value: Any) -> str:
    return f"{prefix}-{_fingerprint(value)[:20]}"


def _require_object(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise RouterError(f"{name} must be an object")
    return value


def _exact_fields(value: dict[str, Any], allowed: set[str], required: set[str], name: str) -> None:
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise RouterError(f"unknown field in {name}: {unknown[0]}")
    missing = sorted(required - set(value))
    if missing:
        raise RouterError(f"missing required field in {name}: {missing[0]}")


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RouterError(f"{name} must be a non-empty string")
    return value


def _boolean(value: Any, name: str) -> bool:
    if not isinstance(value, bool):
        raise RouterError(f"{name} must be boolean")
    return value


def _number(value: Any, name: str, nullable: bool = False) -> Decimal | None:
    if value is None and nullable:
        return None
    if isinstance(value, bool):
        raise RouterError(f"{name} must be a finite nonnegative number")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise RouterError(f"{name} must be a finite nonnegative number") from None
    if not result.is_finite() or result < 0:
        raise RouterError(f"{name} must be a finite nonnegative number")
    return result


def _count(value: Any, name: str, nullable: bool = True) -> int | None:
    if value is None and nullable:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise RouterError(f"{name} must be a nonnegative integer or null")
    return value


def _validate_pair(value: Any, name: str) -> dict[str, str]:
    pair = _require_object(value, name)
    _exact_fields(pair, {"model", "effort"}, {"model", "effort"}, name)
    model = _text(pair["model"], f"{name}.model")
    effort = _text(pair["effort"], f"{name}.effort")
    if model not in MODELS:
        raise RouterError(f"unsupported model in {name}: {model}")
    if effort not in EFFORTS[model]:
        raise RouterError(f"unsupported effort for {model} in {name}: {effort}")
    return {"model": model, "effort": effort}


def _validate_available(value: Any) -> tuple[list[dict[str, Any]], dict[str, set[str]]]:
    if not isinstance(value, list):
        raise RouterError("available must be a list")
    normalized = []
    lookup: dict[str, set[str]] = {}
    for index, item in enumerate(value):
        entry = _require_object(item, f"available[{index}]")
        _exact_fields(entry, {"model", "efforts"}, {"model", "efforts"}, f"available[{index}]")
        model = _text(entry["model"], f"available[{index}].model")
        if model not in MODELS:
            raise RouterError(f"unsupported model in available: {model}")
        if model in lookup:
            raise RouterError(f"duplicate availability for model: {model}")
        efforts = entry["efforts"]
        if not isinstance(efforts, list) or not efforts:
            raise RouterError(f"available[{index}].efforts must be a non-empty list")
        if len(efforts) != len(set(efforts)):
            raise RouterError(f"duplicate effort in available for model: {model}")
        for effort in efforts:
            if effort not in EFFORTS[model]:
                raise RouterError(f"unsupported effort for {model} in available: {effort}")
        lookup[model] = set(efforts)
        normalized.append({"model": model, "efforts": list(efforts)})
    return normalized, lookup


def validate_card(raw: Any) -> dict[str, Any]:
    card = _require_object(raw, "decision card")
    _exact_fields(card, REQUIRED_CARD_FIELDS | OPTIONAL_CARD_FIELDS, REQUIRED_CARD_FIELDS, "decision card")
    normalized: dict[str, Any] = {}
    for name in ("task_id", "phase_id", "input_revision", "rules_revision", "scope", "pattern"):
        normalized[name] = _text(card[name], name)
    for name, choices in ENUMS.items():
        value = _text(card[name], name)
        if value not in choices:
            raise RouterError(f"invalid {name}: {value}")
        normalized[name] = value
    for name in ("constraints_ready", "authorized", "independent", "parent_has_work"):
        normalized[name] = _boolean(card[name], name)
    normalized["current"] = _validate_pair(card["current"], "current")
    normalized["available"], _ = _validate_available(card["available"])

    if "requested" in card:
        normalized["requested"] = _validate_pair(card["requested"], "requested")
    if "estimates" in card:
        estimates = _require_object(card["estimates"], "estimates")
        _exact_fields(estimates, {"direct_credits", "delegated_credits"}, {"direct_credits", "delegated_credits"}, "estimates")
        normalized["estimates"] = {
            "direct_credits": _json_number(_number(estimates["direct_credits"], "estimates.direct_credits", True)),
            "delegated_credits": _json_number(_number(estimates["delegated_credits"], "estimates.delegated_credits", True)),
        }
    if "approved_fallbacks" in card:
        fallbacks = card["approved_fallbacks"]
        if not isinstance(fallbacks, list):
            raise RouterError("approved_fallbacks must be a list")
        seen = set()
        normalized_fallbacks = []
        for index, raw_fallback in enumerate(fallbacks):
            fallback = _require_object(raw_fallback, f"approved_fallbacks[{index}]")
            _exact_fields(fallback, {"model", "effort", "estimated_credits"}, {"model", "effort", "estimated_credits"}, f"approved_fallbacks[{index}]")
            pair = _validate_pair({"model": fallback["model"], "effort": fallback["effort"]}, f"approved_fallbacks[{index}]")
            key = (pair["model"], pair["effort"])
            if key in seen:
                raise RouterError(f"duplicate approved fallback: {pair['model']}/{pair['effort']}")
            seen.add(key)
            pair["estimated_credits"] = _json_number(_number(fallback["estimated_credits"], f"approved_fallbacks[{index}].estimated_credits", True))
            normalized_fallbacks.append(pair)
        normalized["approved_fallbacks"] = normalized_fallbacks
    if "budget_credits" in card:
        normalized["budget_credits"] = _json_number(_number(card["budget_credits"], "budget_credits", True))
    if "capability_failure" in card:
        failure = _require_object(card["capability_failure"], "capability_failure")
        _exact_fields(failure, {"model", "effort", "evidence_ref"}, {"model", "effort", "evidence_ref"}, "capability_failure")
        pair = _validate_pair({"model": failure["model"], "effort": failure["effort"]}, "capability_failure")
        pair["evidence_ref"] = _text(failure["evidence_ref"], "capability_failure.evidence_ref")
        normalized["capability_failure"] = pair
    return normalized


def _json_number(value: Decimal | None) -> int | float | None:
    if value is None:
        return None
    if value == value.to_integral_value():
        return int(value)
    return float(value)


def _available(pair: dict[str, str], lookup: dict[str, set[str]]) -> bool:
    return pair["effort"] in lookup.get(pair["model"], set())


def _capable(pair: dict[str, str], floor: dict[str, str]) -> bool:
    return MODEL_RANK[pair["model"]] >= MODEL_RANK[floor["model"]] and EFFORT_RANK[pair["effort"]] >= EFFORT_RANK[floor["effort"]]


def _floor(card: dict[str, Any]) -> tuple[dict[str, str], str]:
    if card["kind"] == "coordination":
        if card["current"]["model"] == "gpt-6-astra":
            return {"model": "gpt-6-astra", "effort": card["current"]["effort"]}, "coordination_current_astra"
        return {"model": "gpt-5.6-sol", "effort": "medium"}, "coordination_default"
    if card["kind"] == "review":
        if card["risk"] == "high":
            return {"model": "gpt-5.6-sol", "effort": "high"}, "high_risk_review"
        return {"model": "gpt-5.6-terra", "effort": "medium"}, "separate_review"
    failure = card.get("capability_failure")
    if failure and failure["model"] == "gpt-5.6-sol":
        return {"model": "gpt-6-astra", "effort": "high"}, "confirmed_sol_capability_failure"
    if card["risk"] == "high" and card["judgment"] == "exceptional" and card["impact"] in {"cross_module", "cross_service"}:
        return {"model": "gpt-6-astra", "effort": "high"}, "exceptional_high_risk"
    if card["risk"] == "high" or card["impact"] == "cross_service" or card["judgment"] == "complex":
        return {"model": "gpt-5.6-sol", "effort": "high"}, "risk_or_complexity_floor"
    if card["kind"] == "mechanical" and card["clarity"] == "clear" and card["risk"] == "low" and card["verifiability"] == "deterministic":
        return {"model": "gpt-5.6-luna", "effort": "low"}, "mechanical_default"
    if card["kind"] == "implementation" and card["clarity"] == "clear" and card["impact"] == "local" and card["judgment"] == "low":
        return {"model": "gpt-5.6-luna", "effort": "medium"}, "frozen_implementation_default"
    if card["judgment"] == "routine":
        return {"model": "gpt-5.6-terra", "effort": "medium"}, "routine_judgment_default"
    return {"model": "gpt-5.6-sol", "effort": "high"}, "uncertain_analysis_default"


def decide(card: dict[str, Any]) -> dict[str, Any]:
    current = card["current"]
    _, availability = _validate_available(card["available"])
    base = {
        "task_id": card["task_id"], "phase_id": card["phase_id"],
        "input_revision": card["input_revision"], "rules_revision": card["rules_revision"],
        "scope": card["scope"], "pattern": card["pattern"],
        "current": current, "actual": current, "desired": None, "selected": None,
        "execution_kind": None, "independent_review_required": card["kind"] == "implementation" and card["risk"] == "high",
        "estimates": card.get("estimates", {"direct_credits": None, "delegated_credits": None}),
    }
    if not card["authorized"]:
        return {**base, "status": "blocked", "reason": "authorization_required"}
    if not card["constraints_ready"]:
        return {**base, "status": "blocked", "reason": "constraints_not_ready"}
    if card["clarity"] == "unclear":
        return {**base, "status": "blocked", "reason": "requirements_unclear"}

    floor, reason = _floor(card)
    requested = card.get("requested")
    target = requested or floor
    base["desired"] = target

    if requested:
        if not _capable(requested, floor):
            return {**base, "status": "blocked", "reason": "capability_floor"}
        if not _available(requested, availability):
            return {**base, "status": "blocked", "reason": "runtime_change_required"}
        estimate_key = "direct_credits" if requested == current else "delegated_credits"
        estimate = card.get("estimates", {}).get(estimate_key)
        budget = card.get("budget_credits")
        if budget is not None and estimate is not None and Decimal(str(estimate)) > Decimal(str(budget)):
            return {**base, "status": "blocked", "reason": "budget_exceeded"}
        reason = "explicit_request"
    else:
        if card["execution_size"] == "tiny" and card["risk"] == "low" and card["judgment"] == "low" and _capable(current, floor) and _available(current, availability):
            target, reason = current, "tiny_direct"
        else:
            estimates = card.get("estimates")
            if estimates and card["risk"] == "low" and _capable(current, floor) and _available(current, availability):
                direct = estimates["direct_credits"]
                delegated = estimates["delegated_credits"]
                if direct is not None and delegated is not None and Decimal(str(delegated)) >= Decimal(str(direct)):
                    target, reason = current, "delegation_not_cheaper"

        if not _available(target, availability):
            chosen = None
            budget = card.get("budget_credits")
            for fallback in card.get("approved_fallbacks", []):
                pair = {"model": fallback["model"], "effort": fallback["effort"]}
                estimate = fallback["estimated_credits"]
                if (_available(pair, availability) and _capable(pair, floor) and budget is not None
                        and estimate is not None and Decimal(str(estimate)) <= Decimal(str(budget))):
                    chosen = pair
                    break
            if chosen is None:
                return {**base, "status": "unavailable", "reason": "target_unavailable"}
            target, reason = chosen, "approved_fallback"

    if target == current:
        return {**base, "status": "planned", "reason": reason, "desired": target,
                "selected": target, "actual": current, "execution_kind": "self"}

    if not (card["independent"] and card["parent_has_work"]):
        return {**base, "status": "blocked", "reason": "delegation_required_runtime_limit", "desired": target}

    return {**base, "status": "planned", "reason": reason, "desired": target,
            "selected": target, "actual": None, "execution_kind": "delegate"}


def default_state_dir() -> Path:
    codex_home = os.environ.get("CODEX_HOME")
    root = Path(codex_home).expanduser() if codex_home else Path.home() / ".codex"
    return root / "state" / "team-task-router"


def connect(state_dir: str | Path, profile: str) -> sqlite3.Connection:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", profile):
        raise RouterError("profile must use letters, numbers, dot, underscore, or hyphen")
    directory = Path(state_dir).expanduser()
    directory.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(directory / f"{profile}.sqlite3", timeout=15, isolation_level=None)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA busy_timeout=15000")
    db.execute("PRAGMA foreign_keys=ON")
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS phases (
          id INTEGER PRIMARY KEY,
          decision_id TEXT NOT NULL UNIQUE,
          scope TEXT NOT NULL, task_id TEXT NOT NULL, phase_id TEXT NOT NULL,
          input_revision TEXT NOT NULL, rules_revision TEXT NOT NULL,
          pattern TEXT NOT NULL, kind TEXT NOT NULL,
          card_json TEXT NOT NULL, card_fingerprint TEXT NOT NULL,
          decision_json TEXT NOT NULL, status TEXT NOT NULL,
          selected_model TEXT, selected_effort TEXT,
          current_model TEXT NOT NULL, current_effort TEXT NOT NULL,
          execution_kind TEXT, retry_authorization_required INTEGER NOT NULL DEFAULT 0,
          UNIQUE(scope, task_id, phase_id, input_revision, rules_revision)
        );
        CREATE TABLE IF NOT EXISTS runs (
          run_id TEXT PRIMARY KEY, phase_row_id INTEGER NOT NULL REFERENCES phases(id),
          attempt INTEGER NOT NULL, status TEXT NOT NULL, execution_kind TEXT NOT NULL,
          expected_model TEXT NOT NULL, expected_effort TEXT NOT NULL,
          actual_model TEXT, actual_effort TEXT, actual_agent_id TEXT, actual_session_id TEXT,
          role TEXT, sandbox TEXT, bound INTEGER NOT NULL DEFAULT 0,
          start_evidence_ref TEXT NOT NULL, bind_receipt_json TEXT, bind_fingerprint TEXT,
          mismatch_receipt_json TEXT, mismatch_fingerprint TEXT, mismatch_receipt_id TEXT,
          verification_evidence_ref TEXT, finish_status TEXT, finish_evidence_ref TEXT,
          elapsed_ms INTEGER
        );
        CREATE TABLE IF NOT EXISTS usage_samples (
          sample_id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(run_id),
          payload_json TEXT NOT NULL, fingerprint TEXT NOT NULL,
          input_tokens INTEGER, cached_input_tokens INTEGER, output_tokens INTEGER,
          reasoning_tokens INTEGER, rate_version TEXT NOT NULL, speed_mode TEXT NOT NULL,
          estimated_credits TEXT, cost_status TEXT NOT NULL, elapsed_ms INTEGER,
          parent_run_id TEXT, coverage_complete INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS replan_audit (
          replan_id TEXT PRIMARY KEY, phase_row_id INTEGER NOT NULL REFERENCES phases(id),
          fingerprint TEXT NOT NULL, payload_json TEXT NOT NULL,
          previous_decision_id TEXT NOT NULL, new_decision_id TEXT NOT NULL,
          evidence_ref TEXT NOT NULL, result_json TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS feedback_events (
          event_id TEXT NOT NULL UNIQUE, run_id TEXT NOT NULL REFERENCES runs(run_id),
          task_id TEXT NOT NULL, scope TEXT NOT NULL, pattern TEXT NOT NULL,
          rules_revision TEXT NOT NULL, actual_model TEXT NOT NULL, actual_effort TEXT NOT NULL,
          cause TEXT NOT NULL, source TEXT NOT NULL, user_correction INTEGER NOT NULL,
          accepted INTEGER NOT NULL, verified INTEGER NOT NULL, evidence_ref TEXT NOT NULL,
          payload_json TEXT NOT NULL, fingerprint TEXT NOT NULL,
          created_order INTEGER PRIMARY KEY AUTOINCREMENT
        );
        """
    )
    columns = {row["name"] for row in db.execute("PRAGMA table_info(phases)")}
    if "retry_authorization_required" not in columns:
        db.execute("ALTER TABLE phases ADD COLUMN retry_authorization_required INTEGER NOT NULL DEFAULT 0")
    run_columns = {row["name"] for row in db.execute("PRAGMA table_info(runs)")}
    for name in ("mismatch_receipt_json", "mismatch_fingerprint", "mismatch_receipt_id"):
        if name not in run_columns:
            db.execute(f"ALTER TABLE runs ADD COLUMN {name} TEXT")
    usage_columns = {row["name"] for row in db.execute("PRAGMA table_info(usage_samples)")}
    if "coverage_complete" not in usage_columns:
        db.execute("ALTER TABLE usage_samples ADD COLUMN coverage_complete INTEGER NOT NULL DEFAULT 0")
    return db


def _phase_key(payload: dict[str, Any], allowed_extra: set[str] | None = None) -> tuple[Any, ...]:
    allowed = {"task_id", "phase_id", "input_revision", "rules_revision", "scope"} | (allowed_extra or set())
    _exact_fields(payload, allowed, {"task_id", "phase_id", "input_revision", "rules_revision", "scope"}, "payload")
    return tuple(_text(payload[name], name) for name in ("scope", "task_id", "phase_id", "input_revision", "rules_revision"))


def _get_phase(db: sqlite3.Connection, key: tuple[Any, ...]) -> sqlite3.Row:
    row = db.execute(
        "SELECT * FROM phases WHERE scope=? AND task_id=? AND phase_id=? AND input_revision=? AND rules_revision=?", key
    ).fetchone()
    if row is None:
        raise RouterError("phase not found", "not_found")
    return row


def _route(db: sqlite3.Connection | None, card: dict[str, Any], dry_run: bool) -> dict[str, Any]:
    decision = decide(card)
    decision_id = _id("decision", [card[name] for name in ("scope", "task_id", "phase_id", "input_revision", "rules_revision")])
    decision.update({"decision_id": decision_id, "phase_status": decision["status"], "replayed": False, "dry_run": dry_run})
    if dry_run:
        return decision
    assert db is not None
    fingerprint = _fingerprint(card)
    key = (card["scope"], card["task_id"], card["phase_id"], card["input_revision"], card["rules_revision"])
    db.execute("BEGIN IMMEDIATE")
    try:
        existing = db.execute(
            "SELECT * FROM phases WHERE scope=? AND task_id=? AND phase_id=? AND input_revision=? AND rules_revision=?", key
        ).fetchone()
        if existing:
            if existing["card_fingerprint"] != fingerprint:
                raise RouterError("decision card conflict for existing phase key", "conflict")
            replay = json.loads(existing["decision_json"])
            replay.update({"replayed": True, "dry_run": False, "phase_status": existing["status"]})
            db.execute("COMMIT")
            return replay
        db.execute(
            """INSERT INTO phases
               (decision_id,scope,task_id,phase_id,input_revision,rules_revision,pattern,kind,
                card_json,card_fingerprint,decision_json,status,selected_model,selected_effort,
                current_model,current_effort,execution_kind)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (decision_id, *key, card["pattern"], card["kind"], _canonical(card), fingerprint,
             _canonical(decision), decision["status"],
             decision["selected"]["model"] if decision["selected"] else None,
             decision["selected"]["effort"] if decision["selected"] else None,
             card["current"]["model"], card["current"]["effort"], decision["execution_kind"]),
        )
        db.execute("COMMIT")
        return decision
    except Exception:
        db.execute("ROLLBACK")
        raise


def _start(db: sqlite3.Connection, payload: dict[str, Any]) -> dict[str, Any]:
    allowed = {"run_id", "execution_kind", "evidence_ref", "retry_authorized"}
    key = _phase_key(payload, allowed)
    run_id = _text(payload.get("run_id"), "run_id")
    execution_kind = payload.get("execution_kind")
    if execution_kind not in {"self", "delegate"}:
        raise RouterError("execution_kind must be self or delegate")
    evidence_ref = _text(payload.get("evidence_ref"), "evidence_ref")
    retry_authorized = payload.get("retry_authorized", False)
    _boolean(retry_authorized, "retry_authorized")
    db.execute("BEGIN IMMEDIATE")
    try:
        phase = _get_phase(db, key)
        if phase["status"] not in {"planned", "failed"}:
            raise RouterError(f"phase already claimed with status {phase['status']}", "already_claimed")
        if phase["status"] == "failed" or phase["retry_authorization_required"]:
            if not retry_authorized:
                raise RouterError("failed run requires explicit retry authorization", "retry_authorization_required")
        if not phase["selected_model"] or not phase["selected_effort"] or not phase["execution_kind"]:
            raise RouterError("phase has no executable selected capability", "not_executable")
        if phase["execution_kind"] != execution_kind:
            raise RouterError("execution_kind does not match route decision", "execution_mismatch")
        existing_run = db.execute("SELECT 1 FROM runs WHERE run_id=?", (run_id,)).fetchone()
        if existing_run:
            raise RouterError("run_id already exists", "conflict")
        attempt = db.execute("SELECT COUNT(*) AS count FROM runs WHERE phase_row_id=?", (phase["id"],)).fetchone()["count"] + 1
        role = "coordinator" if phase["kind"] == "coordination" else "reviewer" if phase["kind"] == "review" else "executor"
        status, bound = "dispatching", 0
        actual_model = actual_effort = None
        db.execute(
            """INSERT INTO runs
               (run_id,phase_row_id,attempt,status,execution_kind,expected_model,expected_effort,
                actual_model,actual_effort,role,bound,start_evidence_ref)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (run_id, phase["id"], attempt, status, execution_kind, phase["selected_model"],
             phase["selected_effort"], actual_model, actual_effort, role, bound, evidence_ref),
        )
        db.execute("UPDATE phases SET status=?,retry_authorization_required=0 WHERE id=?", (status, phase["id"]))
        db.execute("COMMIT")
        return {"run_id": run_id, "status": status, "attempt": attempt, "execution_kind": execution_kind,
                "native_execution_transactional": False, "dispatch_reconciliation_required": True}
    except Exception:
        db.execute("ROLLBACK")
        raise


def _replan(db: sqlite3.Connection, payload: dict[str, Any]) -> dict[str, Any]:
    allowed = {"task_id", "phase_id", "input_revision", "rules_revision", "scope", "card", "evidence_ref"}
    _exact_fields(payload, allowed, allowed, "replan payload")
    key = tuple(_text(payload[name], name) for name in ("scope", "task_id", "phase_id", "input_revision", "rules_revision"))
    evidence = _text(payload["evidence_ref"], "evidence_ref")
    card = validate_card(payload["card"])
    if key != tuple(card[name] for name in ("scope", "task_id", "phase_id", "input_revision", "rules_revision")):
        raise RouterError("replan card phase key does not match payload")
    normalized_payload = {"scope": key[0], "task_id": key[1], "phase_id": key[2],
                          "input_revision": key[3], "rules_revision": key[4],
                          "card": card, "evidence_ref": evidence}
    fingerprint = _fingerprint(normalized_payload)
    replan_id = _id("replan", normalized_payload)
    mutable = {"current", "available", "requested", "estimates", "approved_fallbacks", "budget_credits",
               "capability_failure", "authorized", "constraints_ready", "independent", "parent_has_work"}
    db.execute("BEGIN IMMEDIATE")
    try:
        existing = db.execute("SELECT * FROM replan_audit WHERE replan_id=?", (replan_id,)).fetchone()
        if existing:
            if existing["fingerprint"] != fingerprint:
                raise RouterError("conflicting replan receipt", "conflict")
            result = json.loads(existing["result_json"])
            result["replayed"] = True
            db.execute("COMMIT")
            return result
        phase = _get_phase(db, key)
        if phase["status"] in {"dispatching", "running", "verifying", "completed"}:
            raise RouterError("active or completed phase cannot be replanned", "invalid_transition")
        runs = db.execute("SELECT status FROM runs WHERE phase_row_id=?", (phase["id"],)).fetchall()
        if any(run["status"] not in {"failed", "blocked", "cancelled"} for run in runs):
            raise RouterError("active or completed run prevents replan", "invalid_transition")
        old_card = json.loads(phase["card_json"])
        old_decision = json.loads(phase["decision_json"])
        for name in REQUIRED_CARD_FIELDS | OPTIONAL_CARD_FIELDS:
            if name not in mutable and old_card.get(name) != card.get(name):
                raise RouterError(f"immutable business field changed during replan: {name}", "conflict")
        if old_card == card:
            raise RouterError("replan card has no runtime condition changes", "conflict")
        decision = decide(card)
        decision_id = _id("decision", {"previous": phase["decision_id"], "replan": replan_id, "card": card})
        decision.update({"decision_id": decision_id, "phase_status": decision["status"],
                         "replayed": False, "dry_run": False, "replan_id": replan_id,
                         "previous_decision_id": phase["decision_id"]})
        audit_payload = {**normalized_payload, "previous_card": old_card,
                         "previous_decision": old_decision}
        db.execute(
            """UPDATE phases SET decision_id=?,pattern=?,kind=?,card_json=?,card_fingerprint=?,decision_json=?,
               status=?,selected_model=?,selected_effort=?,current_model=?,current_effort=?,execution_kind=?,
               retry_authorization_required=? WHERE id=?""",
            (decision_id, card["pattern"], card["kind"], _canonical(card), _fingerprint(card), _canonical(decision),
             decision["status"], decision["selected"]["model"] if decision["selected"] else None,
             decision["selected"]["effort"] if decision["selected"] else None,
             card["current"]["model"], card["current"]["effort"], decision["execution_kind"], int(bool(runs)), phase["id"]),
        )
        db.execute(
            """INSERT INTO replan_audit
               (replan_id,phase_row_id,fingerprint,payload_json,previous_decision_id,new_decision_id,evidence_ref,result_json)
               VALUES (?,?,?,?,?,?,?,?)""",
            (replan_id, phase["id"], fingerprint, _canonical(audit_payload), phase["decision_id"],
             decision_id, evidence, _canonical(decision)),
        )
        db.execute("COMMIT")
        return decision
    except Exception:
        db.execute("ROLLBACK")
        raise


def _run(db: sqlite3.Connection, run_id: str) -> sqlite3.Row:
    row = db.execute(
        "SELECT r.*, p.scope, p.task_id, p.phase_id, p.input_revision, p.rules_revision, p.pattern, p.kind, p.id AS phase_id_row "
        "FROM runs r JOIN phases p ON p.id=r.phase_row_id WHERE r.run_id=?", (run_id,)
    ).fetchone()
    if row is None:
        raise RouterError("run not found", "not_found")
    return row


def _bind(db: sqlite3.Connection, payload: dict[str, Any]) -> dict[str, Any]:
    allowed = {"run_id", "actual_agent_id", "actual_session_id", "model", "effort", "role", "evidence_ref", "sandbox"}
    _exact_fields(payload, allowed, allowed, "bind payload")
    run_id = _text(payload["run_id"], "run_id")
    pair = _validate_pair({"model": payload["model"], "effort": payload["effort"]}, "observed execution")
    for name in ("actual_agent_id", "actual_session_id", "evidence_ref"):
        _text(payload[name], name)
    if payload["role"] not in {"coordinator", "executor", "reviewer"}:
        raise RouterError("role must be coordinator, executor, or reviewer")
    if payload["sandbox"] is not None and not isinstance(payload["sandbox"], str):
        raise RouterError("sandbox must be string or null")
    fingerprint = _fingerprint(payload)
    db.execute("BEGIN IMMEDIATE")
    try:
        run = _run(db, run_id)
        if run["bind_fingerprint"]:
            if run["bind_fingerprint"] == fingerprint:
                db.execute("COMMIT")
                return {"run_id": run_id, "status": run["status"], "replayed": True,
                        "actual": {"model": run["actual_model"], "effort": run["actual_effort"]}}
            raise RouterError("conflicting receipt for bound run", "conflict")
        observed = pair
        expected = {"model": run["expected_model"], "effort": run["expected_effort"]}
        if run["mismatch_fingerprint"]:
            if run["mismatch_fingerprint"] == fingerprint:
                db.execute("COMMIT")
                return {"run_id": run_id, "status": "reconciliation_required", "run_status": "dispatching",
                        "expected": expected, "observed": observed, "replayed": True,
                        "mismatch_receipt_id": run["mismatch_receipt_id"],
                        "receipt_attestation": "caller_supplied"}
            raise RouterError("conflicting mismatch receipt requires reconciliation", "conflict")
        if run["status"] != "dispatching":
            raise RouterError("only a dispatching run can be bound", "invalid_transition")
        if observed != expected:
            receipt_id = _id("mismatch", payload)
            db.execute(
                "UPDATE runs SET mismatch_receipt_json=?,mismatch_fingerprint=?,mismatch_receipt_id=? WHERE run_id=?",
                (_canonical(payload), fingerprint, receipt_id, run_id),
            )
            db.execute("COMMIT")
            return {"run_id": run_id, "status": "reconciliation_required", "run_status": "dispatching",
                    "expected": expected, "observed": observed, "replayed": False,
                    "mismatch_receipt_id": receipt_id, "receipt_attestation": "caller_supplied"}
        db.execute(
            """UPDATE runs SET status='running', actual_model=?,actual_effort=?,actual_agent_id=?,
               actual_session_id=?,role=?,sandbox=?,bound=1,bind_receipt_json=?,bind_fingerprint=? WHERE run_id=?""",
            (pair["model"], pair["effort"], payload["actual_agent_id"], payload["actual_session_id"],
             payload["role"], payload["sandbox"], _canonical(payload), fingerprint, run_id),
        )
        db.execute("UPDATE phases SET status='running' WHERE id=?", (run["phase_row_id"],))
        db.execute("COMMIT")
        return {"run_id": run_id, "status": "running", "replayed": False, "actual": pair,
                "sandbox": payload["sandbox"], "receipt_attestation": "caller_supplied"}
    except Exception:
        db.execute("ROLLBACK")
        raise


def _verify(db: sqlite3.Connection, payload: dict[str, Any]) -> dict[str, Any]:
    _exact_fields(payload, {"run_id", "evidence_ref"}, {"run_id", "evidence_ref"}, "verify payload")
    run_id = _text(payload["run_id"], "run_id")
    evidence = _text(payload["evidence_ref"], "evidence_ref")
    db.execute("BEGIN IMMEDIATE")
    try:
        run = _run(db, run_id)
        if run["status"] == "verifying":
            if run["verification_evidence_ref"] == evidence:
                db.execute("COMMIT")
                return {"run_id": run_id, "status": "verifying", "replayed": True}
            raise RouterError("conflicting verification evidence", "conflict")
        if not run["bound"]:
            raise RouterError("run must be bound before verification", "invalid_transition")
        if run["status"] != "running":
            raise RouterError("verification requires a running bound run", "invalid_transition")
        db.execute("UPDATE runs SET status='verifying',verification_evidence_ref=? WHERE run_id=?", (evidence, run_id))
        db.execute("UPDATE phases SET status='verifying' WHERE id=?", (run["phase_row_id"],))
        db.execute("COMMIT")
        return {"run_id": run_id, "status": "verifying", "replayed": False, "evidence_ref": evidence}
    except Exception:
        db.execute("ROLLBACK")
        raise


def _finish(db: sqlite3.Connection, payload: dict[str, Any]) -> dict[str, Any]:
    allowed = {"run_id", "status", "evidence_ref", "elapsed_ms"}
    _exact_fields(payload, allowed, {"run_id", "status", "evidence_ref"}, "finish payload")
    run_id = _text(payload["run_id"], "run_id")
    status = payload["status"]
    if status not in {"completed", "failed", "blocked", "cancelled"}:
        raise RouterError("finish status must be completed, failed, blocked, or cancelled")
    evidence = _text(payload["evidence_ref"], "evidence_ref")
    elapsed = _count(payload.get("elapsed_ms"), "elapsed_ms")
    db.execute("BEGIN IMMEDIATE")
    try:
        run = _run(db, run_id)
        if run["finish_status"]:
            if run["finish_status"] == status and run["finish_evidence_ref"] == evidence and run["elapsed_ms"] == elapsed:
                db.execute("COMMIT")
                return {"run_id": run_id, "status": status, "replayed": True}
            raise RouterError("finished run cannot change outcome", "invalid_transition")
        if status == "completed" and (run["status"] != "verifying" or not run["verification_evidence_ref"]):
            raise RouterError("completed finish requires verification evidence", "verification_required")
        if status != "completed" and run["status"] not in {"dispatching", "running", "verifying"}:
            raise RouterError("run cannot finish from its current state", "invalid_transition")
        db.execute(
            "UPDATE runs SET status=?,finish_status=?,finish_evidence_ref=?,elapsed_ms=? WHERE run_id=?",
            (status, status, evidence, elapsed, run_id),
        )
        db.execute("UPDATE phases SET status=? WHERE id=?", (status, run["phase_row_id"]))
        db.execute("COMMIT")
        return {"run_id": run_id, "status": status, "replayed": False, "evidence_ref": evidence}
    except Exception:
        db.execute("ROLLBACK")
        raise


def _usage(db: sqlite3.Connection, payload: dict[str, Any]) -> dict[str, Any]:
    allowed = {"run_id", "sample_id", "input_tokens", "cached_input_tokens", "output_tokens",
               "reasoning_tokens", "includes_child_usage", "rate_version", "speed_mode", "elapsed_ms",
               "parent_run_id", "coverage_complete"}
    required = {"run_id", "sample_id", "includes_child_usage", "rate_version", "speed_mode"}
    _exact_fields(payload, allowed, required, "usage payload")
    payload = dict(payload)
    payload.setdefault("input_tokens", None)
    payload.setdefault("cached_input_tokens", None)
    payload.setdefault("output_tokens", None)
    payload.setdefault("reasoning_tokens", None)
    payload.setdefault("elapsed_ms", None)
    payload.setdefault("coverage_complete", False)
    run_id = _text(payload["run_id"], "run_id")
    sample_id = _text(payload["sample_id"], "sample_id")
    run = _run(db, run_id)
    if not run["bound"] or not run["actual_model"]:
        raise RouterError("usage requires a bound run", "invalid_transition")
    counts = {name: _count(payload[name], name) for name in ("input_tokens", "cached_input_tokens", "output_tokens", "reasoning_tokens")}
    if counts["cached_input_tokens"] is not None and counts["input_tokens"] is not None and counts["cached_input_tokens"] > counts["input_tokens"]:
        raise RouterError("cached_input_tokens cannot exceed input_tokens")
    if counts["reasoning_tokens"] is not None and counts["output_tokens"] is not None and counts["reasoning_tokens"] > counts["output_tokens"]:
        raise RouterError("reasoning_tokens cannot exceed output_tokens")
    if _boolean(payload["includes_child_usage"], "includes_child_usage"):
        raise RouterError("overlapping counters that include child usage are rejected")
    coverage_complete = _boolean(payload["coverage_complete"], "coverage_complete")
    rate_version = _text(payload["rate_version"], "rate_version")
    speed_mode = _text(payload["speed_mode"], "speed_mode")
    elapsed = _count(payload["elapsed_ms"], "elapsed_ms")
    parent_run_id = payload.get("parent_run_id")
    if parent_run_id is not None:
        _text(parent_run_id, "parent_run_id")
        if parent_run_id == run_id:
            raise RouterError("parent_run_id cannot equal run_id")
        _run(db, parent_run_id)
    fingerprint = _fingerprint(payload)
    existing = db.execute("SELECT * FROM usage_samples WHERE sample_id=?", (sample_id,)).fetchone()
    if existing:
        if existing["fingerprint"] != fingerprint:
            raise RouterError("conflicting sample for sample_id", "conflict")
        return _usage_result(existing, replayed=True)
    closed = db.execute("SELECT sample_id FROM usage_samples WHERE run_id=? AND coverage_complete=1", (run_id,)).fetchone()
    if closed:
        raise RouterError(f"usage coverage already closed by sample {closed['sample_id']}", "coverage_closed")
    if coverage_complete and run["status"] not in {"completed", "failed", "blocked", "cancelled"}:
        raise RouterError("coverage_complete requires a terminal run", "invalid_transition")

    missing = [name for name in ("input_tokens", "cached_input_tokens", "output_tokens") if counts[name] is None]
    cost: Decimal | None = None
    if missing:
        cost_status = "unknown_usage"
    elif rate_version != RATE_VERSION or (speed_mode != "standard" and not (run["actual_model"] == "gpt-6-astra" and speed_mode == "fast")):
        cost_status = "unsupported_rate_or_speed"
    else:
        new_input = counts["input_tokens"] - counts["cached_input_tokens"]
        new_rate, cached_rate, output_rate = RATES[run["actual_model"]]
        cost = (Decimal(new_input) * new_rate + Decimal(counts["cached_input_tokens"]) * cached_rate
                + Decimal(counts["output_tokens"]) * output_rate) / Decimal(1_000_000)
        if speed_mode == "fast":
            cost *= Decimal("2.5")
        cost_status = "estimated"
    db.execute(
        """INSERT INTO usage_samples
           (sample_id,run_id,payload_json,fingerprint,input_tokens,cached_input_tokens,output_tokens,
            reasoning_tokens,rate_version,speed_mode,estimated_credits,cost_status,elapsed_ms,parent_run_id,coverage_complete)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (sample_id, run_id, _canonical(payload), fingerprint, counts["input_tokens"], counts["cached_input_tokens"],
         counts["output_tokens"], counts["reasoning_tokens"], rate_version, speed_mode,
         _format_credits(cost), cost_status, elapsed, parent_run_id, int(coverage_complete)),
    )
    row = db.execute("SELECT * FROM usage_samples WHERE sample_id=?", (sample_id,)).fetchone()
    return _usage_result(row, replayed=False)


def _format_credits(value: Decimal | None) -> str | None:
    return None if value is None else format(value.quantize(Decimal("0.000001")), "f")


def _usage_result(row: sqlite3.Row, replayed: bool) -> dict[str, Any]:
    missing = [name for name in ("input_tokens", "cached_input_tokens", "output_tokens") if row[name] is None]
    return {"run_id": row["run_id"], "sample_id": row["sample_id"], "replayed": replayed,
            "input_tokens": row["input_tokens"], "cached_input_tokens": row["cached_input_tokens"],
            "output_tokens": row["output_tokens"], "reasoning_tokens": row["reasoning_tokens"],
            "rate_version": row["rate_version"], "speed_mode": row["speed_mode"],
            "estimated_credits": row["estimated_credits"], "cost_status": row["cost_status"],
            "missing_fields": missing, "coverage_complete": bool(row["coverage_complete"]),
            "amount_kind": "estimate_not_billed"}


def _summary(db: sqlite3.Connection, payload: dict[str, Any]) -> dict[str, Any]:
    _exact_fields(payload, {"scope", "task_id"}, {"scope", "task_id"}, "summary payload")
    scope, task_id = _text(payload["scope"], "scope"), _text(payload["task_id"], "task_id")
    runs = db.execute(
        """SELECT r.*,p.kind,p.pattern,p.rules_revision FROM runs r JOIN phases p ON p.id=r.phase_row_id
           WHERE p.scope=? AND p.task_id=? ORDER BY p.id,r.attempt""", (scope, task_id)
    ).fetchall()
    groups = {"coordinator": [], "executors": [], "retries": [], "reviewers": []}
    known_subtotal = Decimal("0")
    missing_usage = False
    for run in runs:
        samples = db.execute("SELECT * FROM usage_samples WHERE run_id=? ORDER BY rowid", (run["run_id"],)).fetchall()
        totals = {}
        for field in ("input_tokens", "cached_input_tokens", "output_tokens"):
            values = [sample[field] for sample in samples]
            totals[field] = sum(values) if values and all(value is not None for value in values) else None
        credits = [sample["estimated_credits"] for sample in samples]
        closed = any(bool(sample["coverage_complete"]) for sample in samples)
        terminal = run["status"] in {"completed", "failed", "blocked", "cancelled"}
        complete = (bool(samples) and closed and terminal and all(value is not None for value in credits)
                    and all(value is not None for value in totals.values()))
        subtotal = sum((Decimal(value) for value in credits if value is not None), Decimal("0"))
        known_subtotal += subtotal
        missing_usage = missing_usage or not complete
        item = {"run_id": run["run_id"], "attempt": run["attempt"], "status": run["status"],
                "actual": {"model": run["actual_model"], "effort": run["actual_effort"]} if run["actual_model"] else None,
                "known_tokens": totals, "known_credits_subtotal": _format_credits(subtotal),
                "complete_usage": complete, "coverage_closed": closed,
                "elapsed_ms": run["elapsed_ms"] if run["elapsed_ms"] is not None else sum((s["elapsed_ms"] or 0) for s in samples) or None}
        if run["role"] == "coordinator":
            groups["coordinator"].append(item)
        elif run["role"] == "reviewer":
            groups["reviewers"].append(item)
        elif run["attempt"] > 1:
            groups["retries"].append(item)
        else:
            groups["executors"].append(item)
    phase_rows = db.execute("SELECT kind,decision_json FROM phases WHERE scope=? AND task_id=?", (scope, task_id)).fetchall()
    missing_coverage = []
    if any(row["kind"] != "coordination" for row in phase_rows) and not groups["coordinator"]:
        missing_coverage.append("coordinator")
    if any(row["kind"] not in {"coordination", "review"} for row in phase_rows) and not groups["executors"]:
        missing_coverage.append("executor")
    if any(json.loads(row["decision_json"])["independent_review_required"] for row in phase_rows) and not groups["reviewers"]:
        missing_coverage.append("reviewer")
    if missing_usage:
        missing_coverage.append("complete_usage")
    complete = bool(runs) and not missing_coverage
    return {"scope": scope, "task_id": task_id, **groups,
            "known_credits_subtotal": _format_credits(known_subtotal),
            "total_task_credits": _format_credits(known_subtotal) if complete else None,
            "coverage": "complete" if complete else "partial", "missing_coverage": missing_coverage,
            "savings_percentage": None, "amount_kind": "estimate_not_billed"}


def _feedback(db: sqlite3.Connection, payload: dict[str, Any]) -> dict[str, Any]:
    allowed = {"event_id", "run_id", "evidence_ref", "cause", "source", "user_correction", "accepted", "verified"}
    _exact_fields(payload, allowed, allowed, "feedback payload")
    event_id, run_id = _text(payload["event_id"], "event_id"), _text(payload["run_id"], "run_id")
    evidence_ref = _text(payload["evidence_ref"], "evidence_ref")
    cause = payload["cause"]
    if cause not in FEEDBACK_CAUSES:
        raise RouterError(f"invalid feedback cause: {cause}")
    source = _text(payload["source"], "source")
    flags = {name: _boolean(payload[name], name) for name in ("user_correction", "accepted", "verified")}
    if source != "user" and (flags["user_correction"] or flags["accepted"]):
        raise RouterError("only explicit user feedback can mark user_correction or accepted")
    run = _run(db, run_id)
    if not run["bound"] or not run["actual_model"]:
        raise RouterError("feedback requires a bound run", "invalid_transition")
    fingerprint = _fingerprint(payload)
    existing = db.execute("SELECT * FROM feedback_events WHERE event_id=?", (event_id,)).fetchone()
    if existing:
        if existing["fingerprint"] != fingerprint:
            raise RouterError("conflicting feedback for event_id", "conflict")
        reassessment, tasks = _reassessment(db, existing["scope"], existing["pattern"], existing["rules_revision"], existing["actual_model"], existing["actual_effort"])
        return {"event_id": event_id, "status": "recorded", "replayed": True,
                "actual": {"model": existing["actual_model"], "effort": existing["actual_effort"]},
                "reassessment_required": reassessment, "recent_feedback_tasks": tasks}
    db.execute(
        """INSERT INTO feedback_events
           (event_id,run_id,task_id,scope,pattern,rules_revision,actual_model,actual_effort,cause,
            source,user_correction,accepted,verified,evidence_ref,payload_json,fingerprint)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (event_id, run_id, run["task_id"], run["scope"], run["pattern"], run["rules_revision"],
         run["actual_model"], run["actual_effort"], cause, source, int(flags["user_correction"]),
         int(flags["accepted"]), int(flags["verified"]), evidence_ref, _canonical(payload), fingerprint),
    )
    reassessment, tasks = _reassessment(db, run["scope"], run["pattern"], run["rules_revision"], run["actual_model"], run["actual_effort"])
    return {"event_id": event_id, "status": "recorded", "replayed": False,
            "actual": {"model": run["actual_model"], "effort": run["actual_effort"]},
            "reassessment_required": reassessment, "recent_feedback_tasks": tasks}


def _reassessment(db: sqlite3.Connection, scope: str, pattern: str, rules_revision: str, model: str, effort: str) -> tuple[bool, list[dict[str, Any]]]:
    rows = db.execute(
        """SELECT * FROM feedback_events WHERE scope=? AND pattern=? AND rules_revision=?
           AND actual_model=? AND actual_effort=? ORDER BY created_order DESC""",
        (scope, pattern, rules_revision, model, effort),
    ).fetchall()
    tasks_by_id: dict[str, dict[str, Any]] = {}
    task_order: list[str] = []
    for row in rows:
        quality = bool(row["user_correction"]) and row["cause"] in QUALITY_CAUSES
        task_id = row["task_id"]
        if task_id in tasks_by_id:
            tasks_by_id[task_id]["quality_correction"] = tasks_by_id[task_id]["quality_correction"] or quality
        elif len(task_order) < 5:
            task_order.append(task_id)
            tasks_by_id[task_id] = {"task_id": task_id, "quality_correction": quality,
                                    "latest_cause": row["cause"]}
    tasks = [tasks_by_id[task_id] for task_id in task_order]
    return sum(item["quality_correction"] for item in tasks) >= 2, tasks


def _history(db: sqlite3.Connection, payload: dict[str, Any]) -> dict[str, Any]:
    allowed = {"scope", "pattern", "rules_revision", "model", "effort"}
    _exact_fields(payload, allowed, allowed, "history payload")
    pair = _validate_pair({"model": payload["model"], "effort": payload["effort"]}, "history")
    scope = _text(payload["scope"], "scope")
    pattern = _text(payload["pattern"], "pattern")
    rules_revision = _text(payload["rules_revision"], "rules_revision")
    reassessment, tasks = _reassessment(db, scope, pattern, rules_revision, pair["model"], pair["effort"])
    return {"scope": scope, "pattern": pattern, "rules_revision": rules_revision, **pair,
            "reassessment_required": reassessment, "recent_feedback_tasks": tasks,
            "automatic_permanent_floor": False}


def execute(command: str, payload: Any, state_dir: str | Path | None = None,
            profile: str = "local", dry_run: bool = False) -> dict[str, Any]:
    state = Path(state_dir) if state_dir is not None else default_state_dir()
    if command == "route":
        card = validate_card(payload)
        if dry_run:
            return _route(None, card, True)
    db = connect(state, profile)
    try:
        if command == "route":
            return _route(db, card, False)
        body = _require_object(payload, f"{command} payload")
        handlers = {
            "replan": _replan, "start": _start, "bind": _bind, "verify": _verify, "finish": _finish,
            "usage": _usage, "feedback": _feedback, "summary": _summary, "history": _history,
        }
        if command not in handlers:
            raise RouterError(f"unknown command: {command}")
        return handlers[command](db, body)
    finally:
        db.close()


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Local team-task routing reference runtime")
    result.add_argument("--state-dir", default=str(default_state_dir()))
    result.add_argument("--profile", default="local")
    commands = result.add_subparsers(dest="command", required=True)
    for name in ("route", "replan", "start", "bind", "verify", "finish", "usage", "feedback", "summary", "history"):
        command = commands.add_parser(name)
        if name == "route":
            command.add_argument("--dry-run", action="store_true")
        command.add_argument("--input", required=True, metavar="FILE")
    return result


def _read_json(path: str) -> Any:
    try:
        if path == "-":
            return json.load(sys.stdin)
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise RouterError(f"invalid JSON: {exc.msg}") from None
    except OSError as exc:
        raise RouterError(f"cannot read input: {exc.strerror}") from None


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        payload = _read_json(args.input)
        result = execute(args.command, payload, args.state_dir, args.profile, getattr(args, "dry_run", False))
    except RouterError as exc:
        print(f"error[{exc.code}]: {exc}", file=sys.stderr)
        return 2
    except sqlite3.Error as exc:
        print(f"error[state_error]: {exc}", file=sys.stderr)
        return 3
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
