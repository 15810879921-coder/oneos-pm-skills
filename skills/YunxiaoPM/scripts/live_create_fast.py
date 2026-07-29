#!/usr/bin/env python3
"""YunxiaoPM 极速真实建单 v5：快轨描述/计划/标签/工时 2+2/设计 ASSOCIATED 补挂。"""
from __future__ import annotations

import json
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

try:
    import browser_cookie3
except ImportError:  # pragma: no cover
    browser_cookie3 = None

import requests

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = json.loads((ROOT / "assets" / "runtime-ids.json").read_text())
STATUS = RUNTIME["status"]["req"]
TASK_STATUS = RUNTIME["status"]["task"]
FAST = RUNTIME.get("fields", {}).get("fast_track") or {}

SPACE = (
    RUNTIME.get("project", {}).get("spaceIdentifier")
    or (RUNTIME.get("project", {}).get("last_selected") or {}).get("spaceIdentifier")
)
if not SPACE:
    raise RuntimeError(
        "未选定项目 spaceIdentifier：须先走门禁 PJ 点选，或设置 runtime project.last_selected"
    )
REQ_TYPE = RUNTIME["workitem_types"]["product_req"]["identifier"]
TASK_TYPE = RUNTIME["workitem_types"]["task"]["identifier"]
HEFEI = RUNTIME["people"]["hefei"]["identifier"]
WANG = RUNTIME["people"].get("wangmian", {}).get("identifier", "6811df000601d2fea60144a9")
PRI = RUNTIME["priority"]["中"]
TAG_FAULT = RUNTIME.get("tags", {}).get("故障管理", "ceb526a7343995577645317e9a")
PLACEHOLDER = RUNTIME["delivery_placeholder"]
PROTO = "https://prototype.lnoneos.com/vehicle-fault-handling/index.html"
TZ = timezone(timedelta(hours=8))
TODAY = datetime.now(TZ).strftime("%Y-%m-%d")
NOON = f"{TODAY} 12:00:00"
EOD = f"{TODAY} 23:59:59"
NOON_MS = str(
    int(datetime.now(TZ).replace(hour=12, minute=0, second=0, microsecond=0).timestamp() * 1000)
)
START_MS = str(
    int(datetime.now(TZ).replace(hour=9, minute=0, second=0, microsecond=0).timestamp() * 1000)
)
END_MS = str(
    int(datetime.now(TZ).replace(hour=11, minute=0, second=0, microsecond=0).timestamp() * 1000)
)
FAST_EST = int(FAST.get("req_estimated_hours", 2))
FAST_ACT = int(FAST.get("req_actual_hours", 2))

PENDING = STATUS["待处理"]
DESIGN_DONE = STATUS["设计完成"]
PENDING_DEV = STATUS["待开发"]
TASK_DONE = TASK_STATUS["已完成"]

_COOKIE = ""
_XSRF = ""


def load_auth() -> None:
    global _COOKIE, _XSRF
    jar: dict[str, str] = {}
    if browser_cookie3:
        for domain in (".aliyun.com", "devops.aliyun.com", ".devops.aliyun.com"):
            try:
                for c in browser_cookie3.chrome(domain_name=domain):
                    jar[c.name] = c.value
            except Exception:
                pass
    if not jar:
        p = Path("/tmp/yunxiao_cookies.json")
        if p.exists():
            raw = json.loads(p.read_text())
            jar = (
                raw
                if isinstance(raw, dict) and "XSRF-TOKEN" in raw
                else {c["name"]: c["value"] for c in raw.get("cookies", [])}
            )
    _COOKIE = "; ".join(f"{k}={v}" for k, v in jar.items())
    x = jar.get("XSRF-TOKEN", "")
    _XSRF = urllib.parse.unquote(x) if "%" in x else x
    if not _XSRF:
        raise RuntimeError("缺少 XSRF-TOKEN：请先在 Chrome 登录 devops.aliyun.com")


