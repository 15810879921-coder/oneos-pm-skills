#!/usr/bin/env python3
"""Prepare 何斐's audited emergency release fast-lane write-back plan.

This script does not execute a release.  It verifies the operator identity and
required safety facts, then emits an immutable audit payload and an official
CLI gateway transaction plan for a later, explicitly authorized write-back.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA = "oneos.emergency-release/v1"
PREFIX = "【紧急发版快车道】"
EXPECTED_OPERATOR = "何斐"
EXPECTED_ORDER = [
    "identity-verified", "release-execute", "audit-record",
    "task-writeback", "post-release-verify",
]
REQUIRED_CHECKS = {
    "operator-identity",
    "release-task-scope",
    "artifact-version-build",
    "rollback-target",
}


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def stable_hash(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def non_empty(values: list[str], label: str) -> list[str]:
    result = [str(value).strip() for value in values if str(value).strip()]
    if not result:
        raise ValueError(f"{label}至少需要一项")
    return result


def verify_operator(args: argparse.Namespace) -> dict[str, str]:
    if args.operator_name != EXPECTED_OPERATOR:
        raise ValueError("紧急快车道仅允许何斐；普通用户必须回到普通发版流程")
    expected_id = args.authorized_operator_id or os.environ.get("YUNXIAO_EMERGENCY_OPERATOR_ID")
    if not expected_id:
        raise ValueError("缺少何斐的已授权身份ID；不得用姓名单独放行")
    if args.operator_id != expected_id:
        raise ValueError("操作者身份ID与已授权何斐身份不匹配")
    if args.identity_source != "official-cli-current-user":
        raise ValueError("身份来源必须是 official-cli-current-user 的当前用户回读")
    return {"id": args.operator_id, "name": EXPECTED_OPERATOR, "source": args.identity_source}


def make_payload(args: argparse.Namespace) -> dict[str, Any]:
    operator = verify_operator(args)
    skipped = non_empty(args.skipped_step, "skipped-step")
    checks = non_empty(args.minimum_safety_check, "minimum-safety-check")
    missing = sorted(REQUIRED_CHECKS - set(checks))
    if missing:
        raise ValueError("最低安全检查缺失：" + ",".join(missing))
    if not args.rollback_version.strip():
        raise ValueError("必须明确可验证的回滚版本")
    payload: dict[str, Any] = {
        "schemaVersion": SCHEMA,
        "releaseTaskId": args.task_id,
        "taskId": args.task_id,
        "operator": operator,
        "reason": args.reason.strip(),
        "version": args.version.strip(),
        "buildId": args.build_id.strip(),
        "skippedSteps": skipped,
        "minimumSafetyChecks": checks,
        "rollbackVersion": args.rollback_version.strip(),
        "releaseResult": args.release_result,
        "verificationResult": args.verification_result,
        "executionOrder": EXPECTED_ORDER,
        "mode": "plan-only",
        "createdAt": now(),
    }
    if not payload["reason"] or not payload["version"] or not payload["buildId"]:
        raise ValueError("reason/version/build-id均为必填")
    payload["auditId"] = "emergency-" + stable_hash(payload)[:24]
    payload["idempotencyKey"] = payload["auditId"]
    return payload


def gateway_plan(payload: dict[str, Any]) -> dict[str, Any]:
    comment = PREFIX + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    task_id = payload["taskId"]
    return {
        "schema": "oneos.yunxiao-cli-transaction-plan/v1",
        "label": "何斐紧急发版快车道审计回写",
        "authority": "apply",
        "idempotencyKey": payload["idempotencyKey"],
        "guards": [{
            "operation": "projex-get-workitem",
            "args": ["--id", task_id],
            "expect": {"id": task_id},
        }],
        "actions": [{
            "operation": "projex-create-workitem-comment",
            "args": ["--id", task_id, "--content", comment],
        }],
        "verifications": [{
            "operation": "projex-get-workitem",
            "args": ["--id", task_id],
            "expect": {"id": task_id},
        }],
        "releaseGateStage": "release",
        "releaseHandoffs": [],
        "emergencyFastLane": True,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--operator-id", required=True)
    parser.add_argument("--operator-name", required=True)
    parser.add_argument("--authorized-operator-id")
    parser.add_argument("--identity-source", default="official-cli-current-user")
    parser.add_argument("--reason", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--build-id", required=True)
    parser.add_argument("--rollback-version", required=True)
    parser.add_argument("--skipped-step", action="append", default=[])
    parser.add_argument("--minimum-safety-check", action="append", default=[])
    parser.add_argument("--release-result", choices=["success", "failed", "pending"], required=True)
    parser.add_argument("--verification-result", choices=["passed", "failed", "pending"], required=True)
    parser.add_argument("--output", required=True, help="输出审计与gateway计划的JSON文件")
    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()
        payload = make_payload(args)
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps({"audit": payload, "gatewayPlan": gateway_plan(payload)}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"result": "ready", "auditId": payload["auditId"], "output": str(output), "mode": "plan-only", "writeBack": "not-run"}, ensure_ascii=False))
        return 0
    except (OSError, ValueError) as exc:
        print(json.dumps({"result": "blocked", "reason": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
