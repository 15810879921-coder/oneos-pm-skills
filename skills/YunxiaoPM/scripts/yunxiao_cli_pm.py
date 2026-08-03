#!/usr/bin/env python3
"""Official aliyun devops CLI adapter for YunxiaoPM standard lifecycle writes."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import yunxiao_cli_runtime as core


SCHEMA = "oneos.yunxiao-pm-cli/v1"


def canonical_hash(value: Any, excluded: set[str] | None = None) -> str:
    if isinstance(value, dict) and excluded:
        value = {k: v for k, v in value.items() if k not in excluded}
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True,
                     separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def rows(value: Any, label: str) -> list[dict[str, Any]]:
    value = core.unwrap(value)
    if value is None:
        return []
    if not isinstance(value, list):
        raise core.AdapterError(f"{label}返回结构异常。")
    return [row for row in value if isinstance(row, dict)]


def get_project(executable: str, project_id: str) -> dict[str, Any]:
    value = core.unwrap(core.run_devops(executable, ["projex-get-project", "--id", project_id]))
    if not isinstance(value, dict) or str(value.get("id") or "") != project_id:
        raise core.AdapterError("项目无法唯一回读。")
    if str(value.get("logicalStatus") or "NORMAL").upper() != "NORMAL":
        raise core.AdapterError("项目不是正常状态。")
    return value


def search_workitems(executable: str, project_id: str, category: str) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for page in range(1, 101):
        batch = rows(core.run_devops(executable, [
            "projex-search-workitems", "--category", category,
            "--space-id", project_id, "--space-type", "Project",
            "--page", str(page), "--per-page", "200", "--sort", "asc",
        ]), f"{category}工作项查询")
        result.extend(batch)
        if len(batch) < 200:
            break
    return result


def get_workitem(executable: str, workitem_id: str) -> dict[str, Any]:
    value = core.unwrap(core.run_devops(executable, ["projex-get-workitem", "--id", workitem_id]))
    if not isinstance(value, dict) or not value.get("id"):
        raise core.AdapterError(f"工作项{workitem_id}回读失败。")
    return value


def status_name(item: dict[str, Any]) -> str:
    status = item.get("status") or {}
    return str(status.get("displayName") or status.get("name") or "")


def owner_id(item: dict[str, Any]) -> str:
    owner = item.get("assignedTo") or {}
    return str(owner.get("id") or owner.get("identifier") or "")


def serial(item: dict[str, Any]) -> str:
    return str(item.get("serialNumber") or item.get("identifier") or "")


def snapshot_item(item: dict[str, Any] | None) -> dict[str, Any] | None:
    if not item:
        return None
    return {
        "id": str(item.get("id") or ""), "serialNumber": serial(item),
        "subject": item.get("subject"), "status": status_name(item),
        "ownerId": owner_id(item), "parentId": str(item.get("parentId") or ""),
        "logicalStatus": item.get("logicalStatus"),
    }


def exact_member(executable: str, name: str) -> dict[str, str]:
    value = rows(core.run_devops(executable, [
        "base-search-members", "--query", name, "--page", "1", "--per-page", "100",
    ]), "成员查询")
    matches = [row for row in value if str(row.get("name") or "") == name
               and (row.get("userId") or row.get("id"))]
    ids = {str(row.get("userId") or row.get("id")) for row in matches}
    if len(ids) != 1:
        raise core.AdapterError(f"成员{name}无法唯一解析。")
    return {"id": next(iter(ids)), "name": name}


def exact_type(executable: str, project_id: str, category: str, name: str) -> dict[str, Any]:
    values = rows(core.run_devops(executable, [
        "projex-list-workitem-types", "--id", project_id, "--category", category,
    ]), "工作项类型查询")
    matches = [row for row in values if str(row.get("name") or "") == name and row.get("id")]
    if len(matches) != 1:
        raise core.AdapterError(f"工作项类型{name}无法唯一解析。")
    return matches[0]


def field_config(executable: str, project_id: str, type_id: str) -> list[dict[str, Any]]:
    return rows(core.run_devops(executable, [
        "projex-get-workitem-type-field-config", "--project-id", project_id,
        "--id", type_id,
    ]), "字段配置查询")


def priority_id(fields: list[dict[str, Any]], name: str) -> str:
    field = [row for row in fields if str(row.get("id")) == "priority"]
    if len(field) != 1:
        raise core.AdapterError("优先级字段无法唯一解析。")
    matches = [str(row.get("id")) for row in field[0].get("options") or []
               if str(row.get("displayValue") or row.get("value") or "") == name]
    if len(set(matches)) != 1:
        raise core.AdapterError(f"优先级{name}无法唯一解析。")
    return matches[0]


def exact_label(executable: str, project_id: str, name: str) -> dict[str, str]:
    values = rows(core.run_devops(executable, [
        "projex-list-labels", "--id", project_id, "--page", "1", "--per-page", "100",
    ]), "标签查询")
    matches = [row for row in values if str(row.get("name") or "") == name and row.get("id")]
    if len(matches) != 1:
        raise core.AdapterError(f"标签{name}无法唯一解析。")
    return {"id": str(matches[0]["id"]), "name": name}


def status_ids(executable: str, project_id: str, type_id: str,
               required: list[str]) -> dict[str, str]:
    value = core.unwrap(core.run_devops(executable, [
        "projex-get-workitem-workflow", "--project-id", project_id, "--id", type_id,
    ]))
    statuses = value.get("statuses") if isinstance(value, dict) else []
    result: dict[str, str] = {}
    for name in required:
        matches = [str(row.get("id")) for row in statuses or [] if isinstance(row, dict)
                   and row.get("id") and name in {
                       str(row.get("name") or ""), str(row.get("displayName") or "")
                   }]
        if len(set(matches)) != 1:
            raise core.AdapterError(f"状态{name}无法唯一解析。")
        result[name] = matches[0]
    return result


def relation_ids(executable: str, source_id: str, relation_type: str) -> list[str]:
    value = rows(core.run_devops(executable, [
        "projex-list-workitem-relation-records", "--id", source_id,
        "--relation-type", relation_type,
    ]), f"{relation_type}关系查询")
    return sorted({str(row.get("resourceId")) for row in value if row.get("resourceId")})


def ensure_relation(executable: str, source_id: str, relation_type: str,
                    target_id: str) -> str:
    if target_id in relation_ids(executable, source_id, relation_type):
        return "idempotent"
    core.run_devops(executable, [
        "projex-create-workitem-relation-record", "--id", source_id,
        "--relation-type", relation_type, "--workitem-id", target_id,
    ])
    if target_id not in relation_ids(executable, source_id, relation_type):
        raise core.AdapterError(f"{relation_type}关系创建后回读失败。")
    return "created"


def managed_matches(executable: str, project_id: str, category: str,
                    marker: str, prefix: str | None = None) -> list[dict[str, Any]]:
    result = []
    for row in search_workitems(executable, project_id, category):
        if str(row.get("logicalStatus") or "NORMAL").upper() != "NORMAL":
            continue
        if prefix and not str(row.get("subject") or "").startswith(prefix):
            continue
        live = get_workitem(executable, str(row["id"]))
        if marker in str(live.get("description") or ""):
            result.append(live)
    return result


def list_sprints(executable: str, project_id: str) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for page in range(1, 101):
        batch = rows(core.run_devops(executable, [
            "projex-list-sprints", "--id", project_id, "--page", str(page),
            "--per-page", "100",
        ]), "迭代查询")
        result.extend(batch)
        if len(batch) < 100:
            break
    return result


def load_text(path: str) -> str:
    value = Path(path).read_text(encoding="utf-8").strip()
    if not value:
        raise core.AdapterError(f"文档为空：{path}")
    return value


def build_scope(executable: str, args: argparse.Namespace) -> dict[str, Any]:
    project = get_project(executable, args.space_id)
    if str(project.get("name") or "") != args.project_name:
        raise core.AdapterError("项目名称与ID不一致。")
    current = core.current_user(executable)
    delivery_owner = exact_member(executable, args.delivery_owner)
    stage_owner = exact_member(executable, args.stage_owner)
    req_type = exact_type(executable, args.space_id, "Req", "产品类需求")
    task_type = exact_type(executable, args.space_id, "Task", "任务")
    priority = priority_id(field_config(executable, args.space_id, str(req_type["id"])),
                           args.priority)
    label = exact_label(executable, args.space_id, args.label)
    req_statuses = status_ids(executable, args.space_id, str(req_type["id"]), [
        "待处理", "已确认", "分析中", "设计中", "设计完成", "待开发",
    ])
    task_statuses = status_ids(executable, args.space_id, str(task_type["id"]), [
        "待处理", "已完成",
    ])
    marker = f"oneos.pm.lifecycle/{args.idempotency_key}"
    existing = {
        "requirement": managed_matches(executable, args.space_id, "Req", marker),
        "delivery": managed_matches(executable, args.space_id, "Task", marker, "【交付】"),
        "analysis": managed_matches(executable, args.space_id, "Task", marker, "【分析】"),
        "design": managed_matches(executable, args.space_id, "Task", marker, "【设计】"),
    }
    for label_name, values in existing.items():
        if len(values) > 1:
            raise core.AdapterError(f"幂等键下存在多条{label_name}，拒绝自动选择。")
    sprint_matches = [row for row in list_sprints(executable, args.space_id)
                      if str(row.get("name") or "") == args.sprint_name]
    if len(sprint_matches) > 1:
        raise core.AdapterError("同名迭代不唯一。")
    return {
        "project": {"id": args.space_id, "name": args.project_name,
                    "customCode": project.get("customCode")},
        "currentUser": current,
        "deliveryOwner": delivery_owner,
        "stageOwner": stage_owner,
        "workitemTypes": {"requirement": str(req_type["id"]), "task": str(task_type["id"])},
        "priority": {"id": priority, "name": args.priority},
        "label": label,
        "statuses": {"requirement": req_statuses, "task": task_statuses},
        "existing": {key: snapshot_item(value[0]) if value else None
                     for key, value in existing.items()},
        "sprint": {"existing": sprint_matches[0] if sprint_matches else None,
                   "name": args.sprint_name, "startDate": args.start_date,
                   "endDate": args.end_date},
        "marker": marker,
    }


def preflight_args(value: dict[str, Any]) -> argparse.Namespace:
    source = value["input"]
    return argparse.Namespace(**{
        "space_id": source["spaceId"], "project_name": source["projectName"],
        "subject": source["subject"], "description_file": source["descriptionFile"],
        "delivery_file": source["deliveryFile"], "priority": source["priority"],
        "label": source["label"], "delivery_owner": source["deliveryOwner"],
        "stage_owner": source["stageOwner"], "sprint_name": source["sprintName"],
        "start_date": source["startDate"], "end_date": source["endDate"],
        "idempotency_key": source["idempotencyKey"],
    })


def create_item(executable: str, *, owner: str, project: str, subject: str,
                type_id: str, description: str, priority: str, label: str,
                parent_id: str | None = None, sprint_id: str | None = None,
                start: str | None = None, finish: str | None = None) -> dict[str, Any]:
    custom = {"priority": priority}
    if start:
        custom["79"] = start + " 12:00:00"
    if finish:
        custom["80"] = finish + " 23:59:59"
    args = [
        "projex-create-workitem", "--assigned-to", owner, "--space-id", project,
        "--subject", subject, "--workitem-type-id", type_id,
        "--description", description, "--format-type", "MARKDOWN",
        "--custom-field-values", json.dumps(custom, ensure_ascii=False, separators=(",", ":")),
        "--labels", label,
    ]
    if parent_id:
        args.extend(["--parent-id", parent_id])
    if sprint_id:
        args.extend(["--sprint", sprint_id])
    value = core.unwrap(core.run_devops(executable, args))
    workitem_id = str(value.get("id") if isinstance(value, dict) else "")
    if not workitem_id:
        raise core.AdapterError("创建工作项后未取得内部ID。")
    return get_workitem(executable, workitem_id)


def update_item(executable: str, workitem_id: str, body: dict[str, Any]) -> dict[str, Any]:
    core.run_devops(executable, [
        "projex-update-workitem", "--id", workitem_id, "--biz-body",
        json.dumps(body, ensure_ascii=False, separators=(",", ":")),
    ])
    return get_workitem(executable, workitem_id)


def move_status(executable: str, item: dict[str, Any], target_name: str,
                target_id: str) -> dict[str, Any]:
    if status_name(item) == target_name:
        return item
    return update_item(executable, str(item["id"]), {"status": target_id})


REQUIREMENT_STATUS_ORDER = (
    "待处理", "已确认", "分析中", "设计中", "设计完成", "待开发",
)


def advance_requirement(executable: str, item: dict[str, Any], target_name: str,
                        status_ids: dict[str, str]) -> tuple[dict[str, Any], list[str]]:
    """只向前推进需求状态；续跑时绝不把已推进的需求倒退。"""
    current_name = status_name(item)
    if current_name not in REQUIREMENT_STATUS_ORDER:
        raise core.AdapterError(f"需求当前状态不在产品阶段可推进范围内：{current_name}")
    if target_name not in REQUIREMENT_STATUS_ORDER:
        raise core.AdapterError(f"需求目标状态不在产品阶段可推进范围内：{target_name}")
    current_index = REQUIREMENT_STATUS_ORDER.index(current_name)
    target_index = REQUIREMENT_STATUS_ORDER.index(target_name)
    if current_index >= target_index:
        return item, []
    advanced: list[str] = []
    for state_name in REQUIREMENT_STATUS_ORDER[current_index + 1:target_index + 1]:
        item = move_status(executable, item, state_name, status_ids[state_name])
        if status_name(item) != state_name:
            raise core.AdapterError(f"需求状态推进后回读不一致：期望 {state_name}")
        advanced.append(state_name)
    return item, advanced


def ensure_sprint(executable: str, scope: dict[str, Any]) -> tuple[dict[str, Any], str]:
    existing = scope["sprint"]["existing"]
    if existing:
        return existing, "idempotent"
    value = core.unwrap(core.run_devops(executable, [
        "projex-create-sprint", "--id", scope["project"]["id"],
        "--name", scope["sprint"]["name"], "--owners", scope["currentUser"]["id"],
        "--start-date", scope["sprint"]["startDate"],
        "--end-date", scope["sprint"]["endDate"],
        "--description", "生命周期正向冒烟；仅挂载受管【交付】任务。",
    ]))
    sprint_id = str(value.get("id") if isinstance(value, dict) else "")
    if not sprint_id:
        raise core.AdapterError("创建迭代后未取得ID。")
    sprint = core.unwrap(core.run_devops(executable, [
        "projex-get-sprint", "--id", sprint_id,
        "--project-id", scope["project"]["id"],
    ]))
    if not isinstance(sprint, dict) or str(sprint.get("name") or "") != scope["sprint"]["name"]:
        raise core.AdapterError("迭代创建后回读失败。")
    return sprint, "created"


def cmd_doctor(_: argparse.Namespace) -> int:
    executable = core.find_aliyun()
    flags = core.require_auth_env()
    print(json.dumps({
        "schema": SCHEMA, "command": "doctor", "ready": True,
        "cliVersion": core.run_raw(executable, ["version"]),
        "pluginVersion": core.run_raw(executable, ["devops", "version"]),
        "credentialFlags": flags, "currentUser": core.current_user(executable),
    }, ensure_ascii=False, indent=2))
    return 0


def cmd_preflight(args: argparse.Namespace) -> int:
    executable = core.find_aliyun()
    core.require_auth_env()
    load_text(args.description_file)
    load_text(args.delivery_file)
    scope = build_scope(executable, args)
    value = {
        "schema": SCHEMA, "command": "preflight-standard", "createdAt": core.now_utc(),
        "input": {
            "spaceId": args.space_id, "projectName": args.project_name,
            "subject": args.subject, "descriptionFile": str(Path(args.description_file).resolve()),
            "deliveryFile": str(Path(args.delivery_file).resolve()), "priority": args.priority,
            "label": args.label, "deliveryOwner": args.delivery_owner,
            "stageOwner": args.stage_owner, "sprintName": args.sprint_name,
            "startDate": args.start_date, "endDate": args.end_date,
            "idempotencyKey": args.idempotency_key,
        },
        "documentHashes": {
            "requirement": hashlib.sha256(load_text(args.description_file).encode("utf-8")).hexdigest(),
            "delivery": hashlib.sha256(load_text(args.delivery_file).encode("utf-8")).hexdigest(),
        },
        "liveScope": scope, "scopeFingerprint": canonical_hash(scope),
    }
    value["preflightHash"] = canonical_hash(value, {"preflightHash"})
    output = Path(args.output) if args.output else core.output_dir() / "pm-standard-preflight.json"
    core.write_json(output, value)
    print(json.dumps({
        "schema": SCHEMA, "ready": True, "preflightPath": str(output),
        "preflightHash": value["preflightHash"], "scope": scope,
    }, ensure_ascii=False, indent=2))
    return 0


def cmd_apply(args: argparse.Namespace) -> int:
    executable = core.find_aliyun()
    core.require_auth_env()
    plan = json.loads(Path(args.preflight).read_text(encoding="utf-8"))
    if plan.get("schema") != SCHEMA or plan.get("preflightHash") != canonical_hash(plan, {"preflightHash"}):
        raise core.AdapterError("预检文件格式或哈希无效。")
    params = preflight_args(plan)
    if hashlib.sha256(load_text(params.description_file).encode("utf-8")).hexdigest() != plan["documentHashes"]["requirement"]:
        raise core.AdapterError("需求文档在预检后发生变化。")
    if hashlib.sha256(load_text(params.delivery_file).encode("utf-8")).hexdigest() != plan["documentHashes"]["delivery"]:
        raise core.AdapterError("交付文档在预检后发生变化。")
    scope = build_scope(executable, params)
    if canonical_hash(scope) != plan.get("scopeFingerprint"):
        raise core.AdapterError("预检后项目、成员、状态、同名对象或迭代发生变化。")

    marker = scope["marker"]
    req_doc = load_text(params.description_file) + f"\n\n<!-- {marker} -->"
    delivery_doc = load_text(params.delivery_file) + f"\n\n<!-- {marker} -->"
    ops: list[dict[str, Any]] = []
    req = scope["existing"]["requirement"]
    if req:
        req = get_workitem(executable, req["id"])
        ops.append({"operation": "requirement", "result": "idempotent"})
    else:
        req = create_item(executable, owner=scope["currentUser"]["id"],
                          project=scope["project"]["id"], subject=params.subject,
                          type_id=scope["workitemTypes"]["requirement"], description=req_doc,
                          priority=scope["priority"]["id"], label=scope["label"]["id"])
        ops.append({"operation": "requirement", "result": "created", "serial": serial(req)})

    delivery = scope["existing"]["delivery"]
    if delivery:
        delivery = get_workitem(executable, delivery["id"])
        ops.append({"operation": "delivery", "result": "idempotent"})
    else:
        delivery = create_item(executable, owner=scope["deliveryOwner"]["id"],
                               project=scope["project"]["id"],
                               subject=f"【交付】{params.subject}",
                               type_id=scope["workitemTypes"]["task"],
                               description=f"等待设计任务完成后自动填入\n\n<!-- {marker} -->",
                               priority=scope["priority"]["id"], label=scope["label"]["id"],
                               start=params.start_date)
        ops.append({"operation": "delivery", "result": "created", "serial": serial(delivery)})
    ops.append({"operation": "delivery-associated",
                "result": ensure_relation(executable, str(delivery["id"]), "ASSOCIATED", str(req["id"]))})

    analysis = scope["existing"]["analysis"]
    if analysis:
        analysis = get_workitem(executable, analysis["id"])
        ops.append({"operation": "analysis", "result": "idempotent"})
    else:
        analysis = create_item(executable, owner=scope["stageOwner"]["id"],
                               project=scope["project"]["id"],
                               subject=f"【分析】{params.subject}",
                               type_id=scope["workitemTypes"]["task"],
                               description=f"分析本次生命周期冒烟的范围、证据与隔离边界。\n\n<!-- {marker} -->",
                               priority=scope["priority"]["id"], label=scope["label"]["id"],
                               parent_id=str(delivery["id"]), start=params.start_date,
                               finish=params.start_date)
        ops.append({"operation": "analysis", "result": "created", "serial": serial(analysis)})
    ops.append({"operation": "analysis-parent",
                "result": ensure_relation(executable, str(analysis["id"]), "PARENT", str(delivery["id"]))})

    design = scope["existing"]["design"]
    if design:
        design = get_workitem(executable, design["id"])
        ops.append({"operation": "design", "result": "idempotent"})
    else:
        design = create_item(executable, owner=scope["stageOwner"]["id"],
                             project=scope["project"]["id"],
                             subject=f"【设计】{params.subject}",
                             type_id=scope["workitemTypes"]["task"],
                             description=f"设计正向生命周期标识、验证证据与发布隔离方案。\n\n<!-- {marker} -->",
                             priority=scope["priority"]["id"], label=scope["label"]["id"],
                             parent_id=str(delivery["id"]), start=params.start_date,
                             finish=params.start_date)
        ops.append({"operation": "design", "result": "created", "serial": serial(design)})
    ops.append({"operation": "design-parent",
                "result": ensure_relation(executable, str(design["id"]), "PARENT", str(delivery["id"]))})

    req_doc_final = (
        load_text(params.description_file)
        + "\n\n## 工作项编号（系统）\n"
        + f"- 交付：{serial(delivery)}\n"
        + f"- 分析：{serial(analysis)}\n"
        + f"- 设计：{serial(design)}\n\n"
        + f"<!-- {marker} -->"
    )
    req = update_item(executable, str(req["id"]), {
        "description": req_doc_final, "formatType": "MARKDOWN",
    })
    ops.append({"operation": "requirement-number-block", "result": "updated"})

    req_status = scope["statuses"]["requirement"]
    req, advanced = advance_requirement(executable, req, "设计中", req_status)
    for target in advanced:
        ops.append({"operation": "requirement-status", "target": target,
                    "result": "verified"})
    analysis = move_status(executable, analysis, "已完成", scope["statuses"]["task"]["已完成"])
    design = move_status(executable, design, "已完成", scope["statuses"]["task"]["已完成"])
    delivery = update_item(executable, str(delivery["id"]), {
        "description": delivery_doc, "formatType": "MARKDOWN",
        "assignedTo": scope["deliveryOwner"]["id"],
    })
    req, advanced = advance_requirement(executable, req, "待开发", req_status)
    for target in advanced:
        ops.append({"operation": "requirement-status", "target": target,
                    "result": "verified"})

    sprint, sprint_result = ensure_sprint(executable, scope)
    sprint_id = str(sprint.get("id") or sprint.get("identifier") or "")
    if not sprint_id:
        raise core.AdapterError("迭代ID为空。")
    delivery = update_item(executable, str(delivery["id"]), {"sprint": sprint_id})

    req = get_workitem(executable, str(req["id"]))
    delivery = get_workitem(executable, str(delivery["id"]))
    analysis = get_workitem(executable, str(analysis["id"]))
    design = get_workitem(executable, str(design["id"]))
    if status_name(req) != "待开发" or status_name(analysis) != "已完成" or status_name(design) != "已完成":
        raise core.AdapterError("产品阶段状态回读未闭合。")
    if str(req["id"]) not in relation_ids(executable, str(delivery["id"]), "ASSOCIATED"):
        raise core.AdapterError("交付到需求的正式关系回读失败。")
    if str(delivery["id"]) not in relation_ids(executable, str(analysis["id"]), "PARENT"):
        raise core.AdapterError("分析到交付的父关系回读失败。")
    if str(delivery["id"]) not in relation_ids(executable, str(design["id"]), "PARENT"):
        raise core.AdapterError("设计到交付的父关系回读失败。")
    sprint_value = delivery.get("sprint") or {}
    if sprint_value and str(sprint_value.get("id") or sprint_value.get("identifier") or "") != sprint_id:
        raise core.AdapterError("交付任务迭代回读不一致。")

    receipt = {
        "schema": SCHEMA, "command": "apply-standard", "createdAt": core.now_utc(),
        "preflightHash": plan["preflightHash"], "operations": ops,
        "project": scope["project"], "sprint": {"id": sprint_id,
            "name": scope["sprint"]["name"], "result": sprint_result},
        "requirement": snapshot_item(req), "delivery": snapshot_item(delivery),
        "analysis": snapshot_item(analysis), "design": snapshot_item(design),
    }
    receipt["receiptHash"] = canonical_hash(receipt, {"receiptHash"})
    output = Path(args.receipt) if args.receipt else core.output_dir() / "pm-standard-receipt.json"
    core.write_json(output, receipt)
    print(json.dumps({**receipt, "receiptPath": str(output)}, ensure_ascii=False, indent=2))
    return 0


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    sub = root.add_subparsers(dest="command", required=True)
    doctor = sub.add_parser("doctor")
    doctor.set_defaults(handler=cmd_doctor)
    preflight = sub.add_parser("preflight-standard")
    for name, required in (("space-id", True), ("project-name", True), ("subject", True),
                           ("description-file", True), ("delivery-file", True),
                           ("priority", True), ("label", True), ("delivery-owner", True),
                           ("stage-owner", True), ("sprint-name", True),
                           ("start-date", True), ("end-date", True),
                           ("idempotency-key", True)):
        preflight.add_argument(f"--{name}", required=required)
    preflight.add_argument("--output")
    preflight.set_defaults(handler=cmd_preflight)
    apply_cmd = sub.add_parser("apply-standard")
    apply_cmd.add_argument("--preflight", required=True)
    apply_cmd.add_argument("--receipt")
    apply_cmd.set_defaults(handler=cmd_apply)
    return root


def main() -> int:
    try:
        args = parser().parse_args()
        return int(args.handler(args))
    except (core.AdapterError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"schema": SCHEMA, "ok": False, "error": core.scrub(str(exc))},
                         ensure_ascii=False, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
