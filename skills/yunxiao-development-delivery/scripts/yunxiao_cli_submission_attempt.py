#!/usr/bin/env python3
"""Persist idempotent per-repository checkpoints for one delivery submission attempt."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


SCHEMA = "oneos.delivery-submission-attempt/v1"
SUITE_VERSION = "10.1.0"
SUPPORTED_SUITE_VERSIONS = {"10.0.0", SUITE_VERSION}
REPO_STATES = {"PENDING", "RUNNING", "SUCCEEDED", "FAILED", "BLOCKED"}
TERMINAL = {"SUCCEEDED", "FAILED", "BLOCKED"}


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("文件必须是JSON对象")
    return value


def write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def now() -> str:
    return datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds")


def validate(attempt: dict[str, Any]) -> None:
    if attempt.get("schemaVersion") != SCHEMA:
        raise ValueError(f"schemaVersion必须为{SCHEMA}")
    if attempt.get("suiteVersion") not in SUPPORTED_SUITE_VERSIONS:
        raise ValueError(f"suiteVersion必须为受支持版本：{sorted(SUPPORTED_SUITE_VERSIONS)}")
    repositories = attempt.get("repositories")
    if not isinstance(repositories, list) or not repositories:
        raise ValueError("repositories不能为空")
    ids = [str(item.get("repositoryId") or "") for item in repositories if isinstance(item, dict)]
    if any(not value for value in ids) or len(ids) != len(set(ids)) or len(ids) != len(repositories):
        raise ValueError("repositoryId必须完整且唯一")
    for item in repositories:
        if item.get("status") not in REPO_STATES:
            raise ValueError(f"仓库{item.get('repositoryId')}状态无效")


def start(spec: dict[str, Any]) -> dict[str, Any]:
    delivery_unit = str(spec.get("deliveryUnitId") or "").strip()
    repositories = spec.get("repositories")
    if not delivery_unit or not isinstance(repositories, list) or not repositories:
        raise ValueError("deliveryUnitId和repositories必填")
    normalized = []
    for item in repositories:
        if not isinstance(item, dict) or not item.get("repositoryId"):
            raise ValueError("每个仓库必须提供repositoryId")
        normalized.append({
            "repositoryId": str(item["repositoryId"]),
            "branchInstanceId": item.get("branchInstanceId"),
            "status": "PENDING",
            "checkpoint": "not_started",
            "commitIds": [],
            "mr": None,
            "error": None,
            "updatedAt": None,
        })
    seed = {"deliveryUnitId": delivery_unit, "repositories": [item["repositoryId"] for item in normalized], "idempotencyKey": spec.get("idempotencyKey")}
    attempt = {
        "schemaVersion": SCHEMA,
        "suiteVersion": SUITE_VERSION,
        "submissionAttemptId": "SUBMIT-" + hashlib.sha256(json.dumps(seed, sort_keys=True).encode("utf-8")).hexdigest()[:20],
        "deliveryUnitId": delivery_unit,
        "idempotencyKey": str(spec.get("idempotencyKey") or ""),
        "createdAt": str(spec.get("createdAt") or now()),
        "status": "PENDING",
        "repositories": normalized,
    }
    if not attempt["idempotencyKey"]:
        raise ValueError("idempotencyKey必填")
    validate(attempt)
    return attempt


def recalculate(attempt: dict[str, Any]) -> None:
    states = {item["status"] for item in attempt["repositories"]}
    if states == {"SUCCEEDED"}:
        attempt["status"] = "SUCCEEDED"
    elif "RUNNING" in states or ("SUCCEEDED" in states and "PENDING" in states):
        attempt["status"] = "PARTIAL"
    elif states & {"FAILED", "BLOCKED"}:
        attempt["status"] = "PARTIAL" if states & {"SUCCEEDED", "RUNNING", "PENDING"} else "FAILED"
    else:
        attempt["status"] = "PENDING"


def record(attempt: dict[str, Any], repository_id: str, status: str, checkpoint: str,
           commit_ids: list[str], mr: str | None, error: str | None) -> dict[str, Any]:
    validate(attempt)
    if status not in REPO_STATES:
        raise ValueError(f"status必须是{sorted(REPO_STATES)}之一")
    matches = [item for item in attempt["repositories"] if item["repositoryId"] == repository_id]
    if len(matches) != 1:
        raise ValueError("repositoryId不在本次提交尝试或不唯一")
    item = matches[0]
    if item["status"] == "SUCCEEDED" and status != "SUCCEEDED":
        raise ValueError("已成功仓库不得在同一次尝试中降级；应创建新的补充提交尝试")
    item.update(status=status, checkpoint=checkpoint, commitIds=commit_ids, mr=mr,
                error=error, updatedAt=now())
    recalculate(attempt)
    return attempt


def main() -> int:
    parser = argparse.ArgumentParser(description="多仓库提交检查点账本")
    sub = parser.add_subparsers(dest="command", required=True)
    start_parser = sub.add_parser("start")
    start_parser.add_argument("--spec", required=True, type=Path)
    start_parser.add_argument("--output", required=True, type=Path)
    record_parser = sub.add_parser("record")
    record_parser.add_argument("--attempt", required=True, type=Path)
    record_parser.add_argument("--repository-id", required=True)
    record_parser.add_argument("--status", required=True, choices=sorted(REPO_STATES))
    record_parser.add_argument("--checkpoint", required=True)
    record_parser.add_argument("--commit-id", action="append", default=[])
    record_parser.add_argument("--mr")
    record_parser.add_argument("--error")
    record_parser.add_argument("--output", required=True, type=Path)
    summary_parser = sub.add_parser("summary")
    summary_parser.add_argument("--attempt", required=True, type=Path)
    args = parser.parse_args()
    try:
        if args.command == "start":
            attempt = start(load(args.spec))
            write(args.output, attempt)
        elif args.command == "record":
            attempt = record(load(args.attempt), args.repository_id, args.status, args.checkpoint,
                             list(args.commit_id), args.mr, args.error)
            write(args.output, attempt)
        else:
            attempt = load(args.attempt)
            validate(attempt)
        print(json.dumps(attempt, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "blocked", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 2


if __name__ == "__main__":
    sys.exit(main())
