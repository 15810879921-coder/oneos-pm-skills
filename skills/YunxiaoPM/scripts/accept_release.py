#!/usr/bin/env python
"""按发版任务执行生产后产品验收；写操作前必须先 --dry-run。"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
import tempfile
import urllib.parse
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import requests

COOKIE_FILE = Path(tempfile.gettempdir()) / "yunxiao_cookies.json"
PROD_START = "<!-- YUNXIAO_RELEASE_PRODUCTION_EVIDENCE_START -->"
PROD_END = "<!-- YUNXIAO_RELEASE_PRODUCTION_EVIDENCE_END -->"
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


def production_evidence(item: dict[str, Any]) -> dict[str, Any]:
    content = document(item)
    start = content.find(PROD_START)
    end = content.find(PROD_END)
    if start < 0 or end <= start:
        raise RuntimeError("发版任务缺受管生产证据区块")
    block = html.unescape(content[start + len(PROD_START) : end])
    match = re.search(r"\{.*\}", block, re.DOTALL)
    if not match:
        raise RuntimeError("生产证据区块缺JSON对象")
    data = json.loads(match.group(0))
    required = {
        "schemaVersion",
        "releaseTaskId",
        "executionId",
        "environment",
        "pipelineStatus",
        "scope",
        "immutableAnchor",
        "callbackVerified",
        "verificationPlanId",
        "verificationStatus",
        "verificationEvidence",
        "observationCompletedAt",
        "idempotencyKey",
    }
    missing = sorted(required - set(data))
    if missing:
        raise RuntimeError(f"生产证据缺字段：{missing}")
    return data


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


def next_status_id(
    session: requests.Session,
    item: dict[str, Any],
    target_name: str,
) -> str:
    current_name, current_id = status(item)
    result = api(
        session,
        "GET",
        f"/projex/api/workitem/workitem/{item['identifier']}/nextStatus/list",
        params={"currentStatusIdentifier": current_id, "_input_charset": "utf-8"},
    ).get("result") or []
    if isinstance(result, dict):
        result = result.get("statuses") or result.get("list") or []
    matches: list[str] = []
    for choice in result if isinstance(result, list) else []:
        if not isinstance(choice, dict):
            continue
        value = choice.get("status") if isinstance(choice.get("status"), dict) else choice
        name = value.get("displayName") or value.get("name") or value.get("statusName")
        identifier = value.get("identifier") or value.get("statusIdentifier")
        if name == target_name and identifier:
            matches.append(str(identifier))
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


def is_delivery(item: dict[str, Any]) -> bool:
    return str(item.get("subject") or "").startswith("【交付】")


def delivery_end_label(item: dict[str, Any]) -> str:
    subject = str(item.get("subject") or "")
    if "【小程序】" in subject or subject.startswith("【交付】【小程序】"):
        return "小程序"
    if "【Web】" in subject or "【PC】" in subject or subject.startswith("【交付】【Web】"):
        return "Web"
    tags = item.get("labels") or item.get("tag") or item.get("tags") or []
    names: list[str] = []
    if isinstance(tags, list):
        for tag in tags:
            if isinstance(tag, dict):
                names.append(str(tag.get("name") or tag.get("displayName") or ""))
            else:
                names.append(str(tag))
    elif isinstance(tags, str):
        names.append(tags)
    joined = " ".join(names)
    if "小程序" in joined:
        return "小程序"
    if "Web" in joined or "PC" in joined:
        return "Web"
    return "未知"


def requirement_deliveries(
    session: requests.Session, requirement: dict[str, Any]
) -> list[dict[str, Any]]:
    return [
        item
        for item in associated_full(session, str(requirement["identifier"]))
        if is_delivery(item)
    ]


def acceptance_block(
    args,
    key: str,
    scope: list[str],
    production_execution_id: str,
    standalone_completed_bugs: list[str],
    *,
    accepted_deliveries: list[str],
    deferred_requirements: list[str],
    pending_deliveries: list[dict[str, str]],
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
        "acceptedDeliveries": accepted_deliveries,
        "deferredRequirements": deferred_requirements,
        "pendingDeliveries": pending_deliveries,
        "partialAcceptance": bool(deferred_requirements or pending_deliveries),
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
        prod = production_evidence(release)
        if (
            prod["schemaVersion"] != "oneos.release-production/v1"
            or prod["releaseTaskId"] != args.release_sn
            or prod["environment"] != "prod"
            or prod["pipelineStatus"] not in {"成功", "success", "SUCCESS"}
            or prod["callbackVerified"] is not True
            or prod["verificationStatus"] not in {"通过", "passed", "PASSED"}
            or not str(prod["executionId"]).strip()
            or not str(prod["immutableAnchor"]).strip()
            or not str(prod["verificationPlanId"]).strip()
            or not list(prod["verificationEvidence"] or [])
            or not str(prod["observationCompletedAt"]).strip()
            or not str(prod["idempotencyKey"]).strip()
        ):
            raise RuntimeError("生产证据环境、状态、验签或锚点门禁失败")
        key_source = "|".join(
            [
                args.release_id,
                str(prod["executionId"]),
                args.action,
                args.evidence.strip(),
            ]
        )
        key = "accept-" + hashlib.sha256(key_source.encode("utf-8")).hexdigest()[:20]

        release_related = associated_full(session, args.release_id)
        requirements = [item for item in release_related if is_requirement(item)]
        release_deliveries = [item for item in release_related if is_delivery(item)]
        standalone_bugs = [item for item in release_related if is_bug(item)]
        if not requirements:
            raise RuntimeError("发版任务未正式关联产品需求")
        if not release_deliveries:
            raise RuntimeError("发版任务未正式关联源【交付】")
        actual_scope = sorted(serial(item) for item in requirements)
        expected_scope = sorted(str(value) for value in prod["scope"])
        if actual_scope != expected_scope:
            raise RuntimeError(
                f"生产scope与正式需求关系不一致：{expected_scope} != {actual_scope}"
            )
        allowed_requirement_states = (
            {"发布完成", "已完成"} if args.action == "pass" else {"发布完成"}
        )
        for item in requirements:
            if status(item)[0] not in allowed_requirement_states:
                raise RuntimeError(
                    f"需求{serial(item)}状态={status(item)[0]}，"
                    f"期望{sorted(allowed_requirement_states)}"
                )

        # 本批交付：发版任务正式关联的端侧【交付】；每条需求在本批恰好对应一条
        deliveries: list[dict[str, Any]] = []
        req_by_id = {str(item["identifier"]): item for item in requirements}
        delivery_to_req: dict[str, dict[str, Any]] = {}
        for delivery in release_deliveries:
            linked_reqs = [
                item
                for item in associated_full(session, str(delivery["identifier"]))
                if is_requirement(item)
                and str(item["identifier"]) in req_by_id
            ]
            if len(linked_reqs) != 1:
                raise RuntimeError(
                    f"交付{serial(delivery)}与本批需求正式关联数={len(linked_reqs)}，期望恰好1"
                )
            delivery_to_req[str(delivery["identifier"])] = linked_reqs[0]
            allowed_delivery_states = (
                {"处理中", "已完成"} if args.action == "pass" else {"处理中"}
            )
            if status(delivery)[0] not in allowed_delivery_states:
                raise RuntimeError(
                    f"交付{serial(delivery)}状态={status(delivery)[0]}，"
                    f"期望{sorted(allowed_delivery_states)}"
                )
            deliveries.append(delivery)

        covered_req_ids = {str(req["identifier"]) for req in delivery_to_req.values()}
        missing_req = [
            serial(item)
            for item in requirements
            if str(item["identifier"]) not in covered_req_ids
        ]
        if missing_req:
            raise RuntimeError(f"本批发版未覆盖源交付的需求：{missing_req}")
        if len(deliveries) != len(requirements):
            raise RuntimeError(
                f"本批需求数={len(requirements)}与源交付数={len(deliveries)}不一致"
            )

        # 双端：查出每条需求的全部端侧交付，判断本批验收后是否仍有未完成端
        pending_by_req: dict[str, list[dict[str, str]]] = {}
        for requirement in requirements:
            all_ends = requirement_deliveries(session, requirement)
            if not all_ends:
                raise RuntimeError(f"需求{serial(requirement)}缺少【交付】关联")
            batch_delivery_ids = {
                str(delivery["identifier"])
                for delivery in deliveries
                if str(delivery_to_req[str(delivery["identifier"])]["identifier"])
                == str(requirement["identifier"])
            }
            pending: list[dict[str, str]] = []
            for end_delivery in all_ends:
                end_id = str(end_delivery["identifier"])
                end_status = status(end_delivery)[0]
                # 本批将关闭的交付视为即将完成；其余端仍非已完成则挂起需求整单关闭
                will_complete = end_id in batch_delivery_ids or end_status == "已完成"
                if not will_complete:
                    pending.append(
                        {
                            "requirement": serial(requirement),
                            "delivery": serial(end_delivery),
                            "end": delivery_end_label(end_delivery),
                            "status": end_status,
                        }
                    )
            if pending:
                pending_by_req[str(requirement["identifier"])] = pending

        deferred_requirements = [
            serial(item)
            for item in requirements
            if str(item["identifier"]) in pending_by_req
        ]
        pending_deliveries = [
            row for rows in pending_by_req.values() for row in rows
        ]
        closeable_requirements = [
            item
            for item in requirements
            if str(item["identifier"]) not in pending_by_req
        ]

        for bug in standalone_bugs:
            if not is_completed_bug(bug):
                raise RuntimeError(f"无交付Bug{serial(bug)}未处于已完成/已关闭状态")
            if "oneos.bug-retest/v1" not in document(bug):
                raise RuntimeError(f"无交付Bug{serial(bug)}缺少独立复测证据")
            bug_relations = associated_full(session, str(bug["identifier"]))
            linked_deliveries = [
                item for item in bug_relations if is_delivery(item)
            ]
            if linked_deliveries:
                raise RuntimeError(
                    f"Bug{serial(bug)}已关联交付，不应作为无交付Bug进入发版任务"
                )

        completed_objects = [
            item
            for item in [release, *requirements, *deliveries, *standalone_bugs]
            if status(item)[0] == "已完成" or is_completed_bug(item)
        ]
        for item in completed_objects:
            if key not in document(item):
                raise RuntimeError(
                    f"{serial(item)}已完成但缺少本次验收幂等证据，拒绝接续"
                )

        # 整批发版已完成且本批交付已完成；需求允许因双端部分验收仍为发布完成
        if release_status == "已完成" and all(
            status(item)[0] == "已完成" for item in deliveries
        ) and all(
            status(item)[0] in {"已完成", "发布完成"} for item in requirements
        ) and all(
            (
                status(item)[0] == "已完成"
                if str(item["identifier"]) not in pending_by_req
                else status(item)[0] == "发布完成"
            )
            for item in requirements
        ):
            print(
                json.dumps(
                    {
                        "ok": True,
                        "alreadyDone": True,
                        "releaseTask": args.release_sn,
                        "requirements": actual_scope,
                        "deliveries": [serial(item) for item in deliveries],
                        "closedRequirements": [
                            serial(item) for item in closeable_requirements
                            if status(item)[0] == "已完成"
                        ],
                        "deferredRequirements": deferred_requirements,
                        "pendingDeliveries": pending_deliveries,
                        "partialAcceptance": bool(deferred_requirements),
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
            str(prod["executionId"]),
            [serial(item) for item in standalone_bugs],
            accepted_deliveries=[serial(item) for item in deliveries],
            deferred_requirements=deferred_requirements,
            pending_deliveries=pending_deliveries,
        )
        requirement_transitions = [
            serial(item)
            for item in closeable_requirements
            if status(item)[0] != "已完成"
        ]
        delivery_transitions = [
            serial(item) for item in deliveries if status(item)[0] != "已完成"
        ]
        plan = {
            "ok": True,
            "dryRun": args.dry_run,
            "releaseTask": args.release_sn,
            "requirements": actual_scope,
            "deliveries": [serial(item) for item in deliveries],
            "closedRequirements": [serial(item) for item in closeable_requirements],
            "deferredRequirements": deferred_requirements,
            "pendingDeliveries": pending_deliveries,
            "partialAcceptance": bool(deferred_requirements),
            "standaloneCompletedBugs": [serial(item) for item in standalone_bugs],
            "conclusion": "通过" if args.action == "pass" else "不通过",
            "idempotencyKey": key,
            "wouldTransit": (
                {
                    "requirements": requirement_transitions,
                    "deliveries": delivery_transitions,
                    "releaseTask": (
                        args.release_sn if release_status != "已完成" else None
                    ),
                    "note": (
                        "双端需求一端先验收：仅关闭本批源交付与发版任务；"
                        "另一端交付未完成前需求保持发布完成"
                        if deferred_requirements
                        else "本批需求全部端侧交付已齐，需求可关闭为已完成"
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
            for item in deliveries:
                if status(get_item(session, str(item["identifier"])))[0] != "已完成":
                    transit(session, get_item(session, str(item["identifier"])), "已完成")
            for item in closeable_requirements:
                if status(get_item(session, str(item["identifier"])))[0] != "已完成":
                    transit(session, get_item(session, str(item["identifier"])), "已完成")
            current_release = get_item(session, str(release["identifier"]))
            if status(current_release)[0] != "已完成":
                transit(session, current_release, "已完成")
            must_done = [*deliveries, *closeable_requirements, release]
            readback = [
                get_item(session, str(item["identifier"])) for item in must_done
            ]
            wrong = [
                {"serialNumber": serial(item), "status": status(item)[0]}
                for item in readback
                if status(item)[0] != "已完成"
            ]
            if wrong:
                raise RuntimeError(f"状态回读失败：{wrong}")
            # 部分验收：延期需求必须仍为发布完成，不得被误关
            for item in requirements:
                if str(item["identifier"]) in pending_by_req:
                    live = get_item(session, str(item["identifier"]))
                    if status(live)[0] == "已完成":
                        raise RuntimeError(
                            f"双端部分验收误关闭需求{serial(live)}；另一端交付尚未完成"
                        )
                    if status(live)[0] != "发布完成":
                        raise RuntimeError(
                            f"部分验收后需求{serial(live)}状态={status(live)[0]}，期望发布完成"
                        )
            plan["dryRun"] = False
            plan["partialAcceptance"] = bool(deferred_requirements)
            print(json.dumps(plan, ensure_ascii=False, indent=2))
            return
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
