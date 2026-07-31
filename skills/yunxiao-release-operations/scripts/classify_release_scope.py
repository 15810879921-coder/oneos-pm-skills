#!/usr/bin/env python
"""离线分类发布范围为A/B/C/D；不连接或修改云效。"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


DEPLOY_SCHEMA = "oneos.test-deployment/v1"
QA_SCHEMA = "oneos.qa-evidence/v1"
BUG_RETEST_SCHEMA = "oneos.bug-retest/v1"


def load_json(path: str) -> dict[str, Any]:
    text = sys.stdin.read() if path == "-" else Path(path).read_text(encoding="utf-8")
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("输入根节点必须是JSON对象")
    return data


def as_count(item: dict[str, Any], key: str) -> int:
    value = item.get(key, 0)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{item.get('id')}.{key}必须是非负整数")
    return value


def valid_ref(value: object) -> bool:
    text = str(value or "").strip()
    return bool(text) and text.lower() not in {"none", "null", "n/a", "无", "..."} and not (
        "<" in text or ">" in text
    )


def structured_evidence_gaps(item: dict[str, Any]) -> list[str]:
    """校验证据内容，禁止用调用方自报布尔值代替真实证据。"""
    gaps: list[str] = []
    requirement_id = str(item.get("id") or "")
    project_id = str(item.get("projectId") or "")
    iteration_id = str(item.get("iterationId") or "")
    test_task_id = str(item.get("testTaskId") or "")

    deployment = item.get("testDeployment")
    if not isinstance(deployment, dict):
        return ["缺少结构化test部署证据"]
    if deployment.get("schemaVersion") != DEPLOY_SCHEMA:
        gaps.append("test部署证据schema无效")
    for field, expected in (
        ("projectId", project_id),
        ("iterationId", iteration_id),
        ("requirementId", requirement_id),
        ("testTaskId", test_task_id),
    ):
        if not expected or str(deployment.get(field) or "") != expected:
            gaps.append(f"test部署证据{field}不一致")
    if str(deployment.get("environment") or "").lower() != "test":
        gaps.append("test部署环境不是test")
    if str(deployment.get("status") or "").lower() not in {"成功", "success", "succeeded"}:
        gaps.append("test部署不是成功终态")
    for field in ("executionId", "deployedVersion", "evidenceUrl", "completedAt", "idempotencyKey"):
        if not valid_ref(deployment.get(field)):
            gaps.append(f"test部署证据{field}无效")

    qa = item.get("qaEvidence")
    if not isinstance(qa, dict):
        gaps.append("缺少结构化QA证据")
        return gaps
    if qa.get("schemaVersion") != QA_SCHEMA or qa.get("sourceVerified") is not True:
        gaps.append("QA证据schema或来源校验无效")
    for field, expected in (
        ("projectId", project_id),
        ("iterationId", iteration_id),
        ("requirementId", requirement_id),
        ("testTaskId", test_task_id),
    ):
        if not expected or str(qa.get(field) or "") != expected:
            gaps.append(f"QA证据{field}不一致")
    for field in ("testPlan", "caseRun", "report"):
        value = qa.get(field)
        if not isinstance(value, dict) or not valid_ref(value.get("id")) or not valid_ref(value.get("url")):
            gaps.append(f"QA证据{field}缺ID或URL")
    counts = qa.get("caseCounts")
    if not isinstance(counts, dict):
        gaps.append("QA证据缺结构化用例计数")
    else:
        try:
            normalized_counts = {
                key: as_count(counts, key)
                for key in ("total", "passed", "failed", "blocked", "unexecuted")
            }
            if normalized_counts["total"] != sum(
                normalized_counts[key]
                for key in ("passed", "failed", "blocked", "unexecuted")
            ):
                gaps.append("QA用例计数无法闭合")
            for key, label in (
                ("failed", "失败"),
                ("blocked", "阻塞"),
                ("unexecuted", "未执行"),
            ):
                if normalized_counts[key]:
                    gaps.append(f"QA{label}用例={normalized_counts[key]}")
        except ValueError as error:
            gaps.append(str(error))
    if not valid_ref(qa.get("manifestSha256")) or len(str(qa.get("manifestSha256"))) != 64:
        gaps.append("QA证据清单哈希无效")
    qa_deployment = qa.get("testDeployment")
    if not isinstance(qa_deployment, dict):
        gaps.append("QA证据缺testDeployment")
    else:
        for field in ("executionId", "deployedVersion", "evidenceUrl"):
            if str(qa_deployment.get(field) or "") != str(deployment.get(field) or ""):
                gaps.append(f"QA证据与test部署{field}不一致")

    bugs = item.get("bugs")
    if not isinstance(bugs, list):
        gaps.append("bugs必须是完整关联Bug数组（无Bug时传空数组）")
        return gaps
    normalized_bug_snapshot: list[dict[str, str]] = []
    approvals = qa.get("riskApprovals")
    if not isinstance(approvals, dict):
        approvals = {}
    for bug in bugs:
        if not isinstance(bug, dict) or not valid_ref(bug.get("id")):
            gaps.append("关联Bug缺少有效ID")
            continue
        bug_id = str(bug.get("id"))
        bug_serial = str(bug.get("serialNumber") or bug_id)
        bug_status = str(bug.get("status") or "")
        retest = bug.get("retestEvidence")
        retest_version = ""
        retest_key = ""
        if isinstance(retest, dict):
            retest_version = str(retest.get("deployedVersion") or "")
            retest_key = str(retest.get("idempotencyKey") or "")
        normalized_bug_snapshot.append(
            {
                "id": bug_id,
                "serialNumber": bug_serial,
                "status": bug_status,
                "retestDeployedVersion": retest_version,
                "retestIdempotencyKey": retest_key,
            }
        )
        if bug_status == "暂不修复":
            approval = approvals.get(bug_serial.upper())
            if not isinstance(approval, dict) or not valid_ref(
                approval.get("approver")
            ) or not valid_ref(approval.get("evidence")):
                gaps.append(f"Bug {bug_serial}暂不修复缺批准证据")
            continue
        if bug_status != "已关闭":
            gaps.append(f"Bug {bug_serial}仍为活动状态：{bug_status or '(空)'}")
            continue
        if not isinstance(retest, dict) or retest.get("schemaVersion") != BUG_RETEST_SCHEMA:
            gaps.append(f"Bug {bug_serial}缺逐条复测证据")
            continue
        if str(retest.get("result") or "").lower() != "passed" or str(
            retest.get("environment") or ""
        ).lower() != "test":
            gaps.append(f"Bug {bug_serial}复测未通过或环境非test")
        if str(retest.get("deployedVersion") or "") != str(deployment.get("deployedVersion") or ""):
            gaps.append(f"Bug {bug_serial}复测版本与test部署不一致")
        for field in (
            "caseId",
            "testExecutionId",
            "evidence",
            "verifiedBy",
            "verifiedAt",
            "idempotencyKey",
        ):
            if not valid_ref(retest.get(field)):
                gaps.append(f"Bug {bug_serial}复测证据{field}无效")
    normalized_bug_snapshot.sort(key=lambda value: value["id"])
    expected_bug_snapshot = qa.get("bugSnapshot")
    if expected_bug_snapshot != normalized_bug_snapshot:
        gaps.append("QA证据Bug快照与发布时实时关联Bug不一致")
    snapshot_digest = hashlib.sha256(
        json.dumps(normalized_bug_snapshot, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()
    if qa.get("bugSnapshotSha256") != snapshot_digest:
        gaps.append("QA证据Bug快照哈希不一致")
    return gaps


def qa_gaps(item: dict[str, Any]) -> list[str]:
    gaps: list[str] = []
    if item.get("requirementStatus") != "测试完成":
        gaps.append("需求状态不是测试完成")
    if item.get("testTaskStatus") != "已完成":
        gaps.append("测试任务不是已完成")
    gaps.extend(structured_evidence_gaps(item))
    return gaps


def classify(data: dict[str, Any]) -> dict[str, Any]:
    project_id = str(data.get("projectId") or "").strip()
    iteration_id = str(data.get("iterationId") or "").strip()
    if not project_id or not iteration_id:
        raise ValueError("projectId和iterationId不能为空")
    selected_raw = data.get("selectedRequirementIds")
    items_raw = data.get("iterationRequirements")
    if not isinstance(selected_raw, list) or not selected_raw:
        raise ValueError("selectedRequirementIds必须是非空数组")
    if not isinstance(items_raw, list):
        raise ValueError("iterationRequirements必须是数组")
    selected = [str(value).strip() for value in selected_raw]
    if any(not value for value in selected) or len(selected) != len(set(selected)):
        raise ValueError("选入需求编号不能为空或重复")
    selected_set = set(selected)

    items: dict[str, dict[str, Any]] = {}
    duplicate_ids: list[str] = []
    for raw in items_raw:
        if not isinstance(raw, dict):
            raise ValueError("iterationRequirements每项必须是对象")
        requirement_id = str(raw.get("id") or "").strip()
        if not requirement_id:
            raise ValueError("需求id不能为空")
        if requirement_id in items:
            duplicate_ids.append(requirement_id)
        items[requirement_id] = raw

    groups: dict[str, list[dict[str, Any]]] = {key: [] for key in "ABCD"}
    for duplicate in sorted(set(duplicate_ids)):
        groups["D"].append({"id": duplicate, "reasons": ["迭代快照重复编号"]})

    missing = sorted(selected_set - set(items))
    for requirement_id in missing:
        groups["D"].append({"id": requirement_id, "reasons": ["选入编号不在迭代快照"]})

    for requirement_id, item in items.items():
        reasons: list[str] = []
        formal = item.get("formallyInIteration") is True
        if str(item.get("projectId") or "") != project_id:
            reasons.append("跨项目")
        if str(item.get("iterationId") or "") != iteration_id:
            reasons.append("跨迭代")
        if not formal:
            reasons.append("缺正式迭代关系")
        if item.get("relationConflict") is True:
            reasons.append("正式关系冲突")

        selected_for_batch = requirement_id in selected_set
        deferred = item.get("formallyDeferred") is True
        if selected_for_batch and deferred:
            reasons.append("同时选入与延期")
        if reasons:
            groups["D"].append({"id": requirement_id, "reasons": reasons})
            continue

        if not selected_for_batch:
            groups["B"].append(
                {
                    "id": requirement_id,
                    "reason": str(item.get("deferredReason") or "本批未选入"),
                }
            )
            continue

        gaps = qa_gaps(item)
        if gaps:
            groups["C"].append({"id": requirement_id, "reasons": gaps})
        else:
            groups["A"].append({"id": requirement_id})

    blocking = not groups["A"] or bool(groups["C"] or groups["D"])
    return {
        "ok": not blocking,
        "blocking": blocking,
        "projectId": project_id,
        "iterationId": iteration_id,
        "A_releaseScope": groups["A"],
        "B_deferredNonBlocking": groups["B"],
        "C_selectedIncomplete": groups["C"],
        "D_anomalies": groups["D"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="离线判定A/B/C/D发布范围")
    parser.add_argument("--input", default="-", help="JSON文件；- 表示stdin")
    args = parser.parse_args()
    try:
        result = classify(load_json(args.input))
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False, indent=2))
        raise SystemExit(2) from error
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["ok"] else 3)


if __name__ == "__main__":
    main()