def session() -> requests.Session:
    s = requests.Session()
    s.headers.update(
        {
            "Content-Type": "application/json",
            "Cookie": _COOKIE,
            "x-xsrf-token": _XSRF,
            "X-XSRF-TOKEN": _XSRF,
            "Origin": "https://devops.aliyun.com",
            "Referer": f"https://devops.aliyun.com/projex/project/{SPACE}/req",
            "accept": "application/json",
            "User-Agent": "YunxiaoPM-live_create_fast/5.0",
            "Connection": "keep-alive",
        }
    )
    return s


def api(s: requests.Session, method: str, url: str, body: Any = None) -> dict:
    r = s.request(method, url, json=body, timeout=60)
    try:
        return r.json()
    except Exception:
        r.raise_for_status()
        raise


def create(s: requests.Session, payload: dict) -> dict:
    url = "https://devops.aliyun.com/projex/api/workitem/workitem?_input_charset=utf-8"
    j = api(s, "POST", url, payload)
    r = j.get("result") or {}
    if j.get("code") == 200 and isinstance(r, dict) and r.get("identifier"):
        return r
    j = api(s, "PUT", url, payload)
    r = j.get("result") or {}
    if j.get("code") == 200 and isinstance(r, dict) and r.get("identifier"):
        return r
    raise RuntimeError(f"create failed: {j}")


def get(s: requests.Session, wid: str) -> dict:
    return api(
        s,
        "GET",
        f"https://devops.aliyun.com/projex/api/workitem/workitem/{wid}?_input_charset=utf-8",
    )["result"]


def apply_tag(s: requests.Session, wid: str, tag_id: str = TAG_FAULT) -> None:
    j = api(
        s,
        "PATCH",
        f"https://devops.aliyun.com/projex/api/workitem/workitem/{wid}?_input_charset=utf-8",
        {
            "workitemIdentifier": wid,
            "propertyKey": "tag",
            "propertyValue": tag_id,
            "operateType": "COVER",
        },
    )
    if j.get("code") != 200:
        raise RuntimeError(f"tag failed {wid}: {j}")


def set_document(s: requests.Session, wid: str, html: str) -> None:
    j = api(
        s,
        "PATCH",
        f"https://devops.aliyun.com/projex/api/workitem/workitem/{wid}/document?_input_charset=utf-8",
        {"content": html, "formatType": "RICHTEXT"},
    )
    if j.get("code") != 200 or j.get("errorMsg"):
        raise RuntimeError(f"document failed {wid}: {j}")


def set_fields(s: requests.Session, wid: str, pairs: list[tuple[str, str]]) -> None:
    data = urllib.parse.urlencode(
        {
            "fieldValueList": json.dumps(
                [{"fieldIdentifier": k, "value": v} for k, v in pairs], ensure_ascii=False
            )
        }
    )
    r = s.post(
        f"https://devops.aliyun.com/projex/api/workitem/workitem/field/value/{wid}?_input_charset=utf-8",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=60,
    )
    j = r.json()
    if j.get("code") != 200:
        raise RuntimeError(f"field/value failed {wid}: {j}")


def set_estimate_hours(s: requests.Session, wid: str, hours: int, user: str = WANG) -> None:
    est = api(
        s,
        "GET",
        f"https://devops.aliyun.com/projex/api/workitem/workitem/time/estimate/list?workitemIdentifier={wid}",
    ).get("result") or []
    for row in est:
        eid = row.get("identifier")
        if eid:
            api(
                s,
                "DELETE",
                f"https://devops.aliyun.com/projex/api/workitem/workitem/time/estimate/{wid}/{eid}",
            )
    j = api(
        s,
        "POST",
        "https://devops.aliyun.com/projex/api/workitem/workitem/time/estimate?_input_charset=utf-8",
        {
            "workitemIdentifier": wid,
            "spentTime": hours,
            "type": "develop",
            "description": "快轨默认预计工时",
            "recordUserIdentifier": user,
            "forCreate": False,
            "containsRestDay": False,
        },
    )
    if j.get("code") != 200:
        raise RuntimeError(f"estimate failed {wid}: {j}")


