#!/usr/bin/env python3
"""Freeze exact per-repository production-target merge actions."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
import validate_release_change_coverage as coverage


INPUT_SCHEMA = "oneos.release-merge-input/v1"
PLAN_SCHEMA = "oneos.release-merge-plan/v1"
SUITE_VERSION = "10.0.0"
PURITY_ACTIONS = {
    "pure": "MERGE_SOURCE_BRANCH",
    "mixed": "BUILD_CLEAN_CANDIDATE",
    "contained": "ALREADY_CONTAINED",
    "unknown": "BLOCKED",
}


def normalize_source(source: dict[str, Any], label: str) -> tuple[dict[str, Any], list[str]]:
    blockers: list[str] = []
    purity = str(source.get("branchPurity") or "unknown")
    exact_commits = [str(value) for value in source.get("exactCommitIds") or []]
    raw_history = source.get("sourceCommitHistory")
    history: list[dict[str, Any]] = []
    if raw_history is not None:
        if not isinstance(raw_history, list):
            blockers.append(f"{label}: sourceCommitHistory必须是数组")
        else:
            seen_history: set[str] = set()
            for index, entry in enumerate(raw_history):
                if not isinstance(entry, dict):
                    blockers.append(f"{label}: sourceCommitHistory[{index}]必须是对象")
                    continue
                commit_id = str(entry.get("commitId") or "")
                evidence_id = str(entry.get("evidenceId") or "")
                include = entry.get("include")
                if not commit_id:
                    blockers.append(f"{label}: sourceCommitHistory[{index}]缺少commitId")
                    continue
                if commit_id in seen_history:
                    blockers.append(f"{label}: sourceCommitHistory存在重复提交{commit_id}")
                    continue
                seen_history.add(commit_id)
                if not isinstance(include, bool):
                    blockers.append(f"{label}: 提交{commit_id}缺少明确include判定")
                if not evidence_id:
                    blockers.append(f"{label}: 提交{commit_id}缺少范围判定证据")
                history.append({
                    "commitId": commit_id,
                    "include": include,
                    "evidenceId": evidence_id or None,
                    "sourceWorkItemIds": [str(value) for value in entry.get("sourceWorkItemIds") or []],
                    "reason": entry.get("reason"),
                    "requiresCommitIds": entry.get("requiresCommitIds") or [],
                    "replayParent": entry.get("replayParent"),
                })

    if purity != "contained":
        if source.get("sourceHistoryComplete") is not True:
            blockers.append(f"{label}: 未证明已读取源分支相对目标基线的完整提交历史")
        if not str(source.get("sourceHistoryEvidenceId") or ""):
            blockers.append(f"{label}: 缺少完整提交历史证据")
        if not history:
            blockers.append(f"{label}: 缺少源分支相对目标基线的完整提交历史")
        else:
            history_ids = [entry["commitId"] for entry in history]
            included_ids = {entry["commitId"] for entry in history if entry.get("include") is True}
            if set(exact_commits) != included_ids:
                missing = sorted(included_ids - set(exact_commits))
                extra = sorted(set(exact_commits) - included_ids)
                blockers.append(
                    f"{label}: 精确提交集合与逐提交范围判定不闭合"
                    f"（遗漏={','.join(missing) or '-'}，多选={','.join(extra) or '-'}）"
                )
            if str(source.get("sourceHead") or "") != history_ids[-1]:
                blockers.append(f"{label}: 完整提交历史末项不是冻结的sourceHead")
            if purity == "pure" and any(entry.get("include") is not True for entry in history):
                blockers.append(f"{label}: pure源分支存在未纳入提交")

    normalized = {
        "sourceBranch": source.get("sourceBranch"),
        "sourceHead": source.get("sourceHead"),
        "exactCommitIds": exact_commits,
        "testEvidenceIds": [str(value) for value in source.get("testEvidenceIds") or []],
        "sourceWorkItemIds": [str(value) for value in source.get("sourceWorkItemIds") or []],
        "deliveryUnitIds": [str(value) for value in source.get("deliveryUnitIds") or []],
        "branchPurity": purity,
        "sourceHistoryComplete": source.get("sourceHistoryComplete") is True,
        "sourceHistoryEvidenceId": source.get("sourceHistoryEvidenceId"),
        "sourceCommitHistory": history,
        "patchHash": source.get("patchHash"),
        "mr": source.get("mr"),
        "containmentEvidenceId": source.get("containmentEvidenceId"),
        "historySnapshot": source.get("historySnapshot"),
        "branchOwner": source.get("branchOwner"),
    }
    return normalized, blockers


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("输入必须是JSON对象")
    return value


def stable_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


def build(data: dict[str, Any], previous: dict[str, Any] | None = None,
          revision_reason: str | None = None) -> dict[str, Any]:
    if data.get("schemaVersion") != INPUT_SCHEMA:
        raise ValueError(f"schemaVersion必须为{INPUT_SCHEMA}")
    release_task = str(data.get("releaseTaskId") or "").strip()
    raw_items = data.get("items")
    if not release_task or not isinstance(raw_items, list) or not raw_items:
        raise ValueError("releaseTaskId和items必填")
    version = 1
    previous_id = None
    if previous is not None:
        if previous.get("schemaVersion") != PLAN_SCHEMA or previous.get("releaseTaskId") != release_task:
            raise ValueError("previous-plan与当前发版任务不一致")
        if not revision_reason:
            raise ValueError("修订mergePlan必须提供revisionReason")
        version = int(previous.get("mergePlanVersion") or 0) + 1
        previous_id = previous.get("mergePlanId")

    dependency_group_ids = {str(value) for value in data.get("dependencyGroupIds") or [] if str(value)}
    items: list[dict[str, Any]] = []
    blockers: list[str] = []
    seen: set[str] = set()
    for index, raw in enumerate(raw_items):
        if not isinstance(raw, dict):
            blockers.append(f"items[{index}]必须是对象")
            continue
        repository_id = str(raw.get("repositoryId") or "")
        component_id = str(raw.get("componentId") or "")
        target_branch = str(raw.get("targetBranch") or "")
        deployment_target = str(raw.get("deploymentTarget") or "")
        pipeline_id = str(raw.get("pipelineId") or "")
        key = f"{repository_id}|{component_id}|{target_branch}|{deployment_target}"
        if not all((repository_id, component_id, target_branch, deployment_target, pipeline_id)):
            blockers.append(f"items[{index}]缺少仓库、组件、目标分支、部署目标或生产流水线")
            continue
        if key in seen:
            blockers.append(f"重复mergePlan项：{key}")
            continue
        seen.add(key)
        raw_sources = raw.get("sources")
        if raw_sources is None:
            raw_sources = [{
                "sourceBranch": raw.get("sourceBranch"),
                "sourceHead": raw.get("sourceHead"),
                "exactCommitIds": raw.get("exactCommitIds") or [],
                "testEvidenceIds": raw.get("testEvidenceIds") or [],
                "sourceWorkItemIds": raw.get("sourceWorkItemIds") or [],
                "deliveryUnitIds": raw.get("deliveryUnitIds") or [],
                "branchPurity": raw.get("branchPurity"),
                "sourceHistoryComplete": raw.get("sourceHistoryComplete"),
                "sourceHistoryEvidenceId": raw.get("sourceHistoryEvidenceId"),
                "sourceCommitHistory": raw.get("sourceCommitHistory"),
                "patchHash": raw.get("patchHash"),
                "mr": raw.get("mr"),
                "containmentEvidenceId": raw.get("containmentEvidenceId"),
                "historySnapshot": raw.get("historySnapshot"),
                "branchOwner": raw.get("branchOwner"),
            }]
        if not isinstance(raw_sources, list) or not raw_sources or not all(isinstance(source, dict) for source in raw_sources):
            blockers.append(f"{key}: sources必须是非空对象数组")
            continue
        sources: list[dict[str, Any]] = []
        source_blockers: list[str] = []
        for source_index, source in enumerate(raw_sources):
            normalized, normalized_blockers = normalize_source(source, f"source[{source_index}]")
            sources.append(normalized)
            source_blockers.extend(normalized_blockers)
        purities = {source["branchPurity"] for source in sources}
        if "unknown" in purities or not purities.issubset(PURITY_ACTIONS):
            action = "BLOCKED"
        elif purities == {"contained"}:
            action = "ALREADY_CONTAINED"
        elif len(sources) == 1 and purities == {"pure"}:
            action = "MERGE_SOURCE_BRANCH"
        else:
            action = "BUILD_CLEAN_CANDIDATE"
        commits = sorted({value for source in sources for value in source["exactCommitIds"]})
        tests = sorted({value for source in sources for value in source["testEvidenceIds"]})
        work_items = sorted({value for source in sources for value in source["sourceWorkItemIds"]})
        delivery_units = sorted({value for source in sources for value in source["deliveryUnitIds"]})
        item_blockers: list[str] = list(source_blockers)
        if raw.get("targetBranchVerified") is not True:
            item_blockers.append("生产目标分支未核验")
        if not commits:
            item_blockers.append("缺少精确提交集合")
        if not tests:
            item_blockers.append("缺少与候选代码对应的测试证据")
        if not delivery_units:
            item_blockers.append("缺少交付单元归属")
        if not str(raw.get("targetBaseCommit") or ""):
            item_blockers.append("缺少冻结的生产目标基线提交")
        dependency_group_id = str(raw.get("dependencyGroupId") or "")
        if not dependency_group_id or dependency_group_id not in dependency_group_ids:
            item_blockers.append("缺少有效依赖组归属")
        if action == "BLOCKED":
            item_blockers.append("无法证明源分支纯度或构建干净候选")
        if action == "ALREADY_CONTAINED" and any(
            not str(source.get("containmentEvidenceId") or "") for source in sources
        ):
            item_blockers.append("缺少目标分支已包含精确提交的证据")
        item = {
            "repositoryId": repository_id,
            "componentId": component_id,
            "sourceWorkItemIds": work_items,
            "deliveryUnitIds": delivery_units,
            "sources": sources,
            "sourceBranch": sources[0].get("sourceBranch") if len(sources) == 1 else None,
            "targetBranch": target_branch,
            "deploymentTarget": deployment_target,
            "pipelineId": pipeline_id,
            "dependencyGroupId": dependency_group_id,
            "sourceHead": sources[0].get("sourceHead") if len(sources) == 1 else None,
            "targetBaseCommit": raw.get("targetBaseCommit"),
            "exactCommitIds": commits,
            "testEvidenceIds": tests,
            "patchHash": raw.get("patchHash"),
            "mr": sources[0].get("mr") if len(sources) == 1 else None,
            "containmentEvidenceId": sources[0].get("containmentEvidenceId") if len(sources) == 1 else None,
            "action": action if not item_blockers else "BLOCKED",
            "blockers": item_blockers,
        }
        try:
            change_coverage = coverage.inspect_item(item)
            item["replayOrder"] = change_coverage["replayOrder"]
            if (change_coverage["equivalentCommitIds"] and not item_blockers
                    and action != "ALREADY_CONTAINED"):
                item["action"] = "BUILD_CLEAN_CANDIDATE"
        except (ValueError, TypeError, KeyError) as exc:
            item_blockers.append(str(exc))
            item["action"] = "BLOCKED"
            item["replayOrder"] = []
        if item_blockers:
            blockers.extend(f"{key}: {reason}" for reason in item_blockers)
        items.append(item)

    core = {
        "schemaVersion": PLAN_SCHEMA,
        "suiteVersion": SUITE_VERSION,
        "coverageVersion": 1,
        "releaseTaskId": release_task,
        "mergePlanVersion": version,
        "previousMergePlanId": previous_id,
        "revisionReason": revision_reason,
        "frozenAt": str(data.get("frozenAt") or datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds")),
        "items": items,
        "dependencyGroupIds": sorted(dependency_group_ids),
        "status": "BLOCKED" if blockers else "READY",
        "blockers": blockers,
    }
    core["mergePlanId"] = "MERGEPLAN-" + stable_hash(core)[:20]
    core["planHash"] = stable_hash(core)
    return core


def main() -> int:
    parser = argparse.ArgumentParser(description="生成逐仓库冻结生产目标分支合并计划")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--previous-plan", type=Path)
    parser.add_argument("--revision-reason")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        previous = load(args.previous_plan) if args.previous_plan else None
        result = build(load(args.input), previous, args.revision_reason)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "BLOCKED", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 2 if result["status"] == "BLOCKED" else 0


if __name__ == "__main__":
    sys.exit(main())
