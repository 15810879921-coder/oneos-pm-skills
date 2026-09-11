#!/usr/bin/env python3
"""Build and validate append-only delivery-ledger events and guarded comment plans."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


SCHEMA = "oneos.delivery-ledger/v1"
SUITE_VERSION = "10.1.0"
SUPPORTED_SUITE_VERSIONS = {"10.0.0", SUITE_VERSION}
COMMENT_PREFIX = "【交付台账事件】"
TRANSACTION_SCHEMA = "oneos.yunxiao-cli-transaction-plan/v1"
SUITE_STATE_SCHEMA = "oneos.lifecycle-suite-state/v1"
SUITE_SKILLS = {
    "YunxiaoPM", "yunxiao-development-delivery", "development-brain",
    "YunxiaoQA", "yunxiao-release-operations",
}
EVENT_TYPES = {
    "DEVELOPMENT_STARTED", "WORK_SEGMENT_RECORDED", "COMMIT_RECORDED",
    "COMMIT_REVERTED", "MR_RECORDED", "MR_MERGED", "DEVELOPMENT_COMPLETED",
    "TEST_DEPLOYMENT_RECORDED", "ITEM_TEST_RESULT_RECORDED", "DELIVERY_ADOPTED",
    "DELIVERY_UNIT_CONSOLIDATED", "DELIVERY_MAPPING_CORRECTED",
    "DEVELOPMENT_TASK_AGGREGATED", "EXTERNAL_COMMIT_DISCOVERED",
    "BRANCH_HEAD_REWRITTEN", "PRODUCTION_BASELINE_CONFIRMED",
    "RELEASE_SCOPE_FROZEN", "MERGE_PLAN_REVISED", "PRODUCTION_MERGE_RECORDED",
    "PRODUCTION_MERGE_REVERTED", "PRODUCTION_RELEASED", "OUT_OF_BAND_PRODUCTION",
    "ACCEPTANCE_COMPLETED", "CLEANUP_AUTHORIZED", "CLEANUP_COMPLETED",
    "LEDGER_REPAIRED",
}
CHINESE_DESCRIPTION_EVENTS = {
    "COMMIT_RECORDED", "COMMIT_REVERTED", "MR_RECORDED", "DEVELOPMENT_COMPLETED",
    "EXTERNAL_COMMIT_DISCOVERED", "DELIVERY_ADOPTED", "DEVELOPMENT_TASK_AGGREGATED",
}
DESCRIPTION_FIELDS = ("修改内容", "修改原因", "影响范围", "验证情况")


def contains_chinese(value: Any) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in str(value or ""))


def validate_payload(event_type: str, payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if event_type in CHINESE_DESCRIPTION_EVENTS:
        summary = payload.get("changeSummary")
        if not isinstance(summary, dict):
            errors.append("payload.changeSummary必须包含中文修改说明")
        else:
            for field in DESCRIPTION_FIELDS:
                if not contains_chinese(summary.get(field)):
                    errors.append(f"payload.changeSummary.{field}必须为有效中文说明")
    if event_type == "DELIVERY_ADOPTED":
        for field in ("adoptionId", "formalWorkItemId", "relationEvidenceId"):
            if not str(payload.get(field) or "").strip():
                errors.append(f"DELIVERY_ADOPTED缺少{field}")
    if event_type == "DEVELOPMENT_TASK_AGGREGATED":
        for field in ("developmentTaskId", "bugIds", "branchInstanceIds"):
            value = payload.get(field)
            if not value or (field.endswith("Ids") and not isinstance(value, list)):
                errors.append(f"DEVELOPMENT_TASK_AGGREGATED缺少{field}")
    if event_type == "WORK_SEGMENT_RECORDED":
        for field in ("startedAt", "endedAt", "conversationId"):
            if not str(payload.get(field) or "").strip():
                errors.append(f"WORK_SEGMENT_RECORDED缺少{field}")
    return errors


def stable_hash(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_events(path: Path | None) -> list[dict[str, Any]]:
    if path is None:
        return []
    value = load_json(path)
    if isinstance(value, dict):
        value = value.get("events")
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise ValueError("台账文件必须是事件数组或包含events数组的对象")
    return list(value)


def validate(events: list[dict[str, Any]]) -> dict[str, Any]:
    errors: list[str] = []
    event_ids: set[str] = set()
    idempotency_keys: set[str] = set()
    previous: dict[str, Any] | None = None
    for index, event in enumerate(events):
        prefix = f"events[{index}]"
        if event.get("schemaVersion") != SCHEMA:
            errors.append(f"{prefix}.schemaVersion无效")
        if event.get("suiteVersion") not in SUPPORTED_SUITE_VERSIONS:
            errors.append(
                f"{prefix}.suiteVersion必须为受支持版本：{sorted(SUPPORTED_SUITE_VERSIONS)}"
            )
        event_id = str(event.get("eventId") or "")
        idem = str(event.get("idempotencyKey") or "")
        event_type = str(event.get("eventType") or "")
        if not event_id or event_id in event_ids:
            errors.append(f"{prefix}.eventId缺失或重复")
        if not idem or idem in idempotency_keys:
            errors.append(f"{prefix}.idempotencyKey缺失或重复")
        if event_type not in EVENT_TYPES:
            errors.append(f"{prefix}.eventType不受支持：{event_type}")
        if not event.get("deliveryUnitId") or not event.get("ledgerOwnerItemId"):
            errors.append(f"{prefix}缺少deliveryUnitId或ledgerOwnerItemId")
        payload = event.get("payload")
        if not isinstance(payload, dict):
            errors.append(f"{prefix}.payload必须是对象")
            payload = {}
        if event.get("payloadHash") != stable_hash(payload):
            errors.append(f"{prefix}.payloadHash不匹配")
        errors.extend(f"{prefix}.{message}" for message in validate_payload(event_type, payload))
        expected_previous_id = previous.get("eventId") if previous else None
        expected_previous_hash = previous.get("payloadHash") if previous else None
        if event.get("previousEventId") != expected_previous_id:
            errors.append(f"{prefix}.previousEventId链路断裂")
        if event.get("previousPayloadHash") != expected_previous_hash:
            errors.append(f"{prefix}.previousPayloadHash链路断裂")
        event_ids.add(event_id)
        idempotency_keys.add(idem)
        previous = event
    return {
        "schemaVersion": "oneos.delivery-ledger-validation/v1",
        "status": "blocked" if errors else "passed",
        "eventCount": len(events),
        "lastEventId": events[-1].get("eventId") if events else None,
        "lastPayloadHash": events[-1].get("payloadHash") if events else None,
        "errors": errors,
    }


def build_event(spec: dict[str, Any], existing: list[dict[str, Any]]) -> tuple[dict[str, Any], bool]:
    current = validate(existing)
    if current["errors"]:
        raise ValueError("已有台账校验失败：" + "；".join(current["errors"]))
    event_type = str(spec.get("eventType") or "")
    if event_type not in EVENT_TYPES:
        raise ValueError(f"eventType不受支持：{event_type}")
    delivery_unit = str(spec.get("deliveryUnitId") or "").strip()
    owner = str(spec.get("ledgerOwnerItemId") or "").strip()
    idem = str(spec.get("idempotencyKey") or "").strip()
    payload = spec.get("payload")
    if not delivery_unit or not owner or not idem or not isinstance(payload, dict):
        raise ValueError("deliveryUnitId、ledgerOwnerItemId、idempotencyKey和payload必填")
    payload_errors = validate_payload(event_type, payload)
    if payload_errors:
        raise ValueError("；".join(payload_errors))
    for event in existing:
        if event.get("idempotencyKey") == idem:
            if event.get("eventType") != event_type or event.get("payloadHash") != stable_hash(payload):
                raise ValueError("同一幂等键对应了不同事件内容")
            return event, False
    previous = existing[-1] if existing else None
    payload_hash = stable_hash(payload)
    event_id = "EVT-" + stable_hash({"owner": owner, "idempotencyKey": idem, "payloadHash": payload_hash})[:20]
    event = {
        "schemaVersion": SCHEMA,
        "suiteVersion": SUITE_VERSION,
        "eventId": event_id,
        "previousEventId": previous.get("eventId") if previous else None,
        "previousPayloadHash": previous.get("payloadHash") if previous else None,
        "idempotencyKey": idem,
        "deliveryUnitId": delivery_unit,
        "ledgerOwnerItemId": owner,
        "eventType": event_type,
        "occurredAt": str(spec.get("occurredAt") or datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds")),
        "repositoryId": spec.get("repositoryId"),
        "branchInstanceId": spec.get("branchInstanceId"),
        "sourceCommitIds": [str(value) for value in spec.get("sourceCommitIds") or []],
        "payload": payload,
        "payloadHash": payload_hash,
    }
    return event, True


def transaction_plan(work_item_id: str, serial_number: str, comment: str, event: dict[str, Any]) -> dict[str, Any]:
    guard = {"operation": "projex-get-workitem", "args": ["--id", work_item_id], "expect": {}}
    if serial_number:
        guard["expect"] = {"serialNumber": serial_number}
    return {
        "schema": TRANSACTION_SCHEMA,
        "label": f"append delivery ledger event {event['eventId']}",
        "authority": "apply",
        "idempotencyKey": event["idempotencyKey"],
        "guards": [guard],
        "actions": [{"operation": "projex-create-workitem-comment", "args": ["--id", work_item_id, "--content", comment]}],
        "verifications": [{"operation": "projex-list-workitem-comments", "args": ["--id", work_item_id]}],
    }


def validate_suite_state(value: Any) -> None:
    if not isinstance(value, dict) or value.get("schemaVersion") != SUITE_STATE_SCHEMA:
        raise ValueError(f"suite-state必须为{SUITE_STATE_SCHEMA}")
    versions = value.get("skills")
    if value.get("verified") is not True or not isinstance(versions, dict):
        raise ValueError("suite-state尚未完成安装回读")
    missing = sorted(name for name in SUITE_SKILLS if versions.get(name) != SUITE_VERSION)
    if missing:
        raise ValueError("生命周期Skill版本未对齐，禁止向云效写新台账：" + ",".join(missing))


def summary(events: list[dict[str, Any]]) -> dict[str, Any]:
    validation = validate(events)
    branches: dict[str, dict[str, Any]] = {}
    commits: set[str] = set()
    work_items: set[str] = set()
    for event in events:
        work_items.add(str(event.get("ledgerOwnerItemId")))
        commits.update(str(value) for value in event.get("sourceCommitIds") or [])
        branch_id = str(event.get("branchInstanceId") or "")
        if branch_id:
            branches[branch_id] = {
                "repositoryId": event.get("repositoryId"),
                "lastEventType": event.get("eventType"),
                "lastEventId": event.get("eventId"),
            }
    return {
        **validation,
        "deliveryUnitIds": sorted({str(event.get("deliveryUnitId")) for event in events}),
        "ledgerOwnerItemIds": sorted(work_items),
        "sourceCommitIds": sorted(commits),
        "branchInstances": branches,
    }


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="交付台账事件构建、校验和云效评论事务计划")
    sub = parser.add_subparsers(dest="command", required=True)
    validate_parser = sub.add_parser("validate")
    validate_parser.add_argument("--events", required=True, type=Path)
    summary_parser = sub.add_parser("summary")
    summary_parser.add_argument("--events", required=True, type=Path)
    append_parser = sub.add_parser("append")
    append_parser.add_argument("--event", required=True, type=Path)
    append_parser.add_argument("--existing", type=Path)
    append_parser.add_argument("--output", required=True, type=Path)
    append_parser.add_argument("--comment-output", type=Path)
    append_parser.add_argument("--transaction-plan", type=Path)
    append_parser.add_argument("--suite-state", type=Path, help="生成云效评论事务前必须提供五Skill安装回读")
    append_parser.add_argument("--work-item-id")
    append_parser.add_argument("--serial-number", default="")
    args = parser.parse_args()
    try:
        if args.command in {"validate", "summary"}:
            events = load_events(args.events)
            result = validate(events) if args.command == "validate" else summary(events)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 2 if result["status"] == "blocked" else 0
        existing = load_events(args.existing)
        spec = load_json(args.event)
        if not isinstance(spec, dict):
            raise ValueError("event必须是JSON对象")
        event, created = build_event(spec, existing)
        updated = existing if not created else [*existing, event]
        result = {"schemaVersion": SCHEMA, "events": updated}
        write_json(args.output, result)
        comment = COMMENT_PREFIX + json.dumps(event, ensure_ascii=False, separators=(",", ":"))
        if args.comment_output:
            args.comment_output.parent.mkdir(parents=True, exist_ok=True)
            args.comment_output.write_text(comment + "\n", encoding="utf-8")
        if args.transaction_plan:
            if not args.work_item_id:
                raise ValueError("生成transaction-plan时必须提供--work-item-id")
            if not args.suite_state:
                raise ValueError("生成transaction-plan时必须提供--suite-state")
            validate_suite_state(load_json(args.suite_state))
            write_json(args.transaction_plan, transaction_plan(args.work_item_id, args.serial_number, comment, event))
        print(json.dumps({"status": "created" if created else "reused", "event": event, "output": str(args.output)}, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "blocked", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 2


if __name__ == "__main__":
    sys.exit(main())
