#!/usr/bin/env python3
"""标签候选列表（聚合工作项 tag + runtime）；未命中可 --match 后自动重拉一次。"""
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
        raise RuntimeError("缺少 XSRF-TOKEN")
    return jar


def session() -> requests.Session:
    jar = load_jar()
    x = jar.get("XSRF-TOKEN", "")
    xsrf = urllib.parse.unquote(x) if "%" in x else x
    s = requests.Session()
    s.headers.update(
        {
            "Cookie": "; ".join(f"{k}={v}" for k, v in jar.items()),
            "x-xsrf-token": xsrf,
            "X-XSRF-TOKEN": xsrf,
            "Origin": "https://devops.aliyun.com",
            "Referer": "https://devops.aliyun.com/projex",
            "accept": "application/json",
            "Content-Type": "application/json",
        }
    )
    return s


def fetch_tags(space_id: str) -> list[dict[str, str]]:
    s = session()
    by_id: dict[str, str] = {}
    for name, tid in (RUNTIME.get("tags") or {}).items():
        by_id[tid] = name
    body = {
        "spaceIdentifier": space_id,
        "spaceType": "Project",
        "category": "Req",
        "toPage": 1,
        "pageSize": 100,
        "conditions": json.dumps({"conditionGroups": [[]]}),
    }
    rows = (
        s.post(
            "https://devops.aliyun.com/projex/api/workitem/workitem/list?_input_charset=utf-8",
            json=body,
            timeout=30,
        )
        .json()
        .get("result")
        or []
    )
    for row in rows:
        for t in row.get("tag") or []:
            tid = t.get("identifier")
            name = t.get("name") or t.get("displayName")
            if tid and name:
                by_id[tid] = name
    # Task 再扫一页，补标签
    body["category"] = "Task"
    rows = (
        s.post(
            "https://devops.aliyun.com/projex/api/workitem/workitem/list?_input_charset=utf-8",
            json=body,
            timeout=30,
        )
        .json()
        .get("result")
        or []
    )
    for row in rows:
        for t in row.get("tag") or []:
            tid = t.get("identifier")
            name = t.get("name") or t.get("displayName")
            if tid and name:
                by_id[tid] = name
    return [{"name": n, "identifier": i} for i, n in sorted(by_id.items(), key=lambda x: x[1])]


def match_tags(tags: list[dict[str, str]], query: str) -> list[dict[str, str]]:
    q = query.strip().lower()
    hits = []
    for t in tags:
        name = (t.get("name") or "").lower()
        if q == name or q in name or name in q:
            hits.append(t)
    return hits


def list_tags(*, space_id: str, match: str | None = None, prefer: str | None = None) -> dict[str, Any]:
    tags = fetch_tags(space_id)
    # prefer 置顶
    if prefer:
        prefer_l = prefer.strip().lower()
        tags = sorted(
            tags,
            key=lambda t: (0 if (t.get("name") or "").lower() == prefer_l else 1, t.get("name") or ""),
        )
    out: dict[str, Any] = {
        "fetched_at": datetime.now(TZ).isoformat(),
        "spaceIdentifier": space_id,
        "count": len(tags),
        "tags": tags,
        "refetched": False,
        "note": "标签未命中须自动重拉一次并重生 4.A/B/C 选项；见 compact-select.md",
    }
    if not match:
        return out
    hits = match_tags(tags, match)
    if len(hits) == 1:
        out["matches"] = hits
        out["match_status"] = "unique"
        return out
    # 无法对应 → 重拉一次
    tags2 = fetch_tags(space_id)
    if prefer:
        prefer_l = prefer.strip().lower()
        tags2 = sorted(
            tags2,
            key=lambda t: (0 if (t.get("name") or "").lower() == prefer_l else 1, t.get("name") or ""),
        )
    hits2 = match_tags(tags2, match)
    out["tags"] = tags2
    out["count"] = len(tags2)
    out["refetched"] = True
    out["refetch_reason"] = "首次0命中" if len(hits) == 0 else "首次多命中"
    out["matches"] = hits2
    if len(hits2) == 1:
        out["match_status"] = "unique_after_refetch"
    elif len(hits2) == 0:
        out["match_status"] = "none_after_refetch"
        out["note"] = "已自动重拉标签列表仍无法对应；请用户点选 4.x；禁止再拉第3次"
    else:
        out["match_status"] = "ambiguous_after_refetch"
    out["fetched_at"] = datetime.now(TZ).isoformat()
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--space", required=True, help="spaceIdentifier")
    ap.add_argument("--match", help="标签名")
    ap.add_argument("--prefer", help="置顶标签名")
    args = ap.parse_args()
    print(
        json.dumps(
            list_tags(space_id=args.space, match=args.match, prefer=args.prefer),
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
