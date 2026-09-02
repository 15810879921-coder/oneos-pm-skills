#!/usr/bin/env python3
"""Build deterministic release dependency groups from verified evidence edges."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


INPUT_SCHEMA = "oneos.release-dependency-input/v1"
OUTPUT_SCHEMA = "oneos.release-dependency-groups/v1"
SUITE_VERSION = "10.0.0"
EDGE_TYPES = {"artifact", "pipeline", "api", "package", "data", "config"}


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("输入必须是JSON对象")
    return value


def stable_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


def resolve(data: dict[str, Any]) -> dict[str, Any]:
    if data.get("schemaVersion") != INPUT_SCHEMA:
        raise ValueError(f"schemaVersion必须为{INPUT_SCHEMA}")
    raw_items = data.get("items")
    raw_edges = data.get("edges") or []
    if not isinstance(raw_items, list) or not raw_items:
        raise ValueError("items不能为空")
    if not isinstance(raw_edges, list):
        raise ValueError("edges必须是数组")
    item_ids = [str(item.get("itemId") or "") for item in raw_items if isinstance(item, dict)]
    if any(not value for value in item_ids) or len(item_ids) != len(raw_items) or len(item_ids) != len(set(item_ids)):
        raise ValueError("itemId必须完整且唯一")

    parent = {item_id: item_id for item_id in item_ids}

    def find(value: str) -> str:
        while parent[value] != value:
            parent[value] = parent[parent[value]]
            value = parent[value]
        return value

    def union(left: str, right: str) -> None:
        left_root, right_root = find(left), find(right)
        if left_root != right_root:
            parent[max(left_root, right_root)] = min(left_root, right_root)

    blockers: list[str] = []
    accepted_edges: list[dict[str, Any]] = []
    for index, edge in enumerate(raw_edges):
        if not isinstance(edge, dict):
            blockers.append(f"edges[{index}]必须是对象")
            continue
        left, right = str(edge.get("from") or ""), str(edge.get("to") or "")
        edge_type = str(edge.get("type") or "")
        evidence = str(edge.get("evidenceId") or "")
        if left not in parent or right not in parent or left == right:
            blockers.append(f"edges[{index}]引用了无效事项")
            continue
        if edge_type not in EDGE_TYPES:
            blockers.append(f"edges[{index}]依赖类型无效：{edge_type}")
            continue
        if edge.get("verified") is not True or not evidence:
            blockers.append(f"edges[{index}]缺少可核验依赖证据")
            continue
        accepted_edges.append({"from": left, "to": right, "type": edge_type, "evidenceId": evidence})
        union(left, right)

    grouped: dict[str, list[str]] = {}
    for item_id in item_ids:
        grouped.setdefault(find(item_id), []).append(item_id)
    groups = []
    for members in sorted((sorted(values) for values in grouped.values()), key=lambda value: value[0]):
        group_edges = [edge for edge in accepted_edges if edge["from"] in members and edge["to"] in members]
        group_id = "DEP-" + stable_hash({"members": members, "edges": group_edges})[:16]
        groups.append({"dependencyGroupId": group_id, "itemIds": members, "evidenceEdges": group_edges})
    return {
        "schemaVersion": OUTPUT_SCHEMA,
        "suiteVersion": SUITE_VERSION,
        "status": "blocked" if blockers else "passed",
        "groups": groups,
        "blockers": blockers,
        "inputHash": stable_hash(data),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="根据制品、流水线、API/包、数据和配置证据生成发版依赖组")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        result = resolve(load(args.input))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "blocked", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 2
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 2 if result["status"] == "blocked" else 0


if __name__ == "__main__":
    sys.exit(main())
