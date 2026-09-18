#!/usr/bin/env python3
"""Create an auditable QA-to-development repair request for one Bug.

This command only appends a structured request comment and reads it back.  It
does not edit code and cannot move the Bug to ``已修复`` or ``暂不修复``.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

import yunxiao_cli_runtime as core


SCHEMA = "oneos.test-bug-repair-request/v1"
PREFIX = "【测试缺陷修复请求】"
SECRET_RE = re.compile(r"(?i)(access[_-]?token|authorization|password|secret|cookie|private[_-]?key|otp)")


def text(value: Any) -> str:
    return "" if value is None or isinstance(value, (dict, list)) else str(value).strip()


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


def rows(value: Any) -> list[dict[str, Any]]:
    value = core.unwrap(value)
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        for key in ("items", "workItems", "data", "result", "records"):
            child = value.get(key)
            if isinstance(child, list):
                return [item for item in child if isinstance(item, dict)]
    return []


def status_name(item: dict[str, Any]) -> str:
    status = item.get("status")
    if isinstance(status, dict):
        return text(status.get("displayName") or status.get("name"))
    return text(status)


def current_user(executable: str) -> dict[str, Any]:
    value = core.unwrap(core.run_devops(executable, ["base-get-user-by-token"]))
    if not isinstance(value, dict) or not text(value.get("id")):
        raise core.AdapterError("当前登录测试用户回读失败。")
    return value


def person_id(item: dict[str, Any], field: str) -> str:
    value = item.get(field)
    if isinstance(value, dict):
        return text(value.get("id") or value.get("identifier"))
    return text(value)


def load_object(path: str) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise core.AdapterError(f"{path}必须是JSON对象。")
    return value


def validate_evidence(value: dict[str, Any], bug_serial: str, test_task: str) -> dict[str, Any]:
    if value.get("schemaVersion") not in {None, "oneos.test-bug-evidence/v1"}:
        raise core.AdapterError("缺陷证据schema不受支持。")
    actual = text(value.get("actual"))
    expected = text(value.get("expected"))
    steps = value.get("steps")
    evidence = value.get("evidence")
    if not actual or not expected or not isinstance(steps, list) or not steps:
        raise core.AdapterError("缺陷证据必须包含steps、actual和expected。")
    if not isinstance(evidence, list) or not evidence:
        raise core.AdapterError("缺陷证据必须至少包含一个可回读证据引用。")
    if any(not isinstance(item, dict) or not text(item.get("type")) or not text(item.get("ref"))
           for item in evidence):
        raise core.AdapterError("evidence中的每项必须包含type和ref。")
    serialized = json.dumps(value, ensure_ascii=False)
    if SECRET_RE.search(serialized):
        raise core.AdapterError("缺陷证据不得包含凭据、Cookie、Token或OTP。")
    return {
        "schemaVersion": "oneos.test-bug-evidence/v1",
        "bugSerialNumber": bug_serial,
        "testTask": test_task,
        "environment": text(value.get("environment") or "test"),
        "steps": [text(item) for item in steps],
        "actual": actual,
        "expected": expected,
        "evidence": evidence,
        "diagnosis": value.get("diagnosis") if isinstance(value.get("diagnosis"), dict) else {
            "classification": "待确认", "confidence": "unknown", "basis": []
        },
    }


def resolve_bug(executable: str, project_id: str, serial_number: str) -> dict[str, Any]:
    matches: list[dict[str, Any]] = []
    for page in range(1, 10001):
        page_rows = rows(core.run_devops(executable, [
            "projex-search-workitems", "--category", "Bug", "--space-id", project_id,
            "--space-type", "Project", "--page", str(page), "--per-page", "200", "--sort", "asc",
        ]))
        matches.extend(item for item in page_rows
                       if text(item.get("serialNumber")).upper() == serial_number.upper())
        if len(page_rows) < 200:
            break
    ids = {text(item.get("id")) for item in matches if text(item.get("id"))}
    if len(ids) != 1:
        raise core.AdapterError(f"Bug {serial_number}无法在项目中唯一解析。")
    bug = core.unwrap(core.run_devops(executable, ["projex-get-workitem", "--id", next(iter(ids))]))
    if not isinstance(bug, dict) or text(bug.get("serialNumber")).upper() != serial_number.upper():
        raise core.AdapterError("Bug编号官方回读不一致。")
    return bug


def resolve_test_task(executable: str, project_id: str, value: str) -> dict[str, Any]:
    if value.startswith("【测试】"):
        title = value
        serial_number = ""
    else:
        title = ""
        serial_number = value
    matches: list[dict[str, Any]] = []
    for page in range(1, 10001):
        page_rows = rows(core.run_devops(executable, [
            "projex-search-workitems", "--category", "Task", "--space-id", project_id,
            "--space-type", "Project", "--page", str(page), "--per-page", "200", "--sort", "asc",
        ]))
        for item in page_rows:
            if not text(item.get("subject")).startswith("【测试】"):
                continue
            if serial_number and text(item.get("serialNumber")).upper() == serial_number.upper():
                matches.append(item)
            elif title and text(item.get("subject")) == title:
                matches.append(item)
        if len(page_rows) < 200:
            break
    ids = {text(item.get("id")) for item in matches if text(item.get("id"))}
    if len(ids) != 1:
        raise core.AdapterError(f"测试任务{value}无法唯一解析。")
    return core.unwrap(core.run_devops(executable, ["projex-get-workitem", "--id", next(iter(ids))]))


def relation_ids(executable: str, workitem_id: str) -> set[str]:
    value = core.run_devops(executable, [
        "projex-list-workitem-relation-records", "--id", workitem_id,
        "--relation-type", "ASSOCIATED",
    ])
    return {text(item.get("resourceId") or item.get("relatedWorkitemId")) for item in rows(value)}


def comment_payload(request: dict[str, Any]) -> str:
    human = "\n".join([
        PREFIX,
        f"Bug：{request['bugSerialNumber']}",
        f"测试任务：{request['testTask']}",
        f"修复说明：{request['description']}",
        "诊断：" + text((request.get("evidence") or {}).get("diagnosis", {}).get("classification")),
        "请开发侧通过特殊修复通道接收；状态只能由开发侧在代码合并/暂不修复证据核验后收口。",
        f"<!-- {json.dumps(request, ensure_ascii=False, sort_keys=True)} -->",
    ])
    return human


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--bug", required=True, help="Bug编号，例如ONEOS-123")
    parser.add_argument("--test-task", required=True, help="测试任务编号")
    parser.add_argument("--evidence", required=True, help="缺陷证据JSON")
    parser.add_argument("--description", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()
    try:
        executable = core.find_aliyun()
        core.require_auth_env()
        user = current_user(executable)
        bug = resolve_bug(executable, args.project_id, args.bug)
        test = resolve_test_task(executable, args.project_id, args.test_task)
        if text(test.get("id")) not in relation_ids(executable, text(bug.get("id"))):
            raise core.AdapterError("Bug未正式ASSOCIATED当前【测试】任务，拒绝进入修复通道。")
        if status_name(bug) not in {"待确认", "处理中", "再次打开"}:
            raise core.AdapterError(f"Bug当前状态={status_name(bug)}，不允许重复发起修复请求。")
        if not text(args.description):
            raise core.AdapterError("修复说明不能为空。")
        evidence = validate_evidence(load_object(args.evidence), args.bug, args.test_task)
        request = {
            "schemaVersion": SCHEMA,
            "bugSerialNumber": args.bug,
            "bugId": text(bug.get("id")),
            "projectId": args.project_id,
            "testTask": args.test_task,
            "testTaskId": text(test.get("id")),
            "description": args.description.strip(),
            "evidence": evidence,
            "evidenceHash": digest(evidence),
            "requestedBy": user,
            "requestedAt": core.now_utc(),
            "status": "requested",
        }
        request["idempotencyKey"] = f"test-bug-repair:{args.bug}:{request['evidenceHash']}"
        body = comment_payload(request)
        created = core.unwrap(core.run_devops(executable, [
            "projex-create-workitem-comment", "--id", text(bug.get("id")), "--content", body,
        ]))
        comments = rows(core.run_devops(executable, [
            "projex-list-workitem-comments", "--id", text(bug.get("id")),
        ]))
        found = any(request["idempotencyKey"] in json.dumps(item, ensure_ascii=False) for item in comments)
        if not found:
            raise core.AdapterError("修复请求评论写入后未能官方回读。")
        receipt = {"schema": SCHEMA, "result": "requested", "request": request,
                   "comment": created, "readBack": True}
        if args.output:
            Path(args.output).write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(receipt, ensure_ascii=False, indent=2))
        return 0
    except (core.AdapterError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"schema": SCHEMA, "result": "blocked", "error": core.scrub(str(exc))},
                         ensure_ascii=False, indent=2), file=sys.stderr)
        return 69


if __name__ == "__main__":
    raise SystemExit(main())
