#!/usr/bin/env python3
"""Resolve a safe branch base before the first task-owned code write."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


REQUEST_SCHEMA = "oneos.branch-base-request/v1"
RESULT_SCHEMA = "oneos.branch-base-resolution/v1"
INTENTS = {"continue", "development", "temporary", "test_bug", "production_hotfix"}
DIRTY_STATES = {"clean", "current-scope-only", "mixed"}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("请求必须是JSON对象")
    return value


def _verified_base(value: Any) -> dict[str, str] | None:
    if not isinstance(value, dict) or value.get("verified") is not True:
        return None
    branch = _text(value.get("branch"))
    commit = _text(value.get("commit"))
    if not branch or not commit:
        return None
    return {"branch": branch, "commit": commit, "evidenceId": _text(value.get("evidenceId"))}


def _branch_name(data: dict[str, Any], intent: str) -> str:
    explicit = _text(data.get("requestedBranch"))
    if explicit:
        return explicit
    identity = _text(data.get("targetWorkItemId") or data.get("targetDeliveryUnitId"))
    if not identity:
        digest = hashlib.sha256(json.dumps(data, sort_keys=True).encode("utf-8")).hexdigest()[:10]
        identity = digest
    if intent == "temporary":
        return f"tempdev/{identity.lower()}"
    if intent in {"test_bug", "production_hotfix"}:
        return f"fix/{identity}"
    return f"feature/{identity}"


def resolve(data: dict[str, Any]) -> dict[str, Any]:
    if data.get("schemaVersion") != REQUEST_SCHEMA:
        raise ValueError(f"schemaVersion必须为{REQUEST_SCHEMA}")
    intent = _text(data.get("intent"))
    if intent not in INTENTS:
        raise ValueError(f"intent必须是{sorted(INTENTS)}之一")
    dirty = _text(data.get("workingTree")) or "clean"
    if dirty not in DIRTY_STATES:
        raise ValueError(f"workingTree必须是{sorted(DIRTY_STATES)}之一")

    target_unit = _text(data.get("targetDeliveryUnitId"))
    repository_id = _text(data.get("repositoryId"))
    if not target_unit or not repository_id:
        raise ValueError("repositoryId和targetDeliveryUnitId必填")

    result: dict[str, Any] = {
        "schemaVersion": RESULT_SCHEMA,
        "repositoryId": repository_id,
        "targetDeliveryUnitId": target_unit,
        "intent": intent,
        "status": "resolved",
        "action": None,
        "branchName": None,
        "baseBranch": None,
        "baseCommit": None,
        "baseEvidenceId": None,
        "baseConfidence": "verified",
        "retestRequired": False,
        "carryCurrentChanges": dirty == "current-scope-only",
        "ignoredCurrentBranch": False,
        "blockers": [],
        "warnings": [],
    }

    if dirty == "mixed":
        result.update(status="blocked", action="pause_repository")
        result["blockers"].append("当前工作区混有其他事项改动，无法安全拆分")
        return result

    existing = data.get("existingBoundBranch")
    if isinstance(existing, dict):
        same_unit = _text(existing.get("deliveryUnitId")) == target_unit
        reusable = all(existing.get(key) is True for key in ("remoteExists", "writable", "synchronizable"))
        if same_unit and reusable and _text(existing.get("name")) and _text(existing.get("commit")):
            result.update(
                action="use_existing",
                branchName=_text(existing.get("name")),
                baseBranch=_text(existing.get("name")),
                baseCommit=_text(existing.get("commit")),
                baseEvidenceId=_text(existing.get("evidenceId")),
            )
            return result

    if intent == "continue":
        result.update(status="blocked", action="pause_repository")
        result["blockers"].append("继续开发必须先找到同一交付单元的可复用分支")
        return result

    integration = _verified_base(data.get("integrationBase"))
    tested = _verified_base(data.get("testDeployment"))
    production = _verified_base(data.get("productionBaseline"))

    selected: dict[str, str] | None = None
    if intent in {"development", "temporary"}:
        selected = integration
    elif intent == "test_bug":
        selected = tested
        if selected is None:
            selected = integration
            result["baseConfidence"] = "provisional"
            result["retestRequired"] = True
            result["warnings"].append("无法证明真实被测提交，允许临时修复但必须重新部署并复测")
    elif intent == "production_hotfix":
        selected = production
        if selected is None:
            selected = integration
            result["baseConfidence"] = "provisional"
            result["retestRequired"] = True
            result["warnings"].append("无法证明生产基线，允许临时修复但禁止直接发布生产")

    if selected is None:
        result.update(status="blocked", action="pause_repository")
        result["blockers"].append("没有可核验的分支基线")
        return result

    current_branch = _text(data.get("currentBranch"))
    current_commit = _text(data.get("currentCommit"))
    current_unit = _text(data.get("currentBranchDeliveryUnitId"))
    can_reuse_current = current_unit == target_unit and current_commit == selected["commit"]
    if can_reuse_current and current_branch:
        branch_name = current_branch
        action = "use_current"
    else:
        branch_name = _branch_name(data, intent)
        action = "create_branch"
        result["ignoredCurrentBranch"] = bool(current_branch)

    result.update(
        action=action,
        branchName=branch_name,
        baseBranch=selected["branch"],
        baseCommit=selected["commit"],
        baseEvidenceId=selected.get("evidenceId"),
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="解析开发/TEMPDEV/Bug/hotfix分支的安全基线")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        result = resolve(_load(args.input))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "blocked", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 2
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 2 if result["status"] == "blocked" else 0


if __name__ == "__main__":
    sys.exit(main())