def set_actual_hours(s: requests.Session, wid: str, hours: int, user: str = WANG) -> None:
    j = api(
        s,
        "POST",
        "https://devops.aliyun.com/projex/api/workitem/workitem/time?_input_charset=utf-8",
        {
            "workitemIdentifier": wid,
            "actualTime": hours,
            "type": "develop",
            "description": "快轨默认实际工时",
            "recordUserIdentifier": user,
            "gmtStart": START_MS,
            "gmtEnd": END_MS,
        },
    )
    if j.get("code") != 200 or not j.get("result"):
        raise RuntimeError(f"actual time failed {wid}: {j}")


def try_associate_to_req(s: requests.Session, stage_id: str, req_id: str) -> bool:
    """建后补 ASSOCIATED→需求。Cookie 下常失败，成功返回 True。"""
    bodies = [
        {"relationIdentifier": "ASSOCIATED", "toWorkitemIdentifier": req_id},
        {
            "relationIdentifier": "ASSOCIATED",
            "fromWorkitemIdentifier": stage_id,
            "toWorkitemIdentifier": req_id,
        },
    ]
    for body in bodies:
        for url in (
            f"https://devops.aliyun.com/projex/api/workitem/workitem/{stage_id}/relation/record?_input_charset=utf-8",
            f"https://devops.aliyun.com/projex/api/workitem/v2/workitem/{stage_id}/relation/record?_input_charset=utf-8",
        ):
            j = api(s, "POST", url, body)
            if j.get("code") == 200 and j.get("result") not in (None, False):
                if not (isinstance(j.get("result"), dict) and j["result"].get("status") in (404, 405)):
                    rows = list_associated(s, stage_id)
                    if req_id in {r.get("identifier") for r in rows}:
                        return True
    return False


def transit(s: requests.Session, wid: str, from_status: str, to_status: str) -> None:
    if from_status == to_status:
        return
    j = api(
        s,
        "POST",
        f"https://devops.aliyun.com/projex/api/workitem/workitem/{wid}/status/transit?_input_charset=utf-8",
        {"fromStatus": from_status, "toStatus": to_status},
    )
    if not (j.get("code") == 200 and j.get("result") is True):
        raise RuntimeError(f"transit {wid} {from_status}->{to_status}: {j}")


def md_to_html(md: str) -> str:
    parts = []
    for line in md.splitlines():
        if line.startswith("## "):
            parts.append(f"<h2>{line[3:]}</h2>")
        elif line.startswith("### "):
            parts.append(f"<h3>{line[4:]}</h3>")
        elif line.startswith("- "):
            parts.append(f"<p>• {line[2:]}</p>")
        elif line.strip():
            parts.append(f"<p>{line}</p>")
    return "".join(parts)


def req_document_html(s: requests.Session, rid: str) -> str:
    w = get(s, rid)
    return ((w.get("document") or {}).get("content") or w.get("description") or "").strip()


def req_payload(subject: str, html: str) -> dict:
    return {
        "subject": subject,
        "description": html,
        "formatType": "RICHTEXT",
        "document": {"content": html, "formatType": "RICHTEXT"},
        "spaceIdentifier": SPACE,
        "space": SPACE,
        "spaceType": "Project",
        "workitemTypeIdentifier": REQ_TYPE,
        "workitemType": REQ_TYPE,
        "categoryIdentifier": "Req",
        "category": "Req",
        "assignedTo": WANG,
        "fieldValueList": [
            {"fieldIdentifier": "priority", "value": PRI},
            {"fieldIdentifier": "assignedTo", "value": WANG},
        ],
        "attachmentIdList": [],
        "cloneFrom": None,
        "createWorkitemRelationList": [],
    }


