#!/usr/bin/env python3
"""Track safe multi-repository target-branch merge and deployment continuation state."""

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


PLAN_SCHEMA = "oneos.release-merge-plan/v1"
ATTEMPT_SCHEMA = "oneos.release-merge-attempt/v1"
SUITE_VERSION = "10.1.0"
SUPPORTED_SUITE_VERSIONS = {"10.0.0", SUITE_VERSION}
STATES = {"PENDING", "PARTIAL_TARGET_MERGE", "TARGETS_READY", "MERGED_NOT_DEPLOYED", "DEPLOYED", "REVERTED"}


def now() -> str:
    return datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds")


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("文件必须是JSON对象")
    return value


def write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def attempt_id(plan: dict[str, Any]) -> str:
    seed = f"{plan.get('releaseTaskId')}|{plan.get('mergePlanId')}|{plan.get('planHash')}"
    return "MERGEATTEMPT-" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:20]


def validate_attempt(attempt: dict[str, Any]) -> None:
    if attempt.get("schemaVersion") != ATTEMPT_SCHEMA:
        raise ValueError(f"schemaVersion必须为{ATTEMPT_SCHEMA}")
    if attempt.get("suiteVersion") not in SUPPORTED_SUITE_VERSIONS:
        raise ValueError(f"suiteVersion必须为受支持版本：{sorted(SUPPORTED_SUITE_VERSIONS)}")
    if attempt.get("state") not in STATES:
        raise ValueError("合并尝试状态无效")
    repositories = attempt.get("repositories")
    if not isinstance(repositories, list) or not repositories:
        raise ValueError("repositories不能为空")
    keys = [str(item.get("repositoryKey") or "") for item in repositories if isinstance(item, dict)]
    if len(keys) != len(repositories) or any(not value for value in keys) or len(keys) != len(set(keys)):
        raise ValueError("repositoryKey必须完整且唯一")


def validate_execution(attempt: dict[str, Any]) -> None:
    validate_attempt(attempt)
    coverage.validate_plan(attempt.get("frozenPlan") or {})
    if attempt.get("planHash") != attempt["frozenPlan"]["planHash"]:
        raise ValueError("尝试与冻结计划哈希不一致")


def init(plan: dict[str, Any]) -> dict[str, Any]:
    if plan.get("schemaVersion") != PLAN_SCHEMA or plan.get("status") != "READY":
        raise ValueError("只能执行READY状态的mergePlan")
    coverage.validate_plan(plan)
    repositories = []
    for item in plan.get("items") or []:
        if item.get("action") == "ALREADY_CONTAINED":
            status = "SUCCESS"
            target_commit = item.get("targetBaseCommit")
        else:
            status = "PENDING"
            target_commit = None
        repositories.append({
            "repositoryKey": f"{item.get('repositoryId')}|{item.get('componentId')}|{item.get('targetBranch')}|{item.get('deploymentTarget')}",
            "repositoryId": item.get("repositoryId"),
            "componentId": item.get("componentId"),
            "targetBranch": item.get("targetBranch"),
            "deploymentTarget": item.get("deploymentTarget"),
            "action": item.get("action"),
            "mergeStatus": status,
            "resultTargetCommit": target_commit,
            "revertStatus": None,
            "error": None,
            "targetBaseCommit": item["targetBaseCommit"],
            "targetCoverage": None,
        })
    state = "TARGETS_READY" if all(item["mergeStatus"] == "SUCCESS" for item in repositories) else "PENDING"
    result = {
        "schemaVersion": ATTEMPT_SCHEMA,
        "suiteVersion": str(plan.get("suiteVersion") or SUITE_VERSION),
        "releaseMergeAttemptId": attempt_id(plan),
        "releaseTaskId": plan.get("releaseTaskId"),
        "mergePlanId": plan.get("mergePlanId"),
        "mergePlanVersion": plan.get("mergePlanVersion"),
        "planHash": plan.get("planHash"),
        "frozenPlan": json.loads(json.dumps(plan)),
        "state": state,
        "preflightPassed": False,
        "createdAt": now(),
        "updatedAt": now(),
        "repositories": repositories,
        "deployment": None,
        "events": [],
    }
    validate_attempt(result)
    return result


def preflight(attempt: dict[str, Any], checks: dict[str, Any]) -> dict[str, Any]:
    validate_execution(attempt)
    rows = checks.get("repositories")
    if not isinstance(rows, list):
        raise ValueError("preflight checks.repositories必须是数组")
    checks_by_key = {str(item.get("repositoryKey")): item for item in rows if isinstance(item, dict)}
    failures: list[str] = []
    for repo in attempt["repositories"]:
        check = checks_by_key.get(repo["repositoryKey"])
        if not check:
            failures.append(f"{repo['repositoryKey']}缺少预检")
            continue
        required = ["targetHeadMatches", "testsValid", "dependencyComplete"]
        required.append("exactCommitsContained" if repo.get("action") == "ALREADY_CONTAINED" else "mergeable")
        for field in required:
            if check.get(field) is not True:
                failures.append(f"{repo['repositoryKey']}预检失败：{field}")
        expected_target = repo.get("resultTargetCommit") or repo["targetBaseCommit"]
        if check.get("currentTargetCommit") != expected_target:
            failures.append(f"{repo['repositoryKey']}目标版本与冻结/已合入版本不一致")
        already_merged = repo["mergeStatus"] == "SUCCESS"
        revision = expected_target if already_merged else check.get("candidateRevision")
        proof = check.get("targetCoverage" if already_merged else "candidateCoverage") or {}
        try:
            coverage.validate_proof(proof, attempt["planHash"], repo["repositoryKey"],
                                    repo["targetBaseCommit"], revision)
            if already_merged:
                repo["targetCoverage"] = proof
        except ValueError as exc:
            failures.append(f"{repo['repositoryKey']}:{exc}")
    attempt["preflightPassed"] = not failures
    attempt["preflightBlockers"] = failures
    attempt["updatedAt"] = now()
    return attempt


