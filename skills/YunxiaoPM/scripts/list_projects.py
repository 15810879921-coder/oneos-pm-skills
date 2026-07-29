#!/usr/bin/env python3
"""拉取云效项目列表（供 YunxiaoPMapp 门禁 PJ 点选）。stdout = JSON。

无法对应时自动重拉一次：
  python3 scripts/list_projects.py --match '01_ONEOS'
  python3 scripts/list_projects.py --match-id 1280be963a5a2cc126a4118dca
"""
from __future__ import annotations

import argparse
import json
import urllib.parse
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = json.loads((ROOT / "assets" / "runtime-ids.json").read_text())
ORG = RUNTIME.get("project", {}).get("organizationIdentifier", "697c54a19df7fdfa65466405")
WANG = RUNTIME.get("people", {}).get("wangmian", {}).get("identifier", "6811df000601d2fea60144a9")
ALIASES = [a.lower() for a in (RUNTIME.get("project", {}).get("name_aliases") or [])]
TZ = timezone(timedelta(hours=8))


def load_jar() -> dict[str, str]:
    jar: dict[str, str] = {}
    try:
        import browser_cookie3

        for domain in (".aliyun.com", "devops.aliyun.com", ".devops.aliyun.com"):
            try:
                for c in browser_cookie3.chrome(domain_name=domain):
                    jar[c.name] = c.value
            except Exception:
                pass
    except Exception:
        pass
    if not jar.get("XSRF-TOKEN"):
        p = Path("/tmp/yunxiao_cookies.json")
        if p.exists():
            raw = json.loads(p.read_text())
            jar = (
                raw
                if isinstance(raw, dict) and "XSRF-TOKEN" in raw
                else {c["name"]: c["value"] for c in raw.get("cookies", [])}
            )
    if not jar.get("XSRF-TOKEN"):
        raise RuntimeError("缺少 XSRF-TOKEN：请先在 Chrome 登录 devops.aliyun.com")
    return jar


def fetch_projects() -> list[dict[str, Any]]:
    jar = load_jar()
    x = jar.get("XSRF-TOKEN", "")
    xsrf = urllib.parse.unquote(x) if "%" in x else x
    cookie = "; ".join(f"{k}={v}" for k, v in jar.items())
    headers = {
        "Cookie": cookie,
        "x-xsrf-token": xsrf,
        "X-XSRF-TOKEN": xsrf,
        "Origin": "https://devops.aliyun.com",
        "Referer": "https://devops.aliyun.com/projex",
        "accept": "application/json",
    }
    extra = json.dumps(
        {
            "conditionGroups": [
                [
                    {
                        "className": "user",
                        "fieldIdentifier": "users",
                        "format": "multiList",
                        "operator": "CONTAINS",
                        "value": [WANG],
                    }
                ],
                [
                    {
                        "className": "string",
                        "fieldIdentifier": "scope",
                        "format": "list",
                        "operator": "CONTAINS",
                        "value": ["public"],
                    }
                ],
            ]
        },
        separators=(",", ":"),
    )
    params = {
        "extraConditions": extra,
        "conditions": json.dumps({"conditionGroups": [[]]}, separators=(",", ":")),
        "orderBy": json.dumps(
            {
                "fieldIdentifier": "gmtCreate",
                "format": "input",
                "order": "desc",
                "className": "date",
            },
            separators=(",", ":"),
        ),
        "scope": "all",
        "category": "Project",
        "toPage": 1,
        "pageSize": 100,
        "_input_charset": "utf-8",
    }
    r = requests.get(
        "https://devops.aliyun.com/projex/api/workspace/project/search/list",
        headers=headers,
        params=params,
        timeout=30,
    )
    r.raise_for_status()
    rows = r.json().get("result") or []
    return [
        {
            "name": p.get("name"),
            "identifier": p.get("identifier"),
            "customCode": p.get("customCode"),
            "logicalStatus": p.get("logicalStatus"),
            "status": (p.get("status") or {}).get("displayName"),
            "scope": p.get("scope"),
        }
        for p in rows
    ]


def match_projects(
    projects: list[dict[str, Any]],
    *,
    query: str | None = None,
    space_id: str | None = None,
) -> list[dict[str, Any]]:
    if space_id:
        sid = space_id.strip()
        return [p for p in projects if p.get("identifier") == sid]
    if not query:
        return []
    q = query.strip().lower()
    hits: list[dict[str, Any]] = []
    for p in projects:
        name = (p.get("name") or "").lower()
        code = (p.get("customCode") or "").lower()
        if q == name or q == code or q in name or name in q:
            hits.append(p)
            continue
        if q in ALIASES and (code == "oneos" or "oneos" in name or "运营" in name):
            hits.append(p)
    # de-dupe by identifier
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for p in hits:
        i = p.get("identifier") or ""
        if i in seen:
            continue
        seen.add(i)
        out.append(p)
    return out


def list_projects(
    *,
    match: str | None = None,
    match_id: str | None = None,
) -> dict:
    projects = fetch_projects()
    payload: dict[str, Any] = {
        "fetched_at": datetime.now(TZ).isoformat(),
        "organizationIdentifier": ORG,
        "count": len(projects),
        "projects": projects,
        "selection_required": True,
        "refetched": False,
        "note": "禁止默认直指；须 AskQuestion/Plan 点选后再写入 spaceIdentifier",
    }
    if not match and not match_id:
        return payload

    hits = match_projects(projects, query=match, space_id=match_id)
    if len(hits) == 1:
        payload["matches"] = hits
        payload["match_status"] = "unique"
        return payload

    # 无法对应（0 或多）→ 自动重拉一次
    projects2 = fetch_projects()
    hits2 = match_projects(projects2, query=match, space_id=match_id)
    payload["projects"] = projects2
    payload["count"] = len(projects2)
    payload["refetched"] = True
    payload["refetch_reason"] = "无法对应" if len(hits) != 1 else "unexpected"
    if len(hits) == 0:
        payload["refetch_reason"] = "首次0命中"
    elif len(hits) > 1:
        payload["refetch_reason"] = "首次多命中"
    payload["matches"] = hits2
    if len(hits2) == 1:
        payload["match_status"] = "unique_after_refetch"
    elif len(hits2) == 0:
        payload["match_status"] = "none_after_refetch"
        payload["note"] = "已自动重拉一次仍无法对应；请用户从最新列表点选；禁止再拉第3次"
    else:
        payload["match_status"] = "ambiguous_after_refetch"
        payload["note"] = "已自动重拉一次仍多命中；请用户点选；禁止自动选定"
    payload["fetched_at"] = datetime.now(TZ).isoformat()
    return payload


def main() -> None:
    ap = argparse.ArgumentParser(description="YunxiaoPMapp 项目列表 / 匹配（无法对应则重拉一次）")
    ap.add_argument("--match", help="按项目名或 customCode 匹配")
    ap.add_argument("--match-id", help="按 spaceIdentifier 匹配")
    args = ap.parse_args()
    print(
        json.dumps(
            list_projects(match=args.match, match_id=args.match_id),
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
