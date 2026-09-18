#!/usr/bin/env python3
"""Validate and accept a QA test-bug repair request.

Acceptance is the development-side bridge into the existing ``修复bug`` flow.
It appends one comment after official Bug/request/owner checks and never edits
code or changes the Bug status by itself.
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


REQUEST_SCHEMA = "oneos.test-bug-repair-request/v1"
ACCEPT_SCHEMA = "oneos.development-bug-repair-acceptance/v1"
REQUEST_PREFIX = "【测试缺陷修复请求】"
ACCEPT_PREFIX = "【开发接收测试修复】"
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
        for key in ("items", "comments", "records", "data", "result"):
            child = value.get(key)
            if isinstance(child, list):
                return [item for item in child if isinstance(item, dict)]
    return []


def status_name(item: dict[str, Any]) -> str:
    value = item.get("status")
    return text(value.get("displayName") or value.get("name")) if isinstance(value, dict) else text(value)


def person_id(item: dict[str, Any], field: str) -> str:
    value = item.get(field)
    return text(value.get("id") or value.get("identifier")) if isinstance(value, dict) else text(value)


def current_user(executable: str) -> dict[str, Any]:
    value = core.unwrap(core.run_devops(executable, ["base-get-user-by-token"]))
    if not isinstance(value, dict) or not text(value.get("id")):
        raise core.AdapterError("当前登录开发用户回读失败。")
    return value


def load(path: str) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise core.AdapterError(f"{path}必须是JSON对象。")
    return value


def resolve_bug(executable: str, project_id: str, serial_number: str) -> dict[str, Any]:
    matches: list[dict[str, Any]] = []
    for page in range(1, 10001):
        value = core.run_devops(executable, [
            "projex-search-workitems", "--category", "Bug", "--space-id", project_id,
            "--space-type", "Project", "--page", str(page), "--per-page", "200", "--sort", "asc",
        ])
        page_rows = rows(value)
        matches.extend(item for item in page_rows
                       if text(item.get("serialNumber")).upper() == serial_number.upper())
        if len(page_rows) < 200:
            break
    ids = {text(item.get("id")) for item in matches if text(item.get("id"))}
    if len(ids) != 1:
        raise core.AdapterError(f"Bug {serial_number}无法唯一解析。")
    bug = core.unwrap(core.run_devops(executable, ["projex-get-workitem", "--id", next(iter(ids))]))
    if not isinstance(bug, dict) or text(bug.get("serialNumber")).upper() != serial_number.upper():
        raise core.AdapterError("Bug官方回读编号不一致。")
    return bug


def comment_text(comment: dict[str, Any]) -> str:
    return text(comment.get("content") or comment.get("body") or comment.get("comment"))


def parse_requests(comments: list[dict[str, Any]], serial_number: str) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for comment in comments:
        content = comment_text(comment)
        if REQUEST_PREFIX not in content or "<!--" not in content:
            continue
        raw = content.split("<!--", 1)[1].split("-->", 1)[0].strip()
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and value.get("schemaVersion") == REQUEST_SCHEMA \
                and text(value.get("bugSerialNumber")).upper() == serial_number.upper():
            found.append(value)
    return found


def parse_acceptances(comments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for comment in comments:
        content = comment_text(comment)
        if ACCEPT_PREFIX not in content or "<!--" not in content:
            continue
        try:
            value = json.loads(content.split("<!--", 1)[1].split("-->", 1)[0].strip())
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and value.get("schemaVersion") == ACCEPT_SCHEMA:
            found.append(value)
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--bug", required=True)
    parser.add_argument("--request", help="QA请求回执JSON；不传则从Bug官方评论读取最新请求")
    parser.add_argument("--output")
    args = parser.parse_args()
    try:
        executable = core.find_aliyun()
        core.require_auth_env()
        user = current_user(executable)
        bug = resolve_bug(executable, args.project_id, args.bug)
        if person_id(bug, "assignedTo") != text(user.get("id")):
            raise core.AdapterError("当前开发用户不是Bug负责人，特殊修复通道拒绝接收。")
        if status_name(bug) not in {"待确认", "处理中", "再次打开"}:
            raise core.AdapterError(f"Bug当前状态={status_name(bug)}，不能接收新的修复请求。")
        comments = rows(core.run_devops(executable, [
            "projex-list-workitem-comments", "--id", text(bug.get("id")),
        ]))
        if args.request:
            supplied = load(args.request)
            requests = [supplied.get("request")] if isinstance(supplied.get("request"), dict) else [supplied]
        else:
            requests = parse_requests(comments, args.bug)
        if not requests:
            raise core.AdapterError("Bug没有可验证的测试缺陷修复请求评论。")
        request = requests[-1]
        if request.get("schemaVersion") != REQUEST_SCHEMA or request.get("status") != "requested":
            raise core.AdapterError("修复请求状态或schema无效。")
        if text(request.get("bugSerialNumber")).upper() != args.bug.upper() or \
                text(request.get("bugId")) != text(bug.get("id")):
            raise core.AdapterError("修复请求与当前Bug不一致。")
        if not text(request.get("testTaskId")) or not text(request.get("evidenceHash")):
            raise core.AdapterError("修复请求缺测试任务或证据哈希。")
        if not isinstance(request.get("evidence"), dict) or \
                digest(request["evidence"]) != text(request.get("evidenceHash")):
            raise core.AdapterError("修复请求证据哈希不一致，拒绝进入代码修复。")
        if SECRET_RE.search(json.dumps(request, ensure_ascii=False)):
            raise core.AdapterError("修复请求包含敏感凭据，拒绝接收。")
        request_key = text(request.get("idempotencyKey"))
        existing = [item for item in parse_acceptances(comments)
                    if text(item.get("requestIdempotencyKey")) == request_key]
        if existing:
            receipt = {"schema": ACCEPT_SCHEMA, "result": "idempotent", "acceptance": existing[-1],
                       "nextAction": f"修复bug:{args.bug}"}
        else:
            acceptance = {
                "schemaVersion": ACCEPT_SCHEMA,
                "bugSerialNumber": args.bug,
                "bugId": text(bug.get("id")),
                "requestIdempotencyKey": request_key,
                "requestEvidenceHash": text(request.get("evidenceHash")),
                "acceptedBy": user,
                "acceptedAt": core.now_utc(),
                "status": "accepted",
                "nextAction": f"修复bug:{args.bug}",
            }
            body = "\n".join([
                ACCEPT_PREFIX,
                f"已通过测试证据、Bug负责人和当前状态校验，进入开发修复动作：修复bug:{args.bug}",
                f"<!-- {json.dumps(acceptance, ensure_ascii=False, sort_keys=True)} -->",
            ])
            created = core.unwrap(core.run_devops(executable, [
                "projex-create-workitem-comment", "--id", text(bug.get("id")), "--content", body,
            ]))
            after_comments = rows(core.run_devops(executable, [
                "projex-list-workitem-comments", "--id", text(bug.get("id")),
            ]))
            if not any(request_key in json.dumps(item, ensure_ascii=False) for item in after_comments):
                raise core.AdapterError("开发接收评论写入后官方回读失败。")
            receipt = {"schema": ACCEPT_SCHEMA, "result": "accepted", "acceptance": acceptance,
                       "comment": created, "nextAction": f"修复bug:{args.bug}"}
        if args.output:
            Path(args.output).write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(receipt, ensure_ascii=False, indent=2))
        return 0
    except (core.AdapterError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"schema": ACCEPT_SCHEMA, "result": "blocked", "error": core.scrub(str(exc))},
                         ensure_ascii=False, indent=2), file=sys.stderr)
        return 69


if __name__ == "__main__":
    raise SystemExit(main())