def find_repo(attempt: dict[str, Any], repository_key: str) -> dict[str, Any]:
    matches = [item for item in attempt["repositories"] if item["repositoryKey"] == repository_key]
    if len(matches) != 1:
        raise ValueError("repository-key不在本次尝试或不唯一")
    return matches[0]


def recalculate_merge_state(attempt: dict[str, Any]) -> None:
    statuses = [item["mergeStatus"] for item in attempt["repositories"]]
    if all(value == "SUCCESS" for value in statuses):
        attempt["state"] = "TARGETS_READY"
    elif any(value == "FAILED" for value in statuses):
        attempt["state"] = "PARTIAL_TARGET_MERGE"
    else:
        attempt["state"] = "PENDING"


def record_merge(attempt: dict[str, Any], repository_key: str, status: str,
                 target_commit: str | None, error: str | None,
                 target_coverage: dict[str, Any] | None = None) -> dict[str, Any]:
    validate_execution(attempt)
    if attempt["state"] not in {"PENDING", "PARTIAL_TARGET_MERGE"}:
        raise ValueError("当前状态不允许继续记录目标分支合并")
    if attempt.get("preflightPassed") is not True:
        raise ValueError("全部仓库预检未通过，一个也不能合并")
    if status not in {"success", "failed"}:
        raise ValueError("status必须为success或failed")
    repo = find_repo(attempt, repository_key)
    if repo["mergeStatus"] == "SUCCESS" and status != "success":
        raise ValueError("已成功进入目标分支的仓库不得直接降级")
    if status == "success" and not target_commit:
        raise ValueError("成功合并必须提供resultTargetCommit")
    if status == "success":
        coverage.validate_proof(target_coverage or {}, attempt["planHash"], repository_key,
                                repo["targetBaseCommit"], target_commit)
        repo["targetCoverage"] = target_coverage
    repo.update(mergeStatus=status.upper(), resultTargetCommit=target_commit, error=error)
    if status == "success":
        attempt["events"].append({
            "eventType": "PRODUCTION_MERGE_RECORDED",
            "repositoryKey": repository_key,
            "resultTargetCommit": target_commit,
            "occurredAt": now(),
        })
    recalculate_merge_state(attempt)
    if status == "failed":
        attempt["preflightPassed"] = False
        attempt["preflightBlockers"] = [f"{repository_key}合并失败后必须重新预检全部目标HEAD"]
    attempt["updatedAt"] = now()
    return attempt


def start_deployment(attempt: dict[str, Any]) -> dict[str, Any]:
    validate_execution(attempt)
    if attempt.get("preflightPassed") is not True:
        raise ValueError("全部仓库预检未通过，禁止开始部署")
    for repo in attempt["repositories"]:
        coverage.validate_proof(repo.get("targetCoverage") or {}, attempt["planHash"],
                                repo["repositoryKey"], repo["targetBaseCommit"], repo.get("resultTargetCommit"))
    retrying = attempt["state"] == "MERGED_NOT_DEPLOYED" and (attempt.get("deployment") or {}).get("status") == "FAILED"
    if attempt["state"] != "TARGETS_READY" and not retrying:
        raise ValueError("只有全部目标分支就绪后才能启动生产流水线")
    attempt["state"] = "MERGED_NOT_DEPLOYED"
    previous_attempts = list((attempt.get("deployment") or {}).get("attempts") or [])
    if attempt.get("deployment"):
        previous_attempts.append({key: value for key, value in attempt["deployment"].items() if key != "attempts"})
    attempt["deployment"] = {"status": "RUNNING", "evidenceId": None,
                             "attemptNo": len(previous_attempts) + 1,
                             "attempts": previous_attempts, "updatedAt": now()}
    attempt["updatedAt"] = now()
    return attempt


