#!/usr/bin/env python
"""按发版任务执行生产后产品验收；写操作前必须先 --dry-run。"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import yunxiao_cli_pm as pm
import yunxiao_cli_runtime as core

ACCEPT_START = "<!-- YUNXIAOPM_ACCEPTANCE_START -->"
ACCEPT_END = "<!-- YUNXIAOPM_ACCEPTANCE_END -->"


def load_session() -> str:
    """返回官方 aliyun CLI 可执行文件；鉴权只读取环境变量。"""
    executable = core.find_aliyun()
    core.require_auth_env()
    return executable


def get_item(executable: str, workitem_id: str) -> dict[str, Any]:
    return pm.get_workitem(executable, workitem_id)


def document(item: dict[str, Any]) -> str:
    value = item.get("document")
    if isinstance(value, dict):
        return str(value.get("content") or "")
    return str(item.get("description") or "")


def item_id(item: dict[str, Any]) -> str:
    value = str(item.get("id") or item.get("identifier") or "")
    if not value:
        raise RuntimeError("工作项内部ID为空")
    return value


def status(item: dict[str, Any]) -> tuple[str, str]:
    value = item.get("status") or item.get("workitemStatus") or {}
    if not isinstance(value, dict):
        raise RuntimeError(f"{item.get('identifier')}状态结构无效")
    name = str(value.get("displayName") or value.get("name") or "")
    identifier = str(value.get("id") or value.get("identifier") or "")
    if not name or not identifier:
        raise RuntimeError(f"{item.get('identifier')}状态名称或ID为空")
    return name, identifier


def serial(item: dict[str, Any]) -> str:
    raw = str(item.get("serialNumber") or item.get("identifier") or "").strip()
    if not raw or "-" in raw:
        return raw
    space = item.get("space")
    code = (
        str(space.get("customCode") or "").strip()
        if isinstance(space, dict)
        else ""
    )
    return f"{code}-{raw}" if code and raw.isdigit() else raw


def associated_full(
    executable: str, workitem_id: str
) -> list[dict[str, Any]]:
    ids = pm.relation_ids(executable, workitem_id, "ASSOCIATED")
    return [get_item(executable, identifier) for identifier in ids]


def is_requirement(item: dict[str, Any]) -> bool:
    category = str(item.get("category") or item.get("categoryIdentifier") or item.get("categoryId") or "").lower()
    type_text = json.dumps(item.get("workitemType") or {}, ensure_ascii=False)
    return category in {"req", "requirement"} or "需求" in type_text


def is_bug(item: dict[str, Any]) -> bool:
    category = str(item.get("category") or item.get("categoryIdentifier") or item.get("categoryId") or "").lower()
    type_text = json.dumps(item.get("workitemType") or {}, ensure_ascii=False)
    return category in {"bug", "defect"} or "缺陷" in type_text or "Bug" in type_text


def is_completed_bug(item: dict[str, Any]) -> bool:
    return status(item)[0] in {"已完成", "已关闭"}


def is_delivery(item: dict[str, Any]) -> bool:
    return str(item.get("subject") or "").startswith("【交付】")


def resolve_acceptance_scope(
    executable: str, release_id: str
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """解析验收范围：发版→需求，或发版→【交付】→需求。"""
    release_related = associated_full(executable, release_id)
    standalone_bugs = [item for item in release_related if is_bug(item)]
    requirements = [item for item in release_related if is_requirement(item)]
    deliveries: list[dict[str, Any]] = []

    if requirements:
        for requirement in requirements:
            candidates = [
                item
                for item in associated_full(executable, item_id(requirement))
                if is_delivery(item)
            ]
            if len(candidates) != 1:
                raise RuntimeError(
                    f"需求{serial(requirement)}唯一交付命中数={len(candidates)}"
                )
            deliveries.append(candidates[0])
        return requirements, deliveries, standalone_bugs

    delivery_candidates = [item for item in release_related if is_delivery(item)]
    if not delivery_candidates:
        if standalone_bugs:
            return [], [], standalone_bugs
        raise RuntimeError("发版任务未正式关联产品需求或【交付】")

    seen_req: set[str] = set()
    for delivery in delivery_candidates:
        reqs = [
            item
            for item in associated_full(executable, item_id(delivery))
            if is_requirement(item)
        ]
        if len(reqs) != 1:
            raise RuntimeError(
                f"交付{serial(delivery)}唯一需求命中数={len(reqs)}"
            )
        req_id = item_id(reqs[0])
        if req_id in seen_req:
            raise RuntimeError(
                f"交付{serial(delivery)}与其它交付指向同一需求{serial(reqs[0])}"
            )
        seen_req.add(req_id)
        requirements.append(reqs[0])
        deliveries.append(delivery)
    return requirements, deliveries, standalone_bugs


def replace_block(original: str, block: str) -> str:
    start = original.find(ACCEPT_START)
    end = original.find(ACCEPT_END)
    if start >= 0 and end >= start:
        end += len(ACCEPT_END)
        return original[:start] + block + original[end:]
    return original + ("" if not original.strip() else "\n") + block


def set_document(
    executable: str, workitem_id: str, content: str
) -> None:
    current = get_item(executable, workitem_id)
    pm.update_item(
        executable,
        workitem_id,
        {"description": content, "formatType": current.get("formatType") or "RICHTEXT"},
    )


def type_id(item: dict[str, Any]) -> str:
    value = item.get("workitemType") or item.get("workItemType") or {}
    identifier = str(
        value.get("id") or value.get("identifier") or item.get("workitemTypeId") or ""
    ) if isinstance(value, dict) else str(item.get("workitemTypeId") or "")
    if not identifier:
        raise RuntimeError(f"{serial(item)}工作项类型ID为空")
    return identifier


def list_next_statuses(
    executable: str, item: dict[str, Any]
) -> list[tuple[str, str]]:
    project_id = pm.item_project_id(item)
    result = core.unwrap(core.run_devops(executable, [
        "projex-get-workitem-workflow", "--project-id", project_id,
        "--id", type_id(item),
    ]))
    result = result.get("statuses") if isinstance(result, dict) else []
    rows: list[tuple[str, str]] = []
    for choice in result if isinstance(result, list) else []:
        if not isinstance(choice, dict):
            continue
        value = choice.get("status") if isinstance(choice.get("status"), dict) else choice
        if not isinstance(value, dict):
            continue
        name = str(
            value.get("displayName") or value.get("name") or value.get("statusName") or ""
        )
        identifier = value.get("id") or value.get("identifier") or value.get("statusIdentifier")
        if name and identifier:
            rows.append((name, str(identifier)))
    return rows


def next_status_id(
    executable: str,
    item: dict[str, Any],
    target_name: str,
) -> str:
    current_name, _ = status(item)
    matches = [identifier for name, identifier in list_next_statuses(executable, item) if name == target_name]
    if len(matches) != 1:
        raise RuntimeError(
            f"{serial(item)}工作流中无法唯一解析目标状态{target_name}（当前{current_name}）"
        )
    return matches[0]


def transit(
    executable: str, item: dict[str, Any], target_name: str
) -> None:
    target_id = next_status_id(executable, item, target_name)
    updated = pm.update_item(executable, item_id(item), {"status": target_id})
    if status(updated)[0] != target_name:
        raise RuntimeError(f"{serial(item)}状态流转后回读不是{target_name}")


def is_acceptance_done(item: dict[str, Any]) -> bool:
    name = status(item)[0]
    if is_requirement(item):
        return name in {"已完成", "已关闭"}
    return name == "已完成"


def transit_to_acceptance_done(executable: str, item: dict[str, Any]) -> None:
    """按项目真实下一状态推进到验收终态；需求优先已完成否则已关闭，发版允许经处理中中转。"""
    live = get_item(executable, item_id(item))
    if is_acceptance_done(live):
        return
    preferred = ["已完成", "已关闭"] if is_requirement(live) else ["已完成"]
    next_names = {name for name, _ in list_next_statuses(executable, live)}
    # 发版的真实关闭顺序固定为 发布完成→处理中→已完成。
    if (not is_requirement(live)) and status(live)[0] == "发布完成" and "处理中" in next_names:
        transit(executable, live, "处理中")
        mid = get_item(executable, item_id(live))
        mid_next = {name for name, _ in list_next_statuses(executable, mid)}
        if "已完成" not in mid_next:
            raise RuntimeError(f"{serial(mid)}经处理中后无法流转到已完成")
        transit(executable, mid, "已完成")
        done = get_item(executable, item_id(live))
        if not is_acceptance_done(done):
            raise RuntimeError(f"{serial(done)}中转后未达已完成：{status(done)[0]}")
        return
    for target in preferred:
        if target in next_names:
            transit(executable, live, target)
            done = get_item(executable, item_id(live))
            if not is_acceptance_done(done):
                raise RuntimeError(f"{serial(done)}流转后未达验收终态：{status(done)[0]}")
            return
    raise RuntimeError(
        f"{serial(live)}当前={status(live)[0]}，下一状态={sorted(next_names)}，无法到达验收终态"
    )


def acceptance_block(
    args,
    key: str,
    scope: list[str],
    production_execution_id: str,
    standalone_completed_bugs: list[str],
    component_scope: list[dict[str, Any]] | None = None,
) -> str:
    when = datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds")
    conclusion = "通过" if args.action == "pass" else "不通过"
    reason = args.reason if args.action == "fail" else "无"
    payload = {
        "schemaVersion": "oneos.product-acceptance/v1",
        "releaseTaskId": args.release_sn,
        "productionExecutionId": production_execution_id,
        "conclusion": conclusion,
        "acceptor": args.acceptor,
        "evidence": args.evidence,
        "reason": reason,
        "acceptedScope": scope,
        "componentScope": component_scope or [],
        "scopeMode": "component" if component_scope else "full_release",
        "standaloneCompletedBugs": standalone_completed_bugs,
        "recordedAt": when,
        "idempotencyKey": key,
    }
    if component_scope:
        start = f"<!-- YUNXIAOPM_COMPONENT_ACCEPTANCE:{key}:START -->"
        end = f"<!-- YUNXIAOPM_COMPONENT_ACCEPTANCE:{key}:END -->"
    else:
        start, end = ACCEPT_START, ACCEPT_END
    return (
        f"{start}<h2>生产后产品验收（YunxiaoPM）</h2><pre>"
        + html.escape(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        + f"</pre>{end}"
    )


def read_component_scope(path: Path | None) -> list[dict[str, Any]]:
    if path is None:
        return []
    value = json.loads(path.read_text(encoding="utf-8"))
    rows = value.get("components") if isinstance(value, dict) else value
    if not isinstance(rows, list) or not rows:
        raise RuntimeError("范围清单必须是非空数组或包含非空components数组")
    required = ("deliveryUnitId", "componentId", "deploymentTargetId", "productionVersion")
    result: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            raise RuntimeError(f"范围清单第{index}项不是对象")
        missing = [name for name in required if not str(row.get(name) or "").strip()]
        if missing:
            raise RuntimeError(f"范围清单第{index}项缺少字段：{','.join(missing)}")
        normalized = {name: str(row[name]).strip() for name in required}
        branches = row.get("branchInstanceIds") or []
        if not isinstance(branches, list):
            raise RuntimeError(f"范围清单第{index}项branchInstanceIds必须是数组")
        normalized["branchInstanceIds"] = sorted({str(item).strip() for item in branches if str(item).strip()})
        identity = (normalized["deliveryUnitId"], normalized["componentId"], normalized["deploymentTargetId"])
        if identity in seen:
            raise RuntimeError(f"范围清单存在重复组件/目标：{identity}")
        seen.add(identity)
        result.append(normalized)
    return sorted(result, key=lambda item: (item["deliveryUnitId"], item["componentId"], item["deploymentTargetId"]))


def followup_paths(args: argparse.Namespace, key: str) -> tuple[Path, Path]:
    base = core.output_dir()
    preflight = args.followup_preflight or base / f"pm-accept-followup-{key}-preflight.json"
    receipt = args.followup_receipt or base / f"pm-accept-followup-{key}-receipt.json"
    return Path(preflight), Path(receipt)


def should_auto_followup(
    action: str, component_scope: list[dict[str, Any]], source_sprint_id: str | None
) -> bool:
    return action == "pass" and not component_scope and bool(source_sprint_id)


def linked_sprint_id(item: dict[str, Any]) -> str:
    value = item.get("sprint")
    if isinstance(value, dict):
        return str(value.get("id") or value.get("identifier") or "")
    if isinstance(value, list):
        ids = {
            str(row.get("id") or row.get("identifier") or "")
            for row in value if isinstance(row, dict)
        } - {""}
        if len(ids) > 1:
            raise RuntimeError(f"{serial(item)}关联多个迭代，无法冻结验收来源")
        return next(iter(ids), "")
    return ""


def acceptance_source_sprint_id(
    deliveries: list[dict[str, Any]],
    standalone_bugs: list[dict[str, Any]],
    explicit: str | None,
) -> str | None:
    """从本批交付（仅独立Bug批次则从Bug）冻结唯一来源迭代。"""
    candidates = deliveries if deliveries else standalone_bugs
    known = {linked_sprint_id(item) for item in candidates} - {""}
    if len(known) > 1:
        raise RuntimeError(f"本批工作项跨多个来源迭代，无法自动补建：{sorted(known)}")
    inferred = next(iter(known), "")
    if explicit and inferred and explicit != inferred:
        raise RuntimeError("显式来源迭代与本批工作项实际迭代不一致")
    return inferred or explicit or None


def is_web_version_sprint(executable: str, project_id: str, sprint_identifier: str) -> bool:
    source = pm.get_sprint(executable, project_id, sprint_identifier)
    try:
        return pm.parse_versioned_sprint(source)["endpoint"] == "Web"
    except core.AdapterError:
        return False


def followup_plan(
    executable: str,
    args: argparse.Namespace,
    key: str,
    project_id: str,
) -> tuple[dict[str, Any], Path, Path]:
    """冻结或读取同一验收批次的来源迭代与两期目标。"""
    if not args.source_sprint_id:
        raise RuntimeError("整批验收通过必须提供--source-sprint-id，作为本批Web来源迭代")
    preflight_path, receipt_path = followup_paths(args, key)
    if preflight_path.exists():
        value = json.loads(preflight_path.read_text(encoding="utf-8"))
        if (
            value.get("schema") != pm.SCHEMA
            or value.get("command") != "preflight-followup-sprints"
            or value.get("preflightHash")
            != pm.canonical_hash(value, {"preflightHash"})
        ):
            raise RuntimeError("后续迭代冻结计划格式或哈希无效")
        scope = value.get("liveScope") or {}
        if (
            str((scope.get("project") or {}).get("id") or "") != project_id
            or str((scope.get("source") or {}).get("id") or "") != args.source_sprint_id
            or str(scope.get("idempotencyKey") or "") != key
        ):
            raise RuntimeError("后续迭代冻结计划与本次验收批次不一致")
        return value, preflight_path, receipt_path
    if not args.dry_run:
        raise RuntimeError("缺少后续迭代冻结计划；请先以相同参数执行--dry-run并确认Plan")
    value = pm.write_followup_preflight(
        executable, project_id, args.source_sprint_id, key, preflight_path,
    )
    return value, preflight_path, receipt_path


def followup_plan_output(
    value: dict[str, Any], preflight_path: Path, receipt_path: Path
) -> dict[str, Any]:
    scope = value["liveScope"]
    return {
        "trigger": "full_batch_pass_and_all_close_readback_success",
        "source": scope["source"],
        "targets": scope["targets"],
        "boundaries": {
            "attachWorkitems": False,
            "createDevOrTestTasks": False,
            "changeOldSprintDatesOrOwners": False,
        },
        "preflightPath": str(preflight_path),
        "preflightHash": value["preflightHash"],
        "receiptPath": str(receipt_path),
    }


def apply_followup_result(
    executable: str, preflight_path: Path, receipt_path: Path
) -> dict[str, Any]:
    try:
        receipt = pm.apply_followup_preflight(executable, preflight_path, receipt_path)
        return {
            "ok": True,
            "resumable": False,
            "receiptPath": str(receipt_path),
            "receipt": receipt,
        }
    except (core.AdapterError, RuntimeError, OSError, ValueError, json.JSONDecodeError) as error:
        return {
            "ok": False,
            "resumable": True,
            "preflightPath": str(preflight_path),
            "receiptPath": str(receipt_path),
            "error": core.scrub(str(error)),
        }


def validate_resume_evidence(
    release: dict[str, Any],
    requirements: list[dict[str, Any]],
    deliveries: list[dict[str, Any]],
    standalone_bugs: list[dict[str, Any]],
    key: str,
) -> bool:
    """首次验收允许已完成独立Bug无产品验收键；整批已关闭重跑则全部必须一致。"""
    acceptance_items = [release, *requirements, *deliveries]
    for item in acceptance_items:
        if is_acceptance_done(item) and key not in document(item):
            raise RuntimeError(f"{serial(item)}已完成但缺少本次验收幂等证据，拒绝接续")
    all_closed = is_acceptance_done(release) and all(
        is_acceptance_done(item) for item in [*requirements, *deliveries]
    )
    if all_closed:
        missing = [serial(item) for item in standalone_bugs if key not in document(item)]
        if missing:
            raise RuntimeError(f"整批已关闭但独立Bug缺少本次验收幂等证据：{missing}")
    return all_closed


def main() -> None:
    parser = argparse.ArgumentParser(description="执行生产后产品验收")
    parser.add_argument("action", choices=("pass", "fail"))
    parser.add_argument("--release-id", required=True, help="云效内部identifier")
    parser.add_argument("--release-sn", required=True, help="展示编号")
    parser.add_argument("--acceptor", required=True)
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--reason", default="")
    parser.add_argument("--scope-file", type=Path, help="可选组件/部署目标范围；提供后只记录局部验收，不关闭整批")
    parser.add_argument("--source-sprint-id", help="整批验收通过所属的冻结Web来源迭代内部ID")
    parser.add_argument("--followup-preflight", type=Path, help="后两期迭代冻结计划路径")
    parser.add_argument("--followup-receipt", type=Path, help="后两期迭代补建回执路径")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.action == "fail" and not args.reason.strip():
        parser.error("fail必须提供--reason")

    try:
        session = load_session()
        release = get_item(session, args.release_id)
        if serial(release).split("-")[-1] != args.release_sn.split("-")[-1]:
            raise RuntimeError("发版任务编号与内部ID回读不一致")
        release_status, _ = status(release)
        allowed_release_states = (
            {"发布完成", "已完成"}
            if args.action == "pass"
            else {"发布完成", "发布失败"}
        )
        if release_status not in allowed_release_states:
            raise RuntimeError(
                f"发版任务状态={release_status}，期望{sorted(allowed_release_states)}"
            )
        # 产品验收不再硬依赖 oneos.release-production/v1 受管生产证据区块
        component_scope = read_component_scope(args.scope_file)
        component_scope_hash = hashlib.sha256(
            json.dumps(component_scope, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        requirements, deliveries, standalone_bugs = resolve_acceptance_scope(
            session, args.release_id
        )
        project_id = pm.item_project_id(release)
        detected_source_sprint_id: str | None = None
        followup_skip: dict[str, Any] | None = None
        if args.action == "pass" and not component_scope:
            detected_source_sprint_id = acceptance_source_sprint_id(
                deliveries, standalone_bugs, args.source_sprint_id,
            )
            if detected_source_sprint_id and is_web_version_sprint(
                session, project_id, detected_source_sprint_id,
            ):
                args.source_sprint_id = detected_source_sprint_id
            else:
                followup_skip = (
                    {
                        "skippedNonWeb": True,
                        "reason": "source_sprint_is_not_a_web_version",
                        "sourceSprintId": detected_source_sprint_id,
                    }
                    if detected_source_sprint_id
                    else {
                        "unresolved": True,
                        "reason": "missing_source",
                        "requiredInput": "source_sprint_id",
                    }
                )
                args.source_sprint_id = None
        key_parts = [args.release_id, args.action, args.evidence.strip()]
        if component_scope:
            key_parts.append(component_scope_hash)
        key_source = "|".join(key_parts)
        key = "accept-" + hashlib.sha256(key_source.encode("utf-8")).hexdigest()[:20]

        followup_value: dict[str, Any] | None = None
        followup_preflight_path: Path | None = None
        followup_receipt_path: Path | None = None
        if should_auto_followup(args.action, component_scope, args.source_sprint_id):
            followup_value, followup_preflight_path, followup_receipt_path = followup_plan(
                session, args, key, project_id,
            )
        actual_scope = sorted(serial(item) for item in requirements)
        allowed_requirement_states = (
            {"发布完成", "已完成", "已关闭"} if args.action == "pass" else {"发布完成"}
        )
        for item in requirements:
            if status(item)[0] not in allowed_requirement_states:
                raise RuntimeError(
                    f"需求{serial(item)}状态={status(item)[0]}，"
                    f"期望{sorted(allowed_requirement_states)}"
                )

        allowed_delivery_states = (
            {"处理中", "已完成"} if args.action == "pass" else {"处理中"}
        )
        for item in deliveries:
            if status(item)[0] not in allowed_delivery_states:
                raise RuntimeError(
                    f"交付{serial(item)}状态={status(item)[0]}，"
                    f"期望{sorted(allowed_delivery_states)}"
                )

        for bug in standalone_bugs:
            if not is_completed_bug(bug):
                raise RuntimeError(f"无交付Bug{serial(bug)}未处于已完成/已关闭状态")
            if "oneos.bug-retest/v1" not in document(bug):
                raise RuntimeError(f"无交付Bug{serial(bug)}缺少独立复测证据")
            bug_relations = associated_full(session, item_id(bug))
            linked_deliveries = [
                item
                for item in bug_relations
                if str(item.get("subject") or "").startswith("【交付】")
            ]
            if linked_deliveries:
                raise RuntimeError(
                    f"Bug{serial(bug)}已关联交付，不应作为无交付Bug进入发版任务"
                )

        if validate_resume_evidence(
            release, requirements, deliveries, standalone_bugs, key,
        ):
            completed = {
                "ok": True,
                "acceptanceOk": True,
                "alreadyDone": True,
                "releaseTask": args.release_sn,
                "requirements": actual_scope,
                "deliveries": [serial(item) for item in deliveries],
                "standaloneCompletedBugs": [serial(item) for item in standalone_bugs],
                "idempotencyKey": key,
            }
            if should_auto_followup(args.action, component_scope, args.source_sprint_id):
                assert followup_value and followup_preflight_path and followup_receipt_path
                completed["followupSprints"] = followup_plan_output(
                    followup_value, followup_preflight_path, followup_receipt_path,
                )
                if not args.dry_run:
                    result = apply_followup_result(
                        session, followup_preflight_path, followup_receipt_path,
                    )
                    completed["followupSprints"]["apply"] = result
                    print(json.dumps(completed, ensure_ascii=False, indent=2))
                    if not result["ok"]:
                        raise SystemExit(4)
                    return
            print(json.dumps(completed, ensure_ascii=False, indent=2))
            return

        block = acceptance_block(
            args,
            key,
            actual_scope,
            "n/a",
            [serial(item) for item in standalone_bugs],
            component_scope,
        )
        requirement_transitions = [
            serial(item) for item in requirements if not is_acceptance_done(item)
        ]
        delivery_transitions = [
            serial(item) for item in deliveries if not is_acceptance_done(item)
        ]
        plan = {
            "ok": True,
            "dryRun": args.dry_run,
            "releaseTask": args.release_sn,
            "requirements": actual_scope,
            "deliveries": [serial(item) for item in deliveries],
            "standaloneCompletedBugs": [serial(item) for item in standalone_bugs],
            "conclusion": "通过" if args.action == "pass" else "不通过",
            "idempotencyKey": key,
            "scopeMode": "component" if component_scope else "full_release",
            "componentScope": component_scope,
            "wouldTransit": (
                {
                    "requirements": requirement_transitions,
                    "deliveries": delivery_transitions,
                    "releaseTask": (
                        args.release_sn if not is_acceptance_done(release) else None
                    ),
                }
                if args.action == "pass"
                else {"releaseTask": "发布完成→发布失败（流程支持时）"}
            ),
        }
        if followup_value and followup_preflight_path and followup_receipt_path:
            plan["followupSprints"] = followup_plan_output(
                followup_value, followup_preflight_path, followup_receipt_path,
            )
        elif args.action == "pass" and not component_scope:
            plan["followupSprints"] = followup_skip or {
                "unresolved": True,
                "reason": "missing_source",
                "requiredInput": "source_sprint_id",
            }
        if args.dry_run:
            print(json.dumps(plan, ensure_ascii=False, indent=2))
            return

        if component_scope:
            if args.action != "pass":
                raise RuntimeError("局部范围仅支持验收通过；验收不通过仍按整批失败回流记录")
            current_document = document(release)
            if key not in current_document:
                set_document(session, args.release_id, current_document + block)
            reread = document(get_item(session, args.release_id))
            if key not in reread:
                raise RuntimeError("局部验收事件写入后回读失败")
            cleanup_candidates = [
                {
                    "deliveryUnitId": item["deliveryUnitId"],
                    "componentId": item["componentId"],
                    "deploymentTargetId": item["deploymentTargetId"],
                    "productionVersion": item["productionVersion"],
                    "branchInstanceIds": item["branchInstanceIds"],
                    "eligibility": "COMPONENT_ACCEPTED_BRANCH_NOT_YET_DELETABLE",
                }
                for item in component_scope
            ]
            print(json.dumps(plan | {"dryRun": False, "cleanupCandidates": cleanup_candidates,
                                     "stateTransitions": "none_for_partial_acceptance"},
                             ensure_ascii=False, indent=2))
            return

        targets_by_id = {
            item_id(item): item
            for item in [release, *requirements, *deliveries, *standalone_bugs]
        }
        targets = list(targets_by_id.values())
        for item in targets:
            set_document(
                session,
                item_id(item),
                replace_block(document(item), block),
            )
            reread = document(get_item(session, item_id(item)))
            if ACCEPT_START not in reread or key not in reread:
                raise RuntimeError(f"{serial(item)}验收证据回读失败")

        if args.action == "pass":
            # 需求终态常受关联任务门禁：须先把源交付推到已完成，再关需求
            for item in deliveries:
                transit_to_acceptance_done(session, item)
            for item in requirements:
                transit_to_acceptance_done(session, item)
            transit_to_acceptance_done(session, release)
            readback = [
                get_item(session, item_id(item))
                for item in [*requirements, *deliveries, *standalone_bugs, release]
            ]
            wrong = [
                {"serialNumber": serial(item), "status": status(item)[0]}
                for item in readback
                if not is_acceptance_done(item) and not is_completed_bug(item)
            ]
            if wrong:
                raise RuntimeError(f"状态回读失败：{wrong}")
            plan["acceptanceOk"] = True
            plan["allRequiredClosuresReadBack"] = True
            if followup_preflight_path and followup_receipt_path:
                followup_result = apply_followup_result(
                    session, followup_preflight_path, followup_receipt_path,
                )
                plan["followupSprints"]["apply"] = followup_result
            else:
                followup_result = {"ok": True, **(followup_skip or {
                    "unresolved": True,
                    "reason": "missing_source",
                    "requiredInput": "source_sprint_id",
                })}
            print(json.dumps(plan | {"dryRun": False}, ensure_ascii=False, indent=2))
            if not followup_result.get("ok"):
                raise SystemExit(4)
            return
        else:
            current_release = get_item(session, item_id(release))
            state_result: dict[str, Any] = {
                "before": status(current_release)[0],
                "after": status(current_release)[0],
            }
            if status(current_release)[0] == "发布完成":
                try:
                    transit(session, current_release, "发布失败")
                    state_result["after"] = status(
                        get_item(session, item_id(release))
                    )[0]
                except RuntimeError as error:
                    state_result["notSupported"] = str(error)
            plan["releaseFailureState"] = state_result
            plan["repairHandoff"] = {
                "targetSkill": "YunxiaoQA",
                "nextCommand": (
                    f"接收发布回流：发版任务={args.release_sn}；"
                    f"触发=产品验收失败；证据={args.evidence}"
                ),
            }
        print(json.dumps(plan | {"dryRun": False}, ensure_ascii=False, indent=2))
    except (core.AdapterError, RuntimeError, OSError, ValueError, json.JSONDecodeError) as error:
        print(
            json.dumps(
                {"ok": False, "error": str(error)},
                ensure_ascii=False,
                indent=2,
            )
        )
        raise SystemExit(3) from error


if __name__ == "__main__":
    main()
