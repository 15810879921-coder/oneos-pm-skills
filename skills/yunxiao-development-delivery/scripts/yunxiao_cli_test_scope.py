#!/usr/bin/env python3
"""Resolve an exact requirement TestHub plan and one delivery-end scope read-only."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import yunxiao_cli_runtime as core


SCOPE_PATTERN = re.compile(r"^\[(Web|小程序|跨端)\]\s*")


def write_receipt(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def items(value: Any) -> list[dict[str, Any]]:
    value = core.unwrap(value)
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        for key in ("items", "list", "records", "result"):
            candidate = value.get(key)
            if isinstance(candidate, list):
                return [item for item in candidate if isinstance(item, dict)]
    return []


def list_plans(executable: str, project_id: str) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for page in range(1, 101):
        batch = items(core.run_devops(executable, [
            "test-hub-list-test-plan", "--project-identifier", project_id,
            "--page", str(page), "--per-page", "100",
        ]))
        result.extend(batch)
        if len(batch) < 100:
            break
    return result


def flatten_directories(value: Any) -> list[dict[str, Any]]:
    flattened: list[dict[str, Any]] = []

    def walk(node: Any) -> None:
        if isinstance(node, list):
            for child in node:
                walk(child)
            return
        if not isinstance(node, dict):
            return
        identifier = str(node.get("identifier") or node.get("id") or "")
        name = str(node.get("displayName") or node.get("name") or "")
        if identifier and name:
            flattened.append({
                "id": identifier,
                "name": name,
                "caseCount": int(node.get("workitemCount") or 0),
                "parentId": str(node.get("parentIdentifier") or ""),
            })
        children = node.get("children")
        if isinstance(children, (dict, list)):
            walk(children)
        for child in node.values():
            if child is not children and isinstance(child, list):
                walk(child)

    walk(core.unwrap(value))
    return flattened


def exact_requirement_match(name: str, requirement_sn: str) -> bool:
    return bool(re.search(rf"(?<![A-Za-z0-9-]){re.escape(requirement_sn)}(?![A-Za-z0-9-])",
                          name, flags=re.IGNORECASE))


def command_resolve(args: argparse.Namespace) -> int:
    executable = core.find_aliyun()
    core.require_auth_env()
    end = "Web" if args.delivery_end == "PC" else args.delivery_end
    plans = list_plans(executable, args.project_id)
    exact = [plan for plan in plans if exact_requirement_match(
        str(plan.get("name") or ""), args.requirement_sn)]
    selected: dict[str, Any] | None = None
    match_mode = ""
    if args.test_plan_id:
        explicit = [plan for plan in plans if str(plan.get("testPlanIdentifier") or "") == args.test_plan_id]
        if len(explicit) != 1:
            raise core.AdapterError("指定testPlanId不在当前项目中或不唯一。")
        selected = explicit[0]
        match_mode = "explicit"
    elif len(exact) == 1:
        selected = exact[0]
        match_mode = "requirement-number"
    elif len(exact) > 1:
        payload = {"decision": "ambiguous-plan", "requirement": args.requirement_sn,
                   "plans": [{"id": str(item.get("testPlanIdentifier") or ""), "name": item.get("name")}
                             for item in exact]}
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 3
    else:
        payload = {"decision": "no-formal-plan", "requirement": args.requirement_sn,
                   "deliveryEnd": end, "matchedBy": "requirement-number",
                   "note": "未发现名称含精确需求编号的计划；历史计划须显式指定testPlanId。"}
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    plan_id = str(selected.get("testPlanIdentifier") or "")
    tree = core.run_devops(executable, [
        "test-hub-get-test-plan-result-directory-list", "--test-plan-identifier", plan_id,
    ])
    directories = flatten_directories(tree)
    selected_directories = []
    untagged = []
    for directory in directories:
        match = SCOPE_PATTERN.match(directory["name"])
        if not match:
            untagged.append(directory)
            continue
        if match.group(1) == end:
            selected_directories.append(directory)
    decision = "formal-plan" if selected_directories else "scope-unconfigured"
    payload = {
        "schemaVersion": "oneos.test-scope-resolution/v1",
        "decision": decision,
        "projectId": args.project_id,
        "requirement": args.requirement_sn,
        "deliveryEnd": end,
        "testPlan": {"id": plan_id, "name": selected.get("name"), "matchMode": match_mode},
        "scopeDirectories": selected_directories,
        "untaggedDirectoryCount": len(untagged),
    }
    target = Path(args.output) if args.output else core.output_dir() / \
        f"test-scope-{args.requirement_sn.lower()}-{end.lower()}.json"
    write_receipt(target, payload)
    payload["receipt"] = str(target)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if decision == "formal-plan" else 4


def main() -> int:
    parser = argparse.ArgumentParser(description="云效需求测试计划与端侧范围只读解析")
    sub = parser.add_subparsers(dest="command", required=True)
    resolve = sub.add_parser("resolve")
    resolve.add_argument("--project-id", required=True)
    resolve.add_argument("--requirement-sn", required=True)
    resolve.add_argument("--delivery-end", required=True, choices=("Web", "PC", "小程序", "跨端"))
    resolve.add_argument("--test-plan-id")
    resolve.add_argument("--output")
    resolve.set_defaults(func=command_resolve)
    args = parser.parse_args()
    try:
        return args.func(args)
    except (core.AdapterError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": core.scrub(str(exc))}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