def task_payload(
    subject: str,
    html: str,
    assignee: str,
    *,
    plan_start: bool = True,
    associated_req: str | None = None,
    parent_delivery: str | None = None,
) -> dict:
    fvl = [
        {"fieldIdentifier": "priority", "value": PRI},
        {"fieldIdentifier": "assignedTo", "value": assignee},
    ]
    if plan_start:
        fvl.append({"fieldIdentifier": "79", "value": NOON_MS})
    payload: dict[str, Any] = {
        "subject": subject,
        "description": html,
        "formatType": "RICHTEXT",
        "spaceIdentifier": SPACE,
        "space": SPACE,
        "spaceType": "Project",
        "workitemTypeIdentifier": TASK_TYPE,
        "workitemType": TASK_TYPE,
        "categoryIdentifier": "Task",
        "category": "Task",
        "assignedTo": assignee,
        "fieldValueList": fvl,
        "attachmentIdList": [],
        "cloneFrom": None,
    }
    if parent_delivery:
        payload["parent"] = parent_delivery
        payload["parentIdentifier"] = parent_delivery
        payload["createWorkitemRelationInfo"] = {
            "relatedWorkitemIdentifier": parent_delivery,
            "relatedToRelationIdentifier": "TASK_SUB",
        }
    else:
        if not associated_req:
            raise ValueError("associated_req required for delivery: ASSOCIATED→需求")
        payload["createWorkitemRelationInfo"] = {
            "relatedWorkitemIdentifier": associated_req,
            "relatedToRelationIdentifier": "ASSOCIATED",
        }
    return payload


def list_associated(s: requests.Session, wid: str) -> list[dict]:
    j = api(
        s,
        "GET",
        f"https://devops.aliyun.com/projex/api/workitem/v2/workitem/{wid}/relation/workitem/list/by-relation-category?category=ASSOCIATED&isForward=true",
    )
    return j.get("result") or []


def assert_associated_to_req(s: requests.Session, wid: str, req_id: str, label: str) -> None:
    rows = list_associated(s, wid)
    ids = {r.get("identifier") for r in rows}
    if req_id not in ids:
        raise RuntimeError(
            f"{label} 关联项未挂需求：期望 {req_id}，实际 {[r.get('serialNumber') for r in rows]}"
        )


AUTO_RDO = """## 原始诉求（AutoRDO）

运维需在故障处置页承接机器人上报的故障，完成处置、挂起与归档，并保留证据链；工作台相关统计口径需与处置页一致

待确认：
- 本期是否含真实短信/邮件通道（现口径一般为演示模板）

## 工作项编号（系统）
- 交付：待建
- 分析：待建
- 设计：待建
"""


def summarize_from_create(w: dict, *, status: str, assignee_name: str) -> dict:
    return {
        "serial": w.get("serialNumber"),
        "id": w.get("identifier"),
        "subject": w.get("subject"),
        "status": status,
        "assignee": assignee_name,
        "parent": w.get("parentIdentifier"),
    }


def build_normal() -> dict:
    t0 = time.perf_counter()
    s = session()
    title = "【新增】故障处置（YunxiaoPMapp标准·极速v2）"
    req = create(s, req_payload(title, md_to_html(AUTO_RDO + f"\n原型：{PROTO}\n")))
    rid = req["identifier"]

    with ThreadPoolExecutor(max_workers=2) as pool:
        f_tag_r = pool.submit(apply_tag, session(), rid)
        f_deliv = pool.submit(
            create,
            session(),
            task_payload(
                f"【交付】{title}",
                f"<p>{PLACEHOLDER}</p>",
                HEFEI,
                associated_req=rid,
            ),
        )
        deliv = f_deliv.result()
        f_tag_r.result()
    did = deliv["identifier"]

    with ThreadPoolExecutor(max_workers=3) as pool:
        f_tag_d = pool.submit(apply_tag, session(), did)
        f_ana = pool.submit(
            create,
            session(),
            task_payload(
                f"【分析】{title}",
                "<p>分析阶段：故障处置台账、挂起归档与证据链。</p>",
                WANG,
                associated_req=rid,
                parent_delivery=did,
            ),
        )
        f_des = pool.submit(
            create,
            session(),
            task_payload(
                f"【设计】{title}",
                f"<p>设计阶段：对齐原型 {PROTO}</p>",
                WANG,
                associated_req=rid,
                parent_delivery=did,
            ),
        )
        ana = f_ana.result()
        des = f_des.result()
        f_tag_d.result()

    with ThreadPoolExecutor(max_workers=3) as pool:
        list(
            as_completed(
                [
                    pool.submit(transit, session(), rid, PENDING, DESIGN_DONE),
                    pool.submit(transit, session(), ana["identifier"], PENDING, TASK_DONE),
                    pool.submit(transit, session(), des["identifier"], PENDING, TASK_DONE),
                ]
            )
        )
    transit(s, rid, DESIGN_DONE, PENDING_DEV)

    return {
        "path": "normal",
        "elapsed_s": round(time.perf_counter() - t0, 3),
        "req": summarize_from_create(req, status="待开发", assignee_name="王冕"),
        "delivery": summarize_from_create(deliv, status="待处理", assignee_name="何斐"),
        "analysis": summarize_from_create(ana, status="已完成", assignee_name="王冕"),
        "design": summarize_from_create(des, status="已完成", assignee_name="王冕"),
    }


