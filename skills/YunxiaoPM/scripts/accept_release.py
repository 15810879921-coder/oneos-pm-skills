#!/usr/bin/env python
"""按发版任务执行生产后产品验收；写操作前必须先 --dry-run。"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import sys
import tempfile
import urllib.parse
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import requests

COOKIE_FILE = Path(tempfile.gettempdir()) / "yunxiao_cookies.json"
ACCEPT_START = "<!-- YUNXIAOPM_ACCEPTANCE_START -->"
ACCEPT_END = "<!-- YUNXIAOPM_ACCEPTANCE_END -->"


def load_session() -> requests.Session:
    jar: dict[str, str] = {}
    if COOKIE_FILE.exists():
        raw = json.loads(COOKIE_FILE.read_text(encoding="utf-8"))
        if isinstance(raw, dict) and "cookies" in raw:
            jar = {
                str(item["name"]): str(item["value"])
                for item in raw["cookies"]
                if isinstance(item, dict) and "name" in item and "value" in item
            }
        elif isinstance(raw, dict):
            jar = {str(key): str(value) for key, value in raw.items()}
    if not jar:
        try:
            import browser_cookie3

            for domain in (".aliyun.com", "devops.aliyun.com", ".devops.aliyun.com"):
                try:
                    for cookie in browser_cookie3.chrome(domain_name=domain):
                        jar[cookie.name] = cookie.value
                except Exception:
                    pass
        except ImportError:
            pass
    token = urllib.parse.unquote(jar.get("XSRF-TOKEN", ""))
    if not token:
        raise RuntimeError("云效会话缺失：请先登录并刷新系统临时目录中的 yunxiao_cookies.json")
    session = requests.Session()
    session.headers.update(
        {
            "Cookie": "; ".join(f"{key}={value}" for key, value in jar.items()),
            "x-xsrf-token": token,
            "X-XSRF-TOKEN": token,
            "Origin": "https://devops.aliyun.com",
            "Referer": "https://devops.aliyun.com/projex",
            "Content-Type": "application/json",
            "accept": "application/json",
        }
    )
    return session


def api(
    session: requests.Session,
    method: str,
    path: str,
    *,
    body: Any = None,
    params: dict[str, str] | None = None,
) -> dict[str, Any]:
    response = session.request(
        method,
        "https://devops.aliyun.com" + path,
        json=body,
        params=params,
        timeout=45,
    )
    try:
        data = response.json()
    except Exception as error:
        response.raise_for_status()
        raise RuntimeError("云效接口响应不是JSON") from error
    if response.status_code in (401, 403):
        raise RuntimeError(f"云效鉴权失败 HTTP {response.status_code}")
    response.raise_for_status()
    if not isinstance(data, dict) or data.get("code") not in (200, None):
        raise RuntimeError(str(data.get("errorMsg") if isinstance(data, dict) else data))
    return data


def get_item(session: requests.Session, workitem_id: str) -> dict[str, Any]:
    result = api(
        session,
        "GET",
        f"/projex/api/workitem/workitem/{workitem_id}?_input_charset=utf-8",
    ).get("result")
    if not isinstance(result, dict):
        raise RuntimeError(f"工作项读取失败：{workitem_id}")
    return result


def document(item: dict[str, Any]) -> str:
    value = item.get("document")
    if isinstance(value, dict):
        return str(value.get("content") or "")
    return str(item.get("description") or "")


def status(item: dict[str, Any]) -> tuple[str, str]:
    value = item.get("status") or item.get("workitemStatus") or {}
    if not isinstance(value, dict):
        raise RuntimeError(f"{item.get('identifier')}状态结构无效")
    name = str(value.get("displayName") or value.get("name") or "")
    identifier = str(value.get("identifier") or "")
    if not name or not identifier:
        raise RuntimeError(f"{item.get('identifier')}状态名称或ID为空")
    return name, identifier


def serial(item: dict[str, Any]) -> str:
    raw = str(item.get("serialNumber") or "").strip()
    if not raw or "-" in raw:
        return raw
    space = item.get("space")
    code = (
        str(space.get("customCode") or "").strip()
        if isinstance(space, dict)
        else ""
    )
    return f"{code}-{raw}" if code and raw.isdigit() else raw


def list_relations(
    session: requests.Session,
    workitem_id: str,
    category: str,
    forward: bool,
) -> list[dict[str, Any]]:
    result = api(
        session,
        "GET",
        f"/projex/api/workitem/v2/workitem/{workitem_id}/relation/workitem/list/by-relation-category",
        params={"category": category, "isForward": str(forward).lower()},
    ).get("result")
    return list(result or []) if isinstance(result, list) else []


def associated_full(
    session: requests.Session, workitem_id: str
) -> list[dict[str, Any]]:
    ids: set[str] = set()
    for forward in (True, False):
        for item in list_relations(session, workitem_id, "ASSOCIATED", forward):
            if item.get("identifier"):
                ids.add(str(item["identifier"]))
    return [get_item(session, identifier) for identifier in sorted(ids)]


def is_requirement(item: dict[str, Any]) -> bool:
    category = str(item.get("category") or item.get("categoryIdentifier") or "").lower()
    type_text = json.dumps(item.get("workitemType") or {}, ensure_ascii=False)
    return category in {"req", "requirement"} or "需求" in type_text


def is_bug(item: dict[str, Any]) -> bool:
    category = str(item.get("category") or item.get("categoryIdentifier") or "").lower()
    type_text = json.dumps(item.get("workitemType") or {}, ensure_ascii=False)
    return category in {"bug", "defect"} or "缺陷" in type_text or "Bug" in type_text


def is_completed_bug(item: dict[str, Any]) -> bool:
    return status(item)[0] in {"已完成", "已关闭"}


def is_delivery(item: dict[str, Any]) -> bool:
    return str(item.get("subject") or "").startswith("【交付】")


def resolve_acceptance_scope(
    session: requests.Session, release_id: str
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """解析验收范围：发版→需求，或发版→【交付】→需求。"""
    release_related = associated_full(session, release_id)
    standalone_bugs = [item for item in release_related if is_bug(item)]
    requirements = [item for item in release_related if is_requirement(item)]
    deliveries: list[dict[str, Any]] = []

    if requirements:
        for requirement in requirements:
            candidates = [
                item
                for item in associated_full(session, str(requirement["identifier"]))
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
        raise RuntimeError("发版任务未正式关联产品需求或【交付】")

    seen_req: set[str] = set()
    for delivery in delivery_candidates:
        reqs = [
            item
            for item in associated_full(session, str(delivery["identifier"]))
            if is_requirement(item)
        ]
        if len(reqs) != 1:
            raise RuntimeError(
                f"交付{serial(delivery)}唯一需求命中数={len(reqs)}"
            )
        req_id = str(reqs[0]["identifier"])
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
    session: requests.Session, workitem_id: str, content: str
) -> None:
    api(
        session,
        "PATCH",
        f"/projex/api/workitem/workitem/{workitem_id}/document?_input_charset=utf-8",
        body={"content": content, "formatType": "RICHTEXT"},
    )


def list_next_statuses(
    session: requests.Session, item: dict[str, Any]
) -> list[tuple[str, str]]:
    _, current_id = status(item)
    result = api(
        session,
        "GET",
        f"/projex/api/workitem/workitem/{item['identifier']}/nextStatus/list",
        params={"currentStatusIdentifier": current_id, "_input_charset": "utf-8"},
    ).get("result") or []
    if isinstance(result, dict):
        result = result.get("statuses") or result.get("list") or []
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
        identifier = value.get("identifier") or value.get("statusIdentifier")
        if name and identifier:
            rows.append((name, str(identifier)))
    return rows


def next_status_id(
    session: requests.Session,
    item: dict[str, Any],
    target_name: str,
) -> str:
    current_name, _ = status(item)
    matches = [identifier for name, identifier in list_next_statuses(session, item) if name == target_name]
    if len(matches) != 1:
        raise RuntimeError(
            f"{serial(item)}无法从{current_name}唯一流转到{target_name}"
        )
    return matches[0]


def transit(
    session: requests.Session, item: dict[str, Any], target_name: str
) -> None:
    _, current_id = status(item)
    target_id = next_status_id(session, item, target_name)
    result = api(
        session,
        "POST",
        f"/projex/api/workitem/workitem/{item['identifier']}/status/transit?_input_charset=utf-8",
        body={"fromStatus": current_id, "toStatus": target_id},
    )
    if result.get("result") is not True:
        raise RuntimeError(f"{serial(item)}状态流转失败")


def is_acceptance_done(item: dict[str, Any]) -> bool:
    name = status(item)[0]
    if is_requirement(item):
        return name in {"已完成", "已关闭"}
    return name == "已完成"


def transit_to_acceptance_done(session: requests.Session, item: dict[str, Any]) -> None:
    """按项目真实下一状态推进到验收终态；需求优先已完成否则已关闭，发版允许经处理中中转。"""
    live = get_item(session, str(item["identifier"]))
    if is_acceptance_done(live):
        return
    preferred = ["已完成", "已关闭"] if is_requirement(live) else ["已完成"]
    next_names = {name for name, _ in list_next_statuses(session, live)}
    for target in preferred:
        if target in next_names:
            transit(session, live, target)
            done = get_item(session, str(live["identifier"]))
            if not is_acceptance_done(done):
                raise RuntimeError(f"{serial(done)}流转后未达验收终态：{status(done)[0]}")
            return
    # 发版常见：发布完成不能直达已完成，需 发布完成→处理中→已完成
    if (not is_requirement(live)) and status(live)[0] == "发布完成" and "处理中" in next_names:
        transit(session, live, "处理中")
        mid = get_item(session, str(live["identifier"]))
        mid_next = {name for name, _ in list_next_statuses(session, mid)}
        if "已完成" not in mid_next:
            raise RuntimeError(f"{serial(mid)}经处理中后无法流转到已完成")
        transit(session, mid, "已完成")
        done = get_item(session, str(live["identifier"]))
        if not is_acceptance_done(done):
            raise RuntimeError(f"{serial(done)}中转后未达已完成：{status(done)[0]}")
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
        "standaloneCompletedBugs": standalone_completed_bugs,
        "recordedAt": when,
        "idempotencyKey": key,
    }
    return (
        f"{ACCEPT_START}<h2>生产后产品验收（YunxiaoPM）</h2><pre>"
        + html.escape(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        + f"</pre>{ACCEPT_END}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="执行生产后产品验收")
    parser.add_argument("action", choices=("pass", "fail"))
    parser.add_argument("--release-id", required=True, help="云效内部identifier")
    parser.add_argument("--release-sn", required=True, help="展示编号")
    parser.add_argument("--acceptor", required=True)
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--reason", default="")
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
        key_source = "|".join(
            [
                args.release_id,
                args.action,
                args.evidence.strip(),
            ]
        )
        key = "accept-" + hashlib.sha256(key_source.encode("utf-8")).hexdigest()[:20]

        requirements, deliveries, standalone_bugs = resolve_acceptance_scope(
            session, args.release_id
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
            bug_relations = associated_full(session, str(bug["identifier"]))
            linked_deliveries = [
                item
                for item in bug_relations
                if str(item.get("subject") or "").startswith("【交付】")
            ]
            if linked_deliveries:
                raise RuntimeError(
                    f"Bug{serial(bug)}已关联交付，不应作为无交付Bug进入发版任务"
                )

        completed_objects = [
            item
            for item in [release, *requirements, *deliveries, *standalone_bugs]
            if is_acceptance_done(item) or is_completed_bug(item)
        ]
        for item in completed_objects:
            if key not in document(item):
                raise RuntimeError(
                    f"{serial(item)}已完成但缺少本次验收幂等证据，拒绝接续"
                )

        if is_acceptance_done(release) and all(
            is_acceptance_done(item) for item in [*requirements, *deliveries]
        ):
            print(
                json.dumps(
                    {
                        "ok": True,
                        "alreadyDone": True,
                        "releaseTask": args.release_sn,
                        "requirements": actual_scope,
                        "deliveries": [serial(item) for item in deliveries],
                        "standaloneCompletedBugs": [
                            serial(item) for item in standalone_bugs
                        ],
                        "idempotencyKey": key,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return

        block = acceptance_block(
            args,
            key,
            actual_scope,
            "n/a",
            [serial(item) for item in standalone_bugs],
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
        if args.dry_run:
            print(json.dumps(plan, ensure_ascii=False, indent=2))
            return

        targets_by_id = {
            str(item["identifier"]): item
            for item in [release, *requirements, *deliveries, *standalone_bugs]
        }
        targets = list(targets_by_id.values())
        for item in targets:
            set_document(
                session,
                str(item["identifier"]),
                replace_block(document(item), block),
            )
            reread = document(get_item(session, str(item["identifier"])))
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
                get_item(session, str(item["identifier"]))
                for item in [*requirements, *deliveries, *standalone_bugs, release]
            ]
            wrong = [
                {"serialNumber": serial(item), "status": status(item)[0]}
                for item in readback
                if not is_acceptance_done(item) and not is_completed_bug(item)
            ]
            if wrong:
                raise RuntimeError(f"状态回读失败：{wrong}")
        else:
            current_release = get_item(session, str(release["identifier"]))
            state_result: dict[str, Any] = {
                "before": status(current_release)[0],
                "after": status(current_release)[0],
            }
            if status(current_release)[0] == "发布完成":
                try:
                    transit(session, current_release, "发布失败")
                    state_result["after"] = status(
                        get_item(session, str(release["identifier"]))
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
    except (RuntimeError, OSError, ValueError, json.JSONDecodeError) as error:
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