def record_deployment(attempt: dict[str, Any], status: str, evidence_id: str | None) -> dict[str, Any]:
    validate_attempt(attempt)
    if attempt["state"] != "MERGED_NOT_DEPLOYED":
        raise ValueError("当前状态没有待确认的生产部署")
    if status not in {"success", "failed"}:
        raise ValueError("status必须为success或failed")
    if status == "success" and not evidence_id:
        raise ValueError("生产成功必须提供不可变版本或部署证据")
    if status == "success":
        validate_execution(attempt)
        for repo in attempt["repositories"]:
            coverage.validate_proof(repo.get("targetCoverage") or {}, attempt["planHash"],
                                    repo["repositoryKey"], repo["targetBaseCommit"], repo.get("resultTargetCommit"))
    previous = attempt.get("deployment") or {}
    attempt["deployment"] = {"status": status.upper(), "evidenceId": evidence_id,
                             "attemptNo": previous.get("attemptNo", 1),
                             "attempts": previous.get("attempts") or [], "updatedAt": now()}
    if status == "success":
        attempt["state"] = "DEPLOYED"
        attempt["events"].append({"eventType": "PRODUCTION_RELEASED", "evidenceId": evidence_id, "occurredAt": now()})
    attempt["updatedAt"] = now()
    return attempt


def record_revert(attempt: dict[str, Any], repository_key: str, target_commit: str) -> dict[str, Any]:
    validate_attempt(attempt)
    if attempt["state"] not in {"PARTIAL_TARGET_MERGE", "MERGED_NOT_DEPLOYED"}:
        raise ValueError("只有部分合并或已合未部署状态允许通过新MR回退")
    repo = find_repo(attempt, repository_key)
    if repo["mergeStatus"] != "SUCCESS":
        raise ValueError("未成功进入目标分支的仓库不需要回退")
    if repo.get("action") == "ALREADY_CONTAINED":
        raise ValueError("目标分支原本已包含提交，不属于本次合并，禁止生成回退")
    if not target_commit:
        raise ValueError("回退成功必须提供回读后的目标分支提交")
    repo["revertStatus"] = "SUCCESS"
    repo["revertedTargetCommit"] = target_commit
    attempt["events"].append({
        "eventType": "PRODUCTION_MERGE_REVERTED",
        "repositoryKey": repository_key,
        "resultTargetCommit": target_commit,
        "occurredAt": now(),
    })
    successful = [item for item in attempt["repositories"]
                  if item["mergeStatus"] == "SUCCESS" and item.get("action") != "ALREADY_CONTAINED"]
    if successful and all(item.get("revertStatus") == "SUCCESS" for item in successful):
        attempt["state"] = "REVERTED"
    attempt["updatedAt"] = now()
    return attempt


def main() -> int:
    parser = argparse.ArgumentParser(description="多仓库生产目标分支合并和部署续跑状态机")
    sub = parser.add_subparsers(dest="command", required=True)
    init_parser = sub.add_parser("init")
    init_parser.add_argument("--plan", required=True, type=Path)
    init_parser.add_argument("--output", required=True, type=Path)
    preflight_parser = sub.add_parser("preflight")
    preflight_parser.add_argument("--attempt", required=True, type=Path)
    preflight_parser.add_argument("--checks", required=True, type=Path)
    preflight_parser.add_argument("--output", required=True, type=Path)
    merge_parser = sub.add_parser("record-merge")
    merge_parser.add_argument("--attempt", required=True, type=Path)
    merge_parser.add_argument("--repository-key", required=True)
    merge_parser.add_argument("--status", required=True, choices=["success", "failed"])
    merge_parser.add_argument("--target-commit")
    merge_parser.add_argument("--error")
    merge_parser.add_argument("--coverage", type=Path, help="verify-tree生成的目标文件树核验结果")
    merge_parser.add_argument("--output", required=True, type=Path)
    deploy_parser = sub.add_parser("start-deployment")
    deploy_parser.add_argument("--attempt", required=True, type=Path)
    deploy_parser.add_argument("--output", required=True, type=Path)
    deploy_result_parser = sub.add_parser("record-deployment")
    deploy_result_parser.add_argument("--attempt", required=True, type=Path)
    deploy_result_parser.add_argument("--status", required=True, choices=["success", "failed"])
    deploy_result_parser.add_argument("--evidence-id")
    deploy_result_parser.add_argument("--output", required=True, type=Path)
    revert_parser = sub.add_parser("record-revert")
    revert_parser.add_argument("--attempt", required=True, type=Path)
    revert_parser.add_argument("--repository-key", required=True)
    revert_parser.add_argument("--target-commit", required=True)
    revert_parser.add_argument("--output", required=True, type=Path)
    summary_parser = sub.add_parser("summary")
    summary_parser.add_argument("--attempt", required=True, type=Path)
    args = parser.parse_args()
    try:
        if args.command == "init":
            result = init(load(args.plan))
        elif args.command == "preflight":
            result = preflight(load(args.attempt), load(args.checks))
        elif args.command == "record-merge":
            result = record_merge(load(args.attempt), args.repository_key, args.status, args.target_commit,
                                  args.error, load(args.coverage) if args.coverage else None)
        elif args.command == "start-deployment":
            result = start_deployment(load(args.attempt))
        elif args.command == "record-deployment":
            result = record_deployment(load(args.attempt), args.status, args.evidence_id)
        elif args.command == "record-revert":
            result = record_revert(load(args.attempt), args.repository_key, args.target_commit)
        else:
            result = load(args.attempt)
            validate_attempt(result)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        write(args.output, result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "blocked", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 2


if __name__ == "__main__":
    sys.exit(main())