def build_fast(
    *,
    tag_id: str = TAG_FAULT,
    has_prototype: bool = True,
    delivery_html: str | None = None,
) -> dict:
    """无单快轨。

    - 【交付】描述：须由调用方先跑 AutoRDO 产出「规则对照」章（修改前+修改后），
      经 delivery_html 传入；禁止无故占位；禁止只整文同步需求当作交付描述
    - 设计描述 = 需求 document
    - 设计 79/80=当日；交付 79=当日
    - 需求/交付/设计同标签
    - 需求预计/实际工时各 2
    - 设计 TASK_SUB→交付后尝试 ASSOCIATED→需求
    """
    t0 = time.perf_counter()
    s = session()
    title = "【新增】故障处置（YunxiaoPM快轨·极速v5）"
    req_html = md_to_html(AUTO_RDO + (f"\n原型：{PROTO}\n" if has_prototype else "\n"))
    req = create(s, req_payload(title, req_html))
    rid = req["identifier"]
    # 以落库 document 为准（与手动建需后读需求一致）
    req_html = req_document_html(s, rid) or req_html

    if delivery_html:
        deliv_html = delivery_html
        desc_source = "autoprd"
    elif req_html.strip():
        deliv_html = req_html
        desc_source = "manual_sync"
    else:
        deliv_html = f"<p>{PLACEHOLDER}</p>"
        desc_source = "placeholder"

    with ThreadPoolExecutor(max_workers=2) as pool:
        f_tag_r = pool.submit(apply_tag, session(), rid, tag_id)
        f_deliv = pool.submit(
            create,
            session(),
            task_payload(
                f"【交付】{title}",
                deliv_html,
                HEFEI,
                associated_req=rid,
            ),
        )
        deliv = f_deliv.result()
        f_tag_r.result()
    did = deliv["identifier"]

    with ThreadPoolExecutor(max_workers=2) as pool:
        f_tag_d = pool.submit(apply_tag, session(), did, tag_id)
        f_des = pool.submit(
            create,
            session(),
            task_payload(
                f"【设计】{title}",
                req_html,
                WANG,
                parent_delivery=did,
            ),
        )
        des = f_des.result()
        f_tag_d.result()
    des_id = des["identifier"]
    apply_tag(s, des_id, tag_id)

    # 计划时间：设计起止当日；交付开始当日（create 已带 79，再 field/value 加固）
    set_fields(s, des_id, [("79", NOON), ("80", EOD)])
    set_fields(s, did, [("79", NOON)])

    # 设计关联项补挂需求（可能失败，回报 risk）
    design_assoc_ok = try_associate_to_req(s, des_id, rid)

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(
            as_completed(
                [
                    pool.submit(transit, session(), rid, PENDING, DESIGN_DONE),
                    pool.submit(transit, session(), des_id, PENDING, TASK_DONE),
                ]
            )
        )
    transit(s, rid, DESIGN_DONE, PENDING_DEV)

    set_estimate_hours(s, rid, FAST_EST)
    set_actual_hours(s, rid, FAST_ACT)

    risk = None
    if desc_source == "placeholder":
        risk = "交付描述仍为占位"
    if not design_assoc_ok:
        risk = (risk + "；" if risk else "") + "设计 ASSOCIATED→需求补挂失败（Cookie），须 UI/OpenAPI 兜底"

    return {
        "path": "fast",
        "elapsed_s": round(time.perf_counter() - t0, 3),
        "req": summarize_from_create(req, status="待开发", assignee_name="王冕"),
        "delivery": summarize_from_create(deliv, status="待处理", assignee_name="何斐"),
        "design": summarize_from_create(des, status="已完成", assignee_name="王冕"),
        "analysis": None,
        "delivery_desc_source": desc_source,
        "design_associated_ok": design_assoc_ok,
        "risk": risk,
    }


