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
from yunxiao_testhub_read_api import list_plans_json


SCOPE_PATTERN = re.compile(r"^\[(Web|小程序|跨端)\]\s*")
TRACE_ID_PATTERN = re.compile(r'"?traceId"?\s*[:=]\s*"?([A-Za-z0-9_-]+)', re.IGNORECASE)


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


def testcase_id(item: dict[str, Any]) -> str:
    for key in ("testcaseIdentifier", "workitemIdentifier", "identifier", "id"):
        if item.get(key):
            return str(item[key])
    nested = item.get("testcase")
    return testcase_id(nested) if isinstance(nested, dict) else ""


def result_id(item: dict[str, Any]) -> str:
    for key in ("testResultIdentifier", "resultIdentifier", "executionIdentifier"):
        if item.get(key):
            return str(item[key])
    return ""


def result_status(item: dict[str, Any]) -> str:
    for key in ("status", "testResultStatus", "resultStatus"):
        value = item.get(key)
        if isinstance(value, str):
            return value.upper()
        if isinstance(value, dict):
            for nested in ("identifier", "name", "value"):
                if value.get(nested):
                    return str(value[nested]).upper()
    return ""


def list_directory_cases(executable: str, plan_id: str,
                         directories: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for directory in directories:
        directory_id = str(directory["id"])
        response = core.run_devops(executable, [
            "test-hub-get-test-result-list",
            "--test-plan-identifier", plan_id,
            "--directory-identifier", directory_id,
        ])
        for item in items(response):
            case_id = testcase_id(item)
            if not case_id or case_id in seen:
                continue
            seen.add(case_id)
            selected.append({
                "directoryId": directory_id,
                "testcaseId": case_id,
                "testResultId": result_id(item) or None,
                "status": result_status(item) or None,
            })
    return selected


def retryable_plan_read_error(error: Exception) -> bool:
    text = core.scrub(str(error)).lower()
    denied = (
        "statuscode: 400", "statuscode: 401", "statuscode: 403", "statuscode: 404",
        "unauthorized", "forbidden", "permission", "无权限", "鉴权", "令牌",
    )
    if any(marker in text for marker in denied):
        return False
    retryable = (
        "statuscode: 5", "content type", "timeout", "timed out", "connection",
        "request execution failed", "not a valid api", "unknown command", "eof",
    )
    return any(marker in text for marker in retryable)


def trace_ids(*errors: str) -> list[str]:
    result: list[str] = []
    for error in errors:
        for value in TRACE_ID_PATTERN.findall(error or ""):
            if value not in result:
                result.append(value)
    return result


def discover_plans(project_id: str) -> tuple[list[dict[str, Any]] | None, dict[str, Any]]:
    # The CLI form Content-Type defect is confirmed: never probe it or upgrade
    # the plugin as a prerequisite for this independently supported public API.
    discovery: dict[str, Any] = {
        "status": "available-json-api",
        "transport": "official-openapi-json",
        "contentType": "application/json",
        "upgradeAttempted": False,
        "retryAttempted": False,
        "jsonReadAttempted": True,
        "jsonReadSucceeded": False,
        "traceIds": [],
    }
    try:
        plans = list_plans_json(project_id)
    except core.AdapterError as error:
        if not retryable_plan_read_error(error):
            raise
        diagnostic = core.scrub(str(error))
        discovery.update(status="unavailable-json-api", jsonReadError=diagnostic,
                         traceIds=trace_ids(diagnostic))
        return None, discovery
    discovery["jsonReadSucceeded"] = True
    return plans, discovery


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
    target = Path(args.output) if args.output else core.output_dir() / \
        f"test-scope-{args.requirement_sn.lower()}-{end.lower()}-{args.development_task_sn.lower()}.json"
    plans, discovery = discover_plans(args.project_id)
    if plans is None:
        payload = {
            "schemaVersion": "oneos.test-scope-resolution/v2",
            "decision": "plan-read-skipped",
            "requirement": args.requirement_sn,
            "projectId": args.project_id,
            "developmentTask": args.development_task_sn,
            "deliveryEnd": end,
            "testTaskRequired": True,
            "testMode": "mandatory-test-task",
            "testPlan": None,
            "scopeDirectories": [],
            "directoryIds": [],
            "selectedCaseIds": [],
            "selectedCaseResults": [],
            "formalTestValidationSkipped": True,
            "skipReason": "plan-read-unavailable-json-api",
            "planDiscovery": discovery,
            "note": "官方JSON测试计划读取失败；本次跳过正式TestHub计划/用例验证，仍须创建独立【测试】任务。最终回报必须披露真实读取错误和traceId；不得宣称无计划或测试通过，不执行无关插件升级。",
        }
        write_receipt(target, payload)
        payload["receipt"] = str(target)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
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
        payload = {"schemaVersion": "oneos.test-scope-resolution/v2",
                   "decision": "ambiguous-plan", "requirement": args.requirement_sn,
                   "projectId": args.project_id,
                   "developmentTask": args.development_task_sn, "deliveryEnd": end,
                   "testTaskRequired": True,
                   "plans": [{"id": str(item.get("testPlanIdentifier") or ""), "name": item.get("name")}
                             for item in exact]}
        write_receipt(target, payload)
        payload["receipt"] = str(target)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 3
    else:
        payload = {"schemaVersion": "oneos.test-scope-resolution/v2",
                   "decision": "test-task-required", "requirement": args.requirement_sn,
                   "projectId": args.project_id,
                   "developmentTask": args.development_task_sn,
                   "deliveryEnd": end, "matchedBy": "requirement-number",
                   "testTaskRequired": True, "testMode": "mandatory-test-task",
                   "testPlan": None, "scopeDirectories": [], "directoryIds": [],
                   "selectedCaseIds": [], "selectedCaseResults": [],
                   "formalTestValidationSkipped": True,
                   "skipReason": "no-associated-test-plan",
                   "planDiscovery": discovery,
                   "note": "已成功读取测试计划，但当前需求未关联正式计划；跳过正式TestHub计划/用例验证，仍须为当前开发任务创建独立【测试】任务并由QA完成。"}
        write_receipt(target, payload)
        payload["receipt"] = str(target)
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
    selected_cases = list_directory_cases(executable, plan_id, selected_directories)
    if not selected_directories:
        decision = "scope-unconfigured"
        test_mode = "mandatory-test-task"
    elif not selected_cases:
        decision = "scope-empty"
        test_mode = "mandatory-test-task"
    else:
        decision = "formal-plan"
        test_mode = "formal-plan"
    payload = {
        "schemaVersion": "oneos.test-scope-resolution/v2",
        "decision": decision,
        "projectId": args.project_id,
        "requirement": args.requirement_sn,
        "developmentTask": args.development_task_sn,
        "deliveryEnd": end,
        "testTaskRequired": True,
        "testMode": test_mode,
        "testPlan": {"id": plan_id, "name": selected.get("name"), "matchMode": match_mode},
        "scopeDirectories": selected_directories,
        "directoryIds": [str(item["id"]) for item in selected_directories],
        "selectedCaseIds": [item["testcaseId"] for item in selected_cases],
        "selectedCaseResults": selected_cases,
        "untaggedDirectoryCount": len(untagged),
        "formalTestValidationSkipped": test_mode == "mandatory-test-task",
        "skipReason": decision if test_mode == "mandatory-test-task" else None,
        "planDiscovery": discovery,
    }
    if decision == "scope-empty":
        payload["note"] = "已配置当前端目录但其中没有正式用例；仍创建独立【测试】任务，由QA补齐或执行人工测试。"
    write_receipt(target, payload)
    payload["receipt"] = str(target)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="云效需求测试计划与端侧范围只读解析")
    sub = parser.add_subparsers(dest="command", required=True)
    resolve = sub.add_parser("resolve")
    resolve.add_argument("--project-id", required=True)
    resolve.add_argument("--requirement-sn", required=True)
    resolve.add_argument("--development-task-sn", required=True)
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