def main() -> None:
    auth0 = time.perf_counter()
    load_auth()
    auth_s = round(time.perf_counter() - auth0, 3)

    wall0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=2) as pool:
        f_fast = pool.submit(build_fast)
        f_normal = pool.submit(build_normal)
        fast = f_fast.result()
        normal = f_normal.result()
    build_s = round(time.perf_counter() - wall0, 3)

    s = session()
    assert_associated_to_req(s, normal["delivery"]["id"], normal["req"]["id"], "normal.delivery")
    assert_associated_to_req(s, fast["delivery"]["id"], fast["req"]["id"], "fast.delivery")

    def assert_sub(delivery_id: str, child_id: str, label: str) -> None:
        rows = api(
            s,
            "GET",
            f"https://devops.aliyun.com/projex/api/workitem/v2/workitem/{delivery_id}/relation/workitem/list/by-relation-category?category=PARENT_SUB&isForward=true",
        ).get("result") or []
        ids = {r.get("identifier") for r in rows}
        if child_id not in ids:
            raise RuntimeError(
                f"{label} 未出现在交付子项：期望 {child_id}，实际 {[r.get('serialNumber') for r in rows]}"
            )

    assert_sub(normal["delivery"]["id"], normal["analysis"]["id"], "normal.analysis")
    assert_sub(normal["delivery"]["id"], normal["design"]["id"], "normal.design")
    assert_sub(fast["delivery"]["id"], fast["design"]["id"], "fast.design")
    verify = {
        "normal_req": get(s, normal["req"]["id"])["status"]["displayName"],
        "fast_req": get(s, fast["req"]["id"])["status"]["displayName"],
        "normal_delivery_assignee": (
            get(s, normal["delivery"]["id"]).get("assignedTo") or {}
        ).get("displayName"),
        "fast_delivery_assignee": (get(s, fast["delivery"]["id"]).get("assignedTo") or {}).get(
            "displayName"
        ),
        "delivery_associated_ok": True,
        "stage_tasks_as_sub_ok": True,
        "fast_design_associated_ok": fast.get("design_associated_ok"),
    }
    out = {
        "normal": normal,
        "fast": fast,
        "verify": verify,
        "auth_elapsed_s": auth_s,
        "wall_elapsed_s": build_s,
        "created_at": datetime.now(TZ).isoformat(),
        "mode": "live_create_fast_v5_fast_track_rules",
        "opts": {
            "create_includes_plan_start": True,
            "skip_plan_end_on_create": True,
            "tracked_transit_no_get": True,
            "delivery_assignee_hefei_at_create": True,
            "overlap_tag_with_create": True,
            "fast_req_hours": f"{FAST_EST}+{FAST_ACT}",
            "relation": "delivery ASSOCIATED→req; analysis/design TASK_SUB→delivery; design post ASSOCIATED→req",
            "http": "requests.Session keep-alive",
        },
    }
    Path("/tmp/yunxiao_pmapp_fast_v2_result.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2)
    )
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
