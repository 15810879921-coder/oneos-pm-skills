#!/usr/bin/env python3
"""Official aliyun devops CLI adapter for YunxiaoPM standard lifecycle writes."""

from __future__ import annotations

import argparse
import datetime as dt
import html
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import yunxiao_cli_runtime as core
import handoff_gate as hg


SCHEMA = "oneos.yunxiao-pm-cli/v2"
PRODUCT_SNAPSHOT_SCHEMA = "oneos.product-handoff-snapshot/v1"
MARKDOWN_PRODUCT_SNAPSHOT_RE = re.compile(
    r"(?ms)^## 产品交棒快照\s*\n<!-- ONEOS_PRODUCT_HANDOFF_SNAPSHOT_START id=ps-[a-f0-9]{16} sha256=[a-f0-9]{64} -->.*?<!-- ONEOS_PRODUCT_HANDOFF_SNAPSHOT_END -->\s*"
)
HTML_PRODUCT_SNAPSHOT_RE = re.compile(
    r"(?is)<h2>产品交棒快照</h2><!-- ONEOS_PRODUCT_HANDOFF_SNAPSHOT_START id=ps-[a-f0-9]{16} sha256=[a-f0-9]{64} -->.*?<!-- ONEOS_PRODUCT_HANDOFF_SNAPSHOT_END -->"
)
PRODUCT_SNAPSHOT_SECTIONS = (
    "变更范围", "PRD版本", "原型版本", "页面与交互索引", "验收入口", "未决风险",
)


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


def verified_project(executable: str, project_id: str,
                     expected_name: str | None = None) -> tuple[dict[str, Any], str]:
    project = get_project(executable, project_id)
    live_name = str(project.get("name") or "").strip()
    if not live_name:
        raise core.AdapterError("项目名称无法官方回读。")
    if expected_name and live_name != expected_name:
        raise core.AdapterError("项目名称与ID不一致。")
    return project, live_name


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
        "logicalStatus": item.get("logicalStatus"), "gmtModified": item.get("gmtModified"),
        "descriptionHash": hashlib.sha256(
            str(item.get("description") or "").encode("utf-8")).hexdigest(),
    }


def exact_member(executable: str, name_or_id: str) -> dict[str, str]:
    needle = name_or_id.strip()
    if not needle:
        raise core.AdapterError("负责人未明确；须由命令或项目配置提供姓名或userId。")
    value = rows(core.run_devops(executable, [
        "base-search-members", "--query", needle, "--page", "1", "--per-page", "100",
    ]), "成员查询")
    matches = [row for row in value if (row.get("userId") or row.get("id")) and
               needle in {str(row.get("name") or ""),
                          str(row.get("userId") or row.get("id") or "")}]
    ids = {str(row.get("userId") or row.get("id")) for row in matches}
    if len(ids) != 1:
        raise core.AdapterError(f"成员{name_or_id}无法唯一解析。")
    member_id = next(iter(ids))
    member = next(row for row in matches
                  if str(row.get("userId") or row.get("id")) == member_id)
    return {"id": member_id, "name": str(member.get("name") or needle)}


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


VERSIONED_SPRINT_RE = re.compile(
    r"^(?P<prefix>.*?(?P<endpoint>web端|Web端|WEB端|小程序端))V"
    r"(?P<major>\d+)\.(?P<minor>\d+)(?:\.(?P<patch>\d+))?$"
)


def sprint_id(item: dict[str, Any]) -> str:
    return str(item.get("id") or item.get("identifier") or "")


def sprint_owner_ids(item: dict[str, Any]) -> list[str]:
    value = item.get("owners") or item.get("owner") or []
    if isinstance(value, dict):
        value = [value]
    if not isinstance(value, list):
        value = []
    result = sorted({
        str(row.get("id") or row.get("identifier") or row.get("userId") or "")
        for row in value if isinstance(row, dict)
    } - {""})
    if not result:
        raise core.AdapterError(f"迭代{item.get('name') or sprint_id(item)}负责人无法官方回读。")
    return result


def sprint_day(value: Any, label: str) -> dt.date:
    if isinstance(value, (int, float)):
        seconds = float(value) / (1000 if abs(float(value)) > 10_000_000_000 else 1)
        return dt.datetime.fromtimestamp(
            seconds, tz=ZoneInfo("Asia/Shanghai")
        ).date()
    text = str(value or "").strip()
    if not text:
        raise core.AdapterError(f"{label}为空。")
    if text.isdigit():
        return sprint_day(int(text), label)
    try:
        if "T" in text or " " in text:
            timestamp = dt.datetime.fromisoformat(text.replace("Z", "+00:00"))
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=ZoneInfo("Asia/Shanghai"))
            return timestamp.astimezone(ZoneInfo("Asia/Shanghai")).date()
        return dt.date.fromisoformat(text[:10])
    except ValueError as exc:
        raise core.AdapterError(f"{label}不是可识别日期：{text}") from exc


def parse_versioned_sprint(item: dict[str, Any]) -> dict[str, Any]:
    name = str(item.get("name") or "").strip()
    match = VERSIONED_SPRINT_RE.fullmatch(name)
    if not match:
        raise core.AdapterError(f"来源迭代名称不是受支持的端侧版本：{name or '<empty>'}")
    endpoint_text = match.group("endpoint")
    endpoint = "Web" if "web" in endpoint_text.lower() else "小程序"
    return {
        "name": name,
        "prefix": match.group("prefix"),
        "endpoint": endpoint,
        "version": (
            int(match.group("major")),
            int(match.group("minor")),
            int(match.group("patch") or 0),
        ),
    }


def build_followup_sprint_specs(source: dict[str, Any]) -> list[dict[str, str]]:
    """以冻结来源迭代为唯一版本基线，生成连续两个 Web 子版本。"""
    parsed = parse_versioned_sprint(source)
    if parsed["endpoint"] != "Web":
        raise core.AdapterError("产品验收后自动补建仅适用于Web迭代。")
    start = sprint_day(source.get("startDate"), "来源迭代开始日期")
    end = sprint_day(source.get("endDate"), "来源迭代结束日期")
    if end < start:
        raise core.AdapterError("来源迭代结束日期早于开始日期。")
    cadence = (end - start).days + 1
    major, minor, patch = parsed["version"]
    specs: list[dict[str, str]] = []
    previous_end = end
    for offset in (1, 2):
        target_start = previous_end + dt.timedelta(days=1)
        target_end = target_start + dt.timedelta(days=cadence - 1)
        specs.append({
            "name": f"{parsed['prefix']}V{major}.{minor}.{patch + offset}",
            "startDate": target_start.isoformat(),
            "endDate": target_end.isoformat(),
        })
        previous_end = target_end
    return specs


def get_sprint(executable: str, project_id: str, identifier: str) -> dict[str, Any]:
    value = core.unwrap(core.run_devops(executable, [
        "projex-get-sprint", "--project-id", project_id, "--id", identifier,
    ]))
    if not isinstance(value, dict) or not sprint_id(value):
        raise core.AdapterError(f"迭代{identifier}无法官方回读。")
    if sprint_id(value) != identifier:
        raise core.AdapterError(
            f"迭代回读ID与请求不一致：请求={identifier}，返回={sprint_id(value)}。"
        )
    return value


def followup_target_snapshot(item: dict[str, Any] | None) -> dict[str, Any] | None:
    if not item:
        return None
    return {
        "id": sprint_id(item),
        "name": str(item.get("name") or ""),
        "endpoint": parse_versioned_sprint(item)["endpoint"],
        "startDate": sprint_day(item.get("startDate"), "目标迭代开始日期").isoformat(),
        "endDate": sprint_day(item.get("endDate"), "目标迭代结束日期").isoformat(),
        "status": str(item.get("status") or ""),
        "ownerIds": sprint_owner_ids(item),
    }


def build_followup_scope(executable: str, project_id: str, source_sprint_id: str,
                         idempotency_key: str) -> dict[str, Any]:
    project, project_name = verified_project(executable, project_id)
    source = get_sprint(executable, project_id, source_sprint_id)
    parsed = parse_versioned_sprint(source)
    if parsed["endpoint"] != "Web":
        raise core.AdapterError("产品验收后自动补建仅适用于Web迭代。")
    source_owner_ids = sprint_owner_ids(source)
    all_sprints = list_sprints(executable, project_id)
    targets: list[dict[str, Any]] = []
    for spec in build_followup_sprint_specs(source):
        matches = [row for row in all_sprints if str(row.get("name") or "") == spec["name"]]
        if len(matches) > 1:
            raise core.AdapterError(f"目标迭代同名多条，拒绝复用：{spec['name']}")
        existing = (
            get_sprint(executable, project_id, sprint_id(matches[0])) if matches else None
        )
        snapshot = followup_target_snapshot(existing)
        if snapshot and (
            snapshot["name"] != spec["name"]
            or snapshot["startDate"] != spec["startDate"]
            or snapshot["endDate"] != spec["endDate"]
            or snapshot["ownerIds"] != source_owner_ids
            or parse_versioned_sprint(existing)["endpoint"] != "Web"
        ):
            raise core.AdapterError(f"目标迭代名称、端别、日期或负责人漂移：{spec['name']}")
        targets.append({**spec, "existing": snapshot,
                        "result": "idempotent" if snapshot else "create"})
    return {
        "project": {"id": str(project.get("id") or project_id), "name": project_name},
        "source": {
            "id": sprint_id(source), "name": parsed["name"], "endpoint": "Web",
            "startDate": sprint_day(source.get("startDate"), "来源迭代开始日期").isoformat(),
            "endDate": sprint_day(source.get("endDate"), "来源迭代结束日期").isoformat(),
            "version": ".".join(str(value) for value in parsed["version"]),
            "ownerIds": source_owner_ids,
        },
        "targets": targets,
        "idempotencyKey": idempotency_key,
    }


def write_followup_preflight(executable: str, project_id: str, source_sprint_id: str,
                             idempotency_key: str, output: Path) -> dict[str, Any]:
    scope = build_followup_scope(executable, project_id, source_sprint_id, idempotency_key)
    value = {
        "schema": SCHEMA, "command": "preflight-followup-sprints",
        "createdAt": core.now_utc(), "liveScope": scope,
    }
    value["preflightHash"] = canonical_hash(value, {"preflightHash"})
    core.write_json(output, value)
    return value


def _validate_followup_apply_scope(planned: dict[str, Any], live: dict[str, Any]) -> None:
    for key in ("project", "source", "idempotencyKey"):
        if canonical_hash(planned.get(key)) != canonical_hash(live.get(key)):
            raise core.AdapterError(f"后续迭代预检后{key}发生变化，零写入。")
    planned_targets = planned.get("targets") or []
    live_targets = live.get("targets") or []
    if len(planned_targets) != 2 or len(live_targets) != 2:
        raise core.AdapterError("后续迭代冻结目标必须恰好两期。")
    for before, now in zip(planned_targets, live_targets):
        for key in ("name", "startDate", "endDate"):
            if before.get(key) != now.get(key):
                raise core.AdapterError("后续迭代目标在预检后发生变化，零写入。")
        before_existing = before.get("existing")
        now_existing = now.get("existing")
        if before_existing:
            stable_keys = ("id", "name", "endpoint", "startDate", "endDate", "ownerIds")
            if not now_existing or any(
                before_existing.get(key) != now_existing.get(key) for key in stable_keys
            ):
                raise core.AdapterError(f"已复用目标迭代在预检后漂移：{before.get('name')}")
        # 首次 apply 部分成功后，允许同一冻结目标从“不存在”变为精确匹配的已存在迭代。
        if not before_existing and now_existing:
            if any(now_existing.get(key) != before.get(key)
                   for key in ("name", "startDate", "endDate")):
                raise core.AdapterError(f"新出现的同名目标与冻结计划不一致：{before.get('name')}")


def apply_followup_preflight(executable: str, preflight: Path,
                             receipt_path: Path) -> dict[str, Any]:
    plan = json.loads(preflight.read_text(encoding="utf-8"))
    if (plan.get("schema") != SCHEMA
            or plan.get("command") != "preflight-followup-sprints"
            or plan.get("preflightHash") != canonical_hash(plan, {"preflightHash"})):
        raise core.AdapterError("后续迭代预检文件格式或哈希无效。")
    planned = plan.get("liveScope") or {}
    source = planned.get("source") or {}
    project = planned.get("project") or {}
    live = build_followup_scope(
        executable, str(project.get("id") or ""), str(source.get("id") or ""),
        str(planned.get("idempotencyKey") or ""),
    )
    _validate_followup_apply_scope(planned, live)
    results: list[dict[str, Any]] = []
    receipt = {
        "schema": SCHEMA, "command": "apply-followup-sprints",
        "createdAt": core.now_utc(), "preflightHash": plan["preflightHash"],
        "idempotencyKey": planned["idempotencyKey"], "project": live["project"],
        "source": live["source"], "targets": results, "complete": False,
    }

    def persist_partial() -> None:
        receipt["receiptHash"] = canonical_hash(receipt, {"receiptHash"})
        core.write_json(receipt_path, receipt)

    persist_partial()
    for target in live["targets"]:
        existing = target.get("existing")
        if existing:
            results.append({**existing, "result": "idempotent"})
            persist_partial()
            continue
        value = core.unwrap(core.run_devops(executable, [
            "projex-create-sprint", "--id", live["project"]["id"],
            "--name", target["name"], "--owners", ",".join(live["source"]["ownerIds"]),
            "--start-date", target["startDate"], "--end-date", target["endDate"],
            "--description", "产品整批验收关闭成功后自动补建的空Web迭代；不挂工作项。",
        ]))
        created_id = sprint_id(value) if isinstance(value, dict) else ""
        if not created_id:
            raise core.AdapterError(f"创建目标迭代后未取得ID：{target['name']}")
        created = followup_target_snapshot(
            get_sprint(executable, live["project"]["id"], created_id)
        )
        if (
            not created
            or created.get("id") != created_id
            or created.get("endpoint") != "Web"
            or created.get("ownerIds") != live["source"]["ownerIds"]
            or any(created.get(key) != target.get(key)
                   for key in ("name", "startDate", "endDate"))
        ):
            raise core.AdapterError(f"目标迭代创建后回读不一致：{target['name']}")
        results.append({**created, "result": "created"})
        persist_partial()
    receipt["complete"] = True
    persist_partial()
    return receipt


def cmd_preflight_followup(args: argparse.Namespace) -> int:
    executable = core.find_aliyun()
    core.require_auth_env()
    output = Path(args.output) if args.output else core.output_dir() / "pm-followup-sprints-preflight.json"
    plan = write_followup_preflight(
        executable, args.space_id, args.source_sprint_id, args.idempotency_key, output,
    )
    print(json.dumps({
        "ready": True, "preflightPath": str(output),
        "preflightHash": plan["preflightHash"], "scope": plan["liveScope"],
    }, ensure_ascii=False, indent=2))
    return 0


def cmd_apply_followup(args: argparse.Namespace) -> int:
    executable = core.find_aliyun()
    core.require_auth_env()
    receipt_path = Path(args.receipt) if args.receipt else core.output_dir() / "pm-followup-sprints-receipt.json"
    receipt = apply_followup_preflight(executable, Path(args.preflight), receipt_path)
    print(json.dumps({**receipt, "receiptPath": str(receipt_path)}, ensure_ascii=False, indent=2))
    return 0


def load_text(path: str) -> str:
    value = Path(path).read_text(encoding="utf-8").strip()
    if not value:
        raise core.AdapterError(f"文档为空：{path}")
    return value


def load_product_snapshot(path: str) -> dict[str, str]:
    source = Path(path).resolve()
    if not source.is_file():
        raise core.AdapterError("产品交棒快照文件不存在。")
    content = source.read_text(encoding="utf-8").strip()
    if len(content) < 240:
        raise core.AdapterError("产品交棒快照内容过短，不能作为产品修改后的版本印记。")
    missing = [name for name in PRODUCT_SNAPSHOT_SECTIONS if name not in content]
    if missing:
        raise core.AdapterError(f"产品交棒快照缺少必要章节：{'、'.join(missing)}。")
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    return {
        "path": str(source), "content": content, "sha256": digest,
        "snapshotId": f"ps-{digest[:16]}", "schema": PRODUCT_SNAPSHOT_SCHEMA,
    }


def managed_product_snapshot_description(
        current: str | None, format_type: str | None,
        snapshot: dict[str, str], requirement_serial: str,
        delivery_serial: str) -> tuple[str, str]:
    marker = (f"id={snapshot['snapshotId']} sha256={snapshot['sha256']}")
    metadata = (
        f"schema: {PRODUCT_SNAPSHOT_SCHEMA}\n"
        f"快照编号: {snapshot['snapshotId']}\n"
        f"需求: {requirement_serial}\n"
        f"交付: {delivery_serial}\n\n"
    )
    if str(format_type or "").upper() == "RICHTEXT":
        block = (
            "<h2>产品交棒快照</h2>"
            f"<!-- ONEOS_PRODUCT_HANDOFF_SNAPSHOT_START {marker} -->"
            f"<pre>{html.escape(metadata + snapshot['content'])}</pre>"
            "<!-- ONEOS_PRODUCT_HANDOFF_SNAPSHOT_END -->"
        )
        source = HTML_PRODUCT_SNAPSHOT_RE.sub("", current or "", count=1).rstrip()
        updated = f"{source}{block}" if source else block
        return updated, "RICHTEXT"
    block = (
        "## 产品交棒快照\n"
        f"<!-- ONEOS_PRODUCT_HANDOFF_SNAPSHOT_START {marker} -->\n"
        f"{metadata}{snapshot['content']}\n"
        "<!-- ONEOS_PRODUCT_HANDOFF_SNAPSHOT_END -->"
    )
    source = MARKDOWN_PRODUCT_SNAPSHOT_RE.sub("", current or "", count=1).rstrip()
    updated = f"{source}\n\n{block}" if source else block
    return updated.rstrip(), "MARKDOWN"


def build_scope(executable: str, args: argparse.Namespace) -> dict[str, Any]:
    project, project_name = verified_project(
        executable, args.space_id, args.project_name)
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
        "project": {"id": args.space_id, "name": project_name,
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


def require_unfrozen_initialization(scope: dict[str, Any]) -> None:
    for label in ("requirement", "delivery"):
        item = scope.get("existing", {}).get(label)
        if not item:
            continue
        if "ONEOS_DELIVERY_HANDOFF" in description_text(item) or \
                "ONEOS_PRODUCT_HANDOFF_SNAPSHOT" in description_text(item):
            raise core.AdapterError("已有冻结资料，禁止初始化覆盖；请使用刷新产品快照或正式交棒入口。")
        if label == "requirement" and status_name(item) not in REQUIREMENT_STATUS_ORDER[:-1]:
            raise core.AdapterError("需求已越过初始化阶段，禁止重跑 standard 覆盖或回退。")


def verify_initialization_scope(executable: str, scope: dict[str, Any]) -> None:
    current = {}
    for label in ("requirement", "delivery"):
        snapshot = scope["existing"].get(label)
        current[label] = get_workitem(executable, snapshot["id"]) if snapshot else None
        if snapshot and snapshot_item(current[label]) != snapshot:
            raise core.AdapterError("初始化预检后工作项正文或归属发生变化，零写入。")
    require_unfrozen_initialization({"existing": current})


def cmd_preflight(args: argparse.Namespace) -> int:
    executable = core.find_aliyun()
    core.require_auth_env()
    load_text(args.description_file)
    load_text(args.delivery_file)
    scope = build_scope(executable, args)
    verify_initialization_scope(executable, scope)
    value = {
        "schema": SCHEMA, "command": "preflight-standard", "createdAt": core.now_utc(),
        "input": {
            "spaceId": args.space_id, "projectName": scope["project"]["name"],
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
        "formal": False, "targetStatus": "设计完成",
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
    if plan.get("formal") is not False or plan.get("targetStatus") != "设计完成":
        raise core.AdapterError("旧 standard 预检不能授权正式交棒，请重新预检初始化范围。")
    verify_initialization_scope(executable, scope)

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
    req, advanced = advance_requirement(executable, req, "设计完成", req_status)
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
    if status_name(req) != "设计完成" or status_name(analysis) != "已完成" or status_name(design) != "已完成":
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
        "formal": False, "nextAction": "冻结并回读产品快照及全部端侧交棒清单，再 preflight-handoff / apply-handoff。",
    }
    receipt["receiptHash"] = canonical_hash(receipt, {"receiptHash"})
    output = Path(args.receipt) if args.receipt else core.output_dir() / "pm-standard-receipt.json"
    core.write_json(output, receipt)
    print(json.dumps({**receipt, "receiptPath": str(output)}, ensure_ascii=False, indent=2))
    return 0


def description_text(item: dict[str, Any]) -> str:
    return str(item.get("description") or "")


def item_project_id(item: dict[str, Any]) -> str:
    space = item.get("space") or {}
    return str(space.get("id") if isinstance(space, dict) and space.get("id") else item.get("spaceIdentifier") or item.get("spaceId") or "")


def snapshot_reverse(item: dict[str, Any]) -> dict[str, Any]:
    value = snapshot_item(item) or {}
    value["descriptionHash"] = hashlib.sha256(description_text(item).encode("utf-8")).hexdigest()
    return value


def require_relation(executable: str, source_id: str, target_id: str, relation_type: str, label: str) -> None:
    if target_id not in relation_ids(executable, source_id, relation_type):
        raise core.AdapterError(f"{label}正式关系缺失，拒绝执行。")


def resolve_workitem(executable: str, project_id: str, category: str,
                     identifier: str) -> dict[str, Any]:
    matches = [row for row in search_workitems(executable, project_id, category)
               if str(row.get("id") or "") == identifier or serial(row) == identifier]
    matches = [row for row in matches
               if str(row.get("logicalStatus") or "NORMAL").upper() == "NORMAL"]
    if len(matches) != 1:
        raise core.AdapterError(f"工作项{identifier}无法在项目中唯一解析。")
    return get_workitem(executable, str(matches[0]["id"]))


def build_product_snapshot_scope(executable: str, args: argparse.Namespace) -> dict[str, Any]:
    _, project_name = verified_project(
        executable, args.space_id, args.project_name)
    requirement = resolve_workitem(
        executable, args.space_id, "Req", args.requirement_id)
    delivery = resolve_workitem(
        executable, args.space_id, "Task", args.delivery_id)
    if not str(delivery.get("subject") or "").startswith("【交付】"):
        raise core.AdapterError("目标任务不是【交付】任务。")
    if status_name(requirement) in {"已完成", "已取消"}:
        raise core.AdapterError("已完成或已取消的需求不能刷新产品交棒快照。")
    if status_name(delivery) in {"已完成", "已取消"}:
        raise core.AdapterError("已完成或已取消的交付不能刷新产品交棒快照。")
    require_relation(executable, str(delivery["id"]), str(requirement["id"]),
                     "ASSOCIATED", "交付→需求")
    return {
        "project": {"id": args.space_id, "name": project_name},
        "requirement": snapshot_reverse(requirement),
        "delivery": snapshot_reverse(delivery),
    }


def cmd_preflight_product_snapshot(args: argparse.Namespace) -> int:
    executable = core.find_aliyun()
    core.require_auth_env()
    snapshot = load_product_snapshot(args.snapshot_file)
    scope = build_product_snapshot_scope(executable, args)
    manifest_path = getattr(args, "handoff_file", None)
    if not manifest_path:
        raise core.AdapterError("交棒清单缺失：正式刷新快照须提供 --handoff-file。旧文档可只读，不得冒充已冻结。")
    manifest = load_handoff_manifest(manifest_path, scope)
    value = {
        "schema": SCHEMA, "command": "preflight-product-snapshot",
        "createdAt": core.now_utc(),
        "input": {
            "spaceId": args.space_id, "projectName": scope["project"]["name"],
            "requirementId": args.requirement_id, "deliveryId": args.delivery_id,
            "snapshotFile": snapshot["path"],
            "handoffFile": str(Path(manifest_path).resolve()),
        },
        "productSnapshot": {
            "schema": snapshot["schema"], "snapshotId": snapshot["snapshotId"],
            "path": snapshot["path"], "sha256": snapshot["sha256"],
        },
        "liveScope": scope,
        "handoffManifest": manifest,
    }
    value["preflightHash"] = canonical_hash(value, {"preflightHash"})
    output = Path(args.output) if args.output else core.output_dir() / "pm-product-snapshot-preflight.json"
    core.write_json(output, value)
    print(json.dumps({
        "schema": SCHEMA, "ready": True, "preflightPath": str(output),
        "preflightHash": value["preflightHash"],
        "productSnapshot": value["productSnapshot"], "scope": scope,
    }, ensure_ascii=False, indent=2))
    return 0


def load_handoff_manifest(path: str, scope: dict[str, Any]) -> dict[str, Any]:
    try:
        manifest = json.loads(Path(path).read_text(encoding="utf-8-sig"))
        hg.validate_manifest(manifest, {
            "projectId": scope["project"]["id"],
            "requirementId": scope["requirement"]["id"],
            "deliveryId": scope["delivery"]["id"],
        })
        hg.verify_documents(manifest)
        return manifest
    except (ValueError, OSError) as error:
        raise core.AdapterError(f"交棒清单校验失败：{error}") from error


def cmd_apply_product_snapshot(args: argparse.Namespace) -> int:
    executable = core.find_aliyun()
    core.require_auth_env()
    plan = json.loads(Path(args.preflight).read_text(encoding="utf-8"))
    if plan.get("schema") != SCHEMA or plan.get("command") != "preflight-product-snapshot" \
            or plan.get("preflightHash") != canonical_hash(plan, {"preflightHash"}):
        raise core.AdapterError("产品快照预检文件格式或哈希无效。")
    source = plan["input"]
    params = argparse.Namespace(
        space_id=source["spaceId"], project_name=source["projectName"],
        requirement_id=source["requirementId"], delivery_id=source["deliveryId"],
    )
    snapshot = load_product_snapshot(source["snapshotFile"])
    if snapshot["sha256"] != plan.get("productSnapshot", {}).get("sha256"):
        raise core.AdapterError("产品交棒快照在预检后发生变化。")
    scope = build_product_snapshot_scope(executable, params)
    if canonical_hash(scope) != canonical_hash(plan.get("liveScope")):
        raise core.AdapterError("产品快照预检后需求、交付、状态、负责人、关系或描述发生变化。")
    if not source.get("handoffFile"):
        raise core.AdapterError("交棒预检来自旧版本，须重新生成带清单的预检。")
    manifest = load_handoff_manifest(source["handoffFile"], scope)
    if manifest != plan.get("handoffManifest"):
        raise core.AdapterError("交棒清单在预检后发生变化，零写入。")

    requirement = get_workitem(executable, scope["requirement"]["id"])
    delivery = get_workitem(executable, scope["delivery"]["id"])
    operations: list[dict[str, Any]] = []
    prepared_updates = []
    for label, item in (("requirement", requirement), ("delivery", delivery)):
        updated_description, format_type = managed_product_snapshot_description(
            description_text(item), item.get("formatType"), snapshot,
            serial(requirement), serial(delivery))
        try:
            updated_description = hg.upsert_manifest(updated_description, manifest)
        except ValueError as error:
            raise core.AdapterError(str(error)) from error
        prepared_updates.append((label, item, updated_description, format_type))
    # Parse both managed blocks before the first write; corruption in the second
    # object must not result in a preventable half-published product handoff.
    for label, item, updated_description, format_type in prepared_updates:
        if updated_description == description_text(item) and \
                str(item.get("formatType") or "MARKDOWN").upper() == format_type:
            operations.append({"operation": label, "result": "idempotent"})
            continue
        updated = update_item(executable, str(item["id"]), {
            "description": updated_description, "formatType": format_type,
        })
        operations.append({"operation": label, "result": "updated",
                           "serial": serial(updated)})

    after_requirement = get_workitem(executable, str(requirement["id"]))
    after_delivery = get_workitem(executable, str(delivery["id"]))
    snapshot_marker = f"sha256={snapshot['sha256']}"
    if snapshot_marker not in description_text(after_requirement) or \
            snapshot_marker not in description_text(after_delivery):
        raise core.AdapterError("产品交棒快照未在需求和交付中完整回读。")
    try:
        for item in (after_requirement, after_delivery):
            if hg.manifest_from_description(description_text(item), manifest["scope"]) != manifest:
                raise ValueError("正式交棒清单回读不一致")
    except ValueError as error:
        raise core.AdapterError(f"交棒清单未完整回读：{error}") from error
    if status_name(after_requirement) != scope["requirement"]["status"] or \
            owner_id(after_requirement) != scope["requirement"]["ownerId"] or \
            status_name(after_delivery) != scope["delivery"]["status"] or \
            owner_id(after_delivery) != scope["delivery"]["ownerId"]:
        raise core.AdapterError("刷新产品快照时意外改变了状态或负责人。")
    require_relation(executable, str(after_delivery["id"]),
                     str(after_requirement["id"]), "ASSOCIATED", "交付→需求")

    receipt = {
        "schema": SCHEMA, "command": "apply-product-snapshot",
        "createdAt": core.now_utc(), "preflightHash": plan["preflightHash"],
        "operations": operations,
        "productSnapshot": {
            "schema": snapshot["schema"], "snapshotId": snapshot["snapshotId"],
            "sha256": snapshot["sha256"],
        },
        "requirement": snapshot_reverse(after_requirement),
        "delivery": snapshot_reverse(after_delivery),
        "handoffManifest": manifest,
    }
    receipt["receiptHash"] = canonical_hash(receipt, {"receiptHash"})
    output = Path(args.receipt) if args.receipt else core.output_dir() / "pm-product-snapshot-receipt.json"
    core.write_json(output, receipt)
    print(json.dumps({**receipt, "receiptPath": str(output)}, ensure_ascii=False, indent=2))
    return 0


def build_formal_handoff_scope(executable: str, project_id: str, requirement_id: str,
                               manifests: list[dict[str, Any]]) -> dict[str, Any]:
    _, project_name = verified_project(executable, project_id, None)
    req = get_workitem(executable, requirement_id)
    if str(req.get("id") or "") != requirement_id or item_project_id(req) != project_id:
        raise core.AdapterError("正式交棒需求的项目/内部ID不一致。")
    if status_name(req) not in {"设计完成", "待开发"}:
        raise core.AdapterError("正式交棒仅允许设计完成→待开发；已开发或后续阶段换版请刷新快照。")
    if not isinstance(manifests, list) or not manifests:
        raise core.AdapterError("正式交棒缺冻结清单。")
    deliveries: dict[str, dict[str, Any]] = {}
    seen_scopes: set[str] = set()
    try:
        for manifest in manifests:
            hg.validate_manifest(manifest, {"projectId": project_id, "requirementId": requirement_id})
            scope = manifest["scope"]
            if scope["scopeId"] in seen_scopes:
                raise core.AdapterError("正式交棒存在重复 scopeId。")
            seen_scopes.add(scope["scopeId"])
            delivery_id = scope["deliveryId"]
            item = deliveries.get(delivery_id) or get_workitem(executable, delivery_id)
            if str(item.get("id") or "") != delivery_id or item_project_id(item) != project_id \
                    or not str(item.get("subject") or "").startswith("【交付】") \
                    or status_name(item) in {"已完成", "已取消"} or not owner_id(item):
                raise core.AdapterError("交付任务归属、类型、有效状态或负责人不满足正式交棒。")
            require_relation(executable, delivery_id, requirement_id, "ASSOCIATED", "交付→需求")
            for source in (req, item):
                if hg.manifest_from_description(description_text(source), scope) != manifest:
                    raise core.AdapterError("当前需求/交付冻结资料已变化或两边不一致。")
            hg.verify_documents(manifest)
            deliveries[delivery_id] = item
    except (ValueError, OSError) as error:
        raise core.AdapterError(f"正式交棒校验失败：{error}") from error
    # A requirement-wide state cannot be advanced using one ready endpoint only.
    linked_deliveries = set()
    # ASSOCIATED is written delivery -> requirement. Do not assume that the
    # requirement endpoint returns reverse edges: enumerate project deliveries
    # with the existing paginated official search and check outgoing relations.
    for candidate in search_workitems(executable, project_id, "Task"):
        if not str(candidate.get("subject") or "").startswith("【交付】") or \
                str(candidate.get("logicalStatus") or "NORMAL").upper() != "NORMAL":
            continue
        item_id = str(candidate["id"])
        if requirement_id not in relation_ids(executable, item_id, "ASSOCIATED"):
            continue
        item = deliveries.get(item_id) or get_workitem(executable, item_id)
        if status_name(item) not in {"已完成", "已取消"} and \
                str(item.get("logicalStatus") or "NORMAL").upper() == "NORMAL":
            linked_deliveries.add(item_id)
    if linked_deliveries != set(deliveries):
        raise core.AdapterError("正式推进需求必须覆盖全部当前关联的端侧交付；不能以单端清单放行整条需求。")
    req_type = exact_type(executable, project_id, "Req", "产品类需求")
    target = status_ids(executable, project_id, str(req_type["id"]), ["待开发"])["待开发"]
    return {"project": {"id": project_id, "name": project_name},
            "requirement": snapshot_reverse(req),
            "deliveries": [snapshot_reverse(deliveries[key]) for key in sorted(deliveries)],
            "targetStatusId": target}


def cmd_preflight_handoff(args: argparse.Namespace) -> int:
    executable = core.find_aliyun(); core.require_auth_env()
    manifests = [json.loads(Path(path).read_text(encoding="utf-8-sig")) for path in args.handoff_file]
    scope = build_formal_handoff_scope(executable, args.space_id, args.requirement_id, manifests)
    plan = {"schema": SCHEMA, "command": "preflight-handoff", "createdAt": core.now_utc(),
            "input": {"spaceId": args.space_id, "requirementId": args.requirement_id},
            "manifests": manifests, "liveScope": scope,
            "boundary": "经确认仅推进需求待开发；不改正文、交付负责人、不建开发或测试任务。"}
    plan["preflightHash"] = canonical_hash(plan, {"preflightHash"})
    output = Path(args.output) if args.output else core.output_dir() / "pm-handoff-preflight.json"
    core.write_json(output, plan)
    print(json.dumps({"ready": True, "preflightPath": str(output), "scope": scope}, ensure_ascii=False))
    return 0


def cmd_apply_handoff(args: argparse.Namespace) -> int:
    executable = core.find_aliyun(); core.require_auth_env()
    plan = json.loads(Path(args.preflight).read_text(encoding="utf-8"))
    if plan.get("schema") != SCHEMA or plan.get("command") != "preflight-handoff" \
            or plan.get("preflightHash") != canonical_hash(plan, {"preflightHash"}):
        raise core.AdapterError("正式交棒预检格式或哈希无效。")
    source = plan["input"]
    scope = build_formal_handoff_scope(executable, source["spaceId"], source["requirementId"], plan["manifests"])
    if scope != plan.get("liveScope"):
        raise core.AdapterError("交棒预检后状态、负责人、关系或正文变化，零写入。")
    result = "idempotent"
    if scope["requirement"]["status"] == "设计完成":
        update_item(executable, source["requirementId"], {"status": scope["targetStatusId"]})
        result = "updated"
    # Always re-read raw documents, owners and links; never infer success from PATCH.
    try:
        after = build_formal_handoff_scope(executable, source["spaceId"], source["requirementId"], plan["manifests"])
    except (core.AdapterError, ValueError, OSError) as error:
        raise core.AdapterError(f"正式交棒回读失败，状态可能已写入，未确认完成；先只读核对后重新预检：{error}") from error
    expected_requirement = {**scope["requirement"], "status": "待开发"}
    expected_requirement["gmtModified"] = after["requirement"].get("gmtModified")
    if after["requirement"] != expected_requirement or after["deliveries"] != scope["deliveries"]:
        raise core.AdapterError("正式交棒最终回读不一致；状态可能已写入，未确认完成，须只读核对后重新预检续跑。")
    receipt = {"schema": SCHEMA, "command": "apply-handoff", "createdAt": core.now_utc(),
               "formal": True, "result": result, "preflightHash": plan["preflightHash"],
               "scope": after, "manifestHashes": [m["sha256"] for m in plan["manifests"]]}
    output = Path(args.receipt) if args.receipt else core.output_dir() / "pm-handoff-receipt.json"
    core.write_json(output, receipt)
    print(json.dumps({**receipt, "receiptPath": str(output)}, ensure_ascii=False))
    return 0


def cancellation_marker(key: str) -> str:
    return f"oneos.pm.cancellation/{key}"


def reverse_statuses(executable: str, project_id: str) -> tuple[dict[str, str], dict[str, str]]:
    req_type = exact_type(executable, project_id, "Req", "产品类需求")
    task_type = exact_type(executable, project_id, "Task", "任务")
    return (status_ids(executable, project_id, str(req_type["id"]), ["测试完成", "已取消", "待开发", "设计中"]),
            status_ids(executable, project_id, str(task_type["id"]), ["待处理", "处理中", "已取消"]))


def build_cancel_scope(executable: str, args: argparse.Namespace) -> dict[str, Any]:
    _, project_name = verified_project(
        executable, args.space_id, args.project_name)
    req, delivery, execution = (get_workitem(executable, value) for value in
                                (args.requirement_id, args.delivery_id, args.execution_id))
    protected = [get_workitem(executable, value) for value in args.protected_id]
    if args.test_task_id:
        protected.append(get_workitem(executable, args.test_task_id))
    all_items = [req, delivery, execution, *protected]
    if {item_project_id(item) for item in all_items} != {args.space_id}:
        raise core.AdapterError("取消范围存在跨项目工作项。")
    require_relation(executable, str(delivery["id"]), str(req["id"]), "ASSOCIATED", "交付→需求")
    require_relation(executable, str(execution["id"]), str(req["id"]), "ASSOCIATED", "执行批次→需求")
    require_relation(executable, str(execution["id"]), str(delivery["id"]), "ASSOCIATED", "执行批次→交付")
    if args.test_task_id:
        require_relation(executable, str(execution["id"]), str(args.test_task_id), "ASSOCIATED", "执行批次→测试")
    if "oneos.release-production/v1" in description_text(execution) and "isRealProduction=false" not in description_text(execution):
        raise core.AdapterError("执行批次存在真实生产证据；必须先由发布Skill完成受控回滚。")
    marker = cancellation_marker(args.idempotency_key)
    for label, item, active in (("需求", req, "测试完成"), ("交付", delivery, "处理中"), ("执行批次", execution, "待处理")):
        if status_name(item) not in {active, "已取消"}:
            raise core.AdapterError(f"{label}当前状态为{status_name(item)}，预期为{active}或已取消。")
        if status_name(item) == "已取消" and marker not in description_text(item):
            raise core.AdapterError(f"{label}已由其他流程取消，拒绝接管。")
    req_statuses, task_statuses = reverse_statuses(executable, args.space_id)
    return {"project": {"id": args.space_id, "name": project_name}, "marker": marker,
            "reason": args.reason, "requirement": snapshot_reverse(req), "delivery": snapshot_reverse(delivery),
            "execution": snapshot_reverse(execution), "protected": [snapshot_reverse(item) for item in protected],
            "statusIds": {"requirement": req_statuses, "task": task_statuses},
            "boundaries": {"isRealProduction": False, "notPerformed": ["删除代码分支", "停止或删除已完成测试流水线", "修改已完成开发任务", "修改已完成测试任务", "修改已关闭缺陷"]}}


def cmd_preflight_cancel(args: argparse.Namespace) -> int:
    executable = core.find_aliyun(); core.require_auth_env()
    scope = build_cancel_scope(executable, args)
    value = {"schema": SCHEMA, "command": "preflight-cancel-downstream", "createdAt": core.now_utc(),
             "input": {"spaceId": args.space_id, "projectName": scope["project"]["name"], "requirementId": args.requirement_id,
                       "deliveryId": args.delivery_id, "executionId": args.execution_id, "testTaskId": args.test_task_id,
                       "protectedIds": args.protected_id, "reason": args.reason, "idempotencyKey": args.idempotency_key},
             "liveScope": scope}
    value["preflightHash"] = canonical_hash(value, {"preflightHash"})
    output = Path(args.output) if args.output else core.output_dir() / "pm-cancel-preflight.json"
    core.write_json(output, value); print(json.dumps({"ready": True, "preflightPath": str(output), "preflightHash": value["preflightHash"]}, ensure_ascii=False)); return 0


def cmd_apply_cancel(args: argparse.Namespace) -> int:
    executable = core.find_aliyun(); core.require_auth_env()
    plan = json.loads(Path(args.preflight).read_text(encoding="utf-8"))
    if plan.get("schema") != SCHEMA or plan.get("command") != "preflight-cancel-downstream" or plan.get("preflightHash") != canonical_hash(plan, {"preflightHash"}):
        raise core.AdapterError("取消预检文件格式或哈希无效。")
    source = plan["input"]
    params = argparse.Namespace(space_id=source["spaceId"], project_name=source["projectName"], requirement_id=source["requirementId"], delivery_id=source["deliveryId"], execution_id=source["executionId"], test_task_id=source.get("testTaskId"), protected_id=source.get("protectedIds") or [], reason=source["reason"], idempotency_key=source["idempotencyKey"])
    scope = build_cancel_scope(executable, params)
    if canonical_hash(scope) != canonical_hash(plan.get("liveScope")):
        raise core.AdapterError("取消预检后对象、状态、关系或生产边界发生变化，零写入。")
    block = f"\n\n## 取消留痕（生命周期逆向冒烟）\n- 取消原因：{scope['reason']}\n- 生产边界：isRealProduction=false；未触发真实生产流水线或回滚。\n- 保留证据：开发、测试、缺陷、MR、测试流水线及工作项编号均不删除、不回写。\n<!-- {scope['marker']} -->"
    targets = (("requirement", params.requirement_id, scope["statusIds"]["requirement"]["已取消"]), ("delivery", params.delivery_id, scope["statusIds"]["task"]["已取消"]), ("execution", params.execution_id, scope["statusIds"]["task"]["已取消"]))
    operations = []
    for label, item_id, status_id in targets:
        item = get_workitem(executable, item_id)
        if status_name(item) == "已取消":
            operations.append({"target": label, "result": "idempotent"}); continue
        updated = update_item(executable, item_id, {"status": status_id, "description": description_text(item).rstrip() + block, "formatType": item.get("formatType") or "MARKDOWN"})
        if status_name(updated) != "已取消" or scope["marker"] not in description_text(updated):
            raise core.AdapterError(f"{label}取消后状态或留痕回读不一致。")
        operations.append({"target": label, "result": "cancelled", "after": snapshot_reverse(updated)})
    protected = [snapshot_reverse(get_workitem(executable, item["id"])) for item in scope["protected"]]
    if protected != scope["protected"]:
        raise core.AdapterError("已完成对象发生漂移；停止并保留真实状态。")
    receipt = {"schema": SCHEMA, "command": "apply-cancel-downstream", "createdAt": core.now_utc(), "preflightHash": plan["preflightHash"], "operations": operations, "protected": protected, "boundaries": scope["boundaries"]}
    receipt["receiptHash"] = canonical_hash(receipt, {"receiptHash"})
    output = Path(args.receipt) if args.receipt else core.output_dir() / "pm-cancel-receipt.json"
    core.write_json(output, receipt); print(json.dumps({**receipt, "receiptPath": str(output)}, ensure_ascii=False)); return 0


def planned_start(item: dict[str, Any]) -> str:
    for field in item.get("customFieldValues") or []:
        if isinstance(field, dict) and str(field.get("fieldId") or "") == "79":
            values = field.get("values") or []
            if values and isinstance(values[0], dict):
                return str(values[0].get("identifier") or values[0].get("displayValue") or "")
    return ""


def requirement_priority_and_label(item: dict[str, Any]) -> tuple[str, str]:
    priority = next((str((field.get("values") or [{}])[0].get("identifier") or "") for field in item.get("customFieldValues") or [] if isinstance(field, dict) and str(field.get("fieldId") or "") == "priority"), "")
    labels = {str(value.get("id")) for value in item.get("labels") or [] if isinstance(value, dict) and value.get("id")}
    if not priority or len(labels) != 1:
        raise core.AdapterError("需求优先级或标签无法唯一回读，拒绝创建返工设计任务。")
    return priority, next(iter(labels))


def rollback_marker(key: str) -> str:
    return f"oneos.pm.design-rollback/{key}"


def build_rollback_scope(executable: str, args: argparse.Namespace) -> dict[str, Any]:
    _, project_name = verified_project(
        executable, args.space_id, args.project_name)
    req, delivery, old_design = (get_workitem(executable, value) for value in (args.requirement_id, args.delivery_id, args.old_design_id))
    if {item_project_id(item) for item in (req, delivery, old_design)} != {args.space_id}:
        raise core.AdapterError("设计回退范围存在跨项目工作项。")
    require_relation(executable, str(delivery["id"]), str(req["id"]), "ASSOCIATED", "交付→需求")
    require_relation(executable, str(old_design["id"]), str(delivery["id"]), "PARENT", "原设计→交付")
    marker = rollback_marker(args.idempotency_key)
    if status_name(old_design) != "已完成" or status_name(req) not in {"待开发", "设计中"}:
        raise core.AdapterError("只有已完成的原设计和待开发/设计中的需求可执行返工回退。")
    old_serial = serial(old_design)
    occurrence = re.findall(r"(?m)^- 设计：([^\s]+)\s*$", description_text(req))
    if occurrence != [old_serial] and marker not in description_text(req):
        raise core.AdapterError("需求中的设计编号区块与原设计不一致。")
    matches = managed_matches(executable, args.space_id, "Task", marker, "【设计】")
    if len(matches) > 1:
        raise core.AdapterError("同一回退幂等键对应多条新设计任务。")
    new_design = matches[0] if matches else None
    if new_design:
        require_relation(executable, str(new_design["id"]), str(delivery["id"]), "PARENT", "新设计→交付")
        if status_name(new_design) != "待处理":
            raise core.AdapterError("已存在的新设计不在待处理，拒绝接续。")
    req_statuses, _ = reverse_statuses(executable, args.space_id)
    priority, label = requirement_priority_and_label(req)
    return {"project": {"id": args.space_id, "name": project_name}, "marker": marker, "reason": args.reason,
            "requirement": snapshot_reverse(req), "delivery": {**snapshot_reverse(delivery), "plannedStart": planned_start(delivery)},
            "oldDesign": snapshot_reverse(old_design), "newDesign": snapshot_reverse(new_design) if new_design else None,
            "requirementStatuses": req_statuses, "creation": {"owner": owner_id(old_design), "priority": priority, "label": label, "oldSerial": old_serial,
            "taskTypeId": str(exact_type(executable, args.space_id, "Task", "任务")["id"])}}


def cmd_preflight_rollback(args: argparse.Namespace) -> int:
    executable = core.find_aliyun(); core.require_auth_env(); scope = build_rollback_scope(executable, args)
    value = {"schema": SCHEMA, "command": "preflight-rollback-to-design", "createdAt": core.now_utc(), "input": {"spaceId": args.space_id, "projectName": scope["project"]["name"], "requirementId": args.requirement_id, "deliveryId": args.delivery_id, "oldDesignId": args.old_design_id, "reason": args.reason, "idempotencyKey": args.idempotency_key}, "liveScope": scope}
    value["preflightHash"] = canonical_hash(value, {"preflightHash"})
    output = Path(args.output) if args.output else core.output_dir() / "pm-design-rollback-preflight.json"
    core.write_json(output, value); print(json.dumps({"ready": True, "preflightPath": str(output), "preflightHash": value["preflightHash"]}, ensure_ascii=False)); return 0


def cmd_apply_rollback(args: argparse.Namespace) -> int:
    executable = core.find_aliyun(); core.require_auth_env(); plan = json.loads(Path(args.preflight).read_text(encoding="utf-8"))
    if plan.get("schema") != SCHEMA or plan.get("command") != "preflight-rollback-to-design" or plan.get("preflightHash") != canonical_hash(plan, {"preflightHash"}):
        raise core.AdapterError("设计回退预检文件格式或哈希无效。")
    source = plan["input"]; params = argparse.Namespace(space_id=source["spaceId"], project_name=source["projectName"], requirement_id=source["requirementId"], delivery_id=source["deliveryId"], old_design_id=source["oldDesignId"], reason=source["reason"], idempotency_key=source["idempotencyKey"])
    scope = build_rollback_scope(executable, params)
    if canonical_hash(scope) != canonical_hash(plan.get("liveScope")):
        raise core.AdapterError("设计回退预检后对象、状态、关系、计划开始或编号发生变化，零写入。")
    new_design = get_workitem(executable, scope["newDesign"]["id"]) if scope["newDesign"] else None
    if not new_design:
        new_design = create_item(executable, owner=scope["creation"]["owner"], project=params.space_id, subject=f"【设计】返工-{serial(get_workitem(executable, params.requirement_id))}", type_id=scope["creation"]["taskTypeId"], description=f"## 回退重做设计\n- 原设计：{scope['creation']['oldSerial']}（保持已完成）\n- 回退原因：{params.reason}\n<!-- {scope['marker']} -->", priority=scope["creation"]["priority"], label=scope["creation"]["label"], parent_id=params.delivery_id)
    req = get_workitem(executable, params.requirement_id)
    if status_name(req) == "待开发":
        matches = list(re.finditer(r"(?m)^- 设计：([^\s]+)\s*$", description_text(req)))
        if len(matches) != 1:
            raise core.AdapterError("需求中的设计编号区块无法唯一确认。")
        updated = description_text(req)[:matches[0].start(1)] + serial(new_design) + description_text(req)[matches[0].end(1):]
        req = update_item(executable, params.requirement_id, {"status": scope["requirementStatuses"]["设计中"], "description": updated.rstrip() + f"\n\n## 变更纪要（回退重做）\n- 原设计：{scope['creation']['oldSerial']}（保持已完成）\n- 新设计：{serial(new_design)}（承接返工）\n- 原因：{params.reason}\n- 交付计划开始时间保持首次开工记录。\n<!-- {scope['marker']} -->", "formatType": req.get("formatType") or "MARKDOWN"})
    delivery = get_workitem(executable, params.delivery_id); old_design = get_workitem(executable, params.old_design_id)
    if status_name(req) != "设计中" or scope["marker"] not in description_text(req) or planned_start(delivery) != scope["delivery"]["plannedStart"] or status_name(old_design) != "已完成":
        raise core.AdapterError("设计回退后的状态、留痕或计划开始回读不一致。")
    receipt = {"schema": SCHEMA, "command": "apply-rollback-to-design", "createdAt": core.now_utc(), "preflightHash": plan["preflightHash"], "requirement": snapshot_reverse(req), "delivery": {**snapshot_reverse(delivery), "plannedStart": planned_start(delivery)}, "oldDesign": snapshot_reverse(old_design), "newDesign": snapshot_reverse(new_design)}
    receipt["receiptHash"] = canonical_hash(receipt, {"receiptHash"}); output = Path(args.receipt) if args.receipt else core.output_dir() / "pm-design-rollback-receipt.json"; core.write_json(output, receipt); print(json.dumps({**receipt, "receiptPath": str(output)}, ensure_ascii=False)); return 0


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    sub = root.add_subparsers(dest="command", required=True)
    doctor = sub.add_parser("doctor")
    doctor.set_defaults(handler=cmd_doctor)
    preflight = sub.add_parser("preflight-standard")
    for name, required in (("space-id", True), ("project-name", False), ("subject", True),
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
    followup_preflight = sub.add_parser("preflight-followup-sprints")
    followup_preflight.add_argument("--space-id", required=True)
    followup_preflight.add_argument("--source-sprint-id", required=True)
    followup_preflight.add_argument("--idempotency-key", required=True)
    followup_preflight.add_argument("--output")
    followup_preflight.set_defaults(handler=cmd_preflight_followup)
    followup_apply = sub.add_parser("apply-followup-sprints")
    followup_apply.add_argument("--preflight", required=True)
    followup_apply.add_argument("--receipt")
    followup_apply.set_defaults(handler=cmd_apply_followup)
    snapshot_preflight = sub.add_parser("preflight-product-snapshot")
    for name in ("space-id", "requirement-id", "delivery-id", "snapshot-file"):
        snapshot_preflight.add_argument(f"--{name}", required=True)
    snapshot_preflight.add_argument("--project-name")
    snapshot_preflight.add_argument("--handoff-file", help="冻结交棒清单 JSON；正式刷新时必需")
    snapshot_preflight.add_argument("--output")
    snapshot_preflight.set_defaults(handler=cmd_preflight_product_snapshot)
    snapshot_apply = sub.add_parser("apply-product-snapshot")
    snapshot_apply.add_argument("--preflight", required=True)
    snapshot_apply.add_argument("--receipt")
    snapshot_apply.set_defaults(handler=cmd_apply_product_snapshot)
    handoff_preflight = sub.add_parser("preflight-handoff")
    handoff_preflight.add_argument("--space-id", required=True)
    handoff_preflight.add_argument("--requirement-id", required=True, help="需求官方内部ID")
    handoff_preflight.add_argument("--handoff-file", required=True, action="append",
                                   help="每个 scope 一份；重复指定，覆盖全部当前端侧交付")
    handoff_preflight.add_argument("--output")
    handoff_preflight.set_defaults(handler=cmd_preflight_handoff)
    handoff_apply = sub.add_parser("apply-handoff")
    handoff_apply.add_argument("--preflight", required=True)
    handoff_apply.add_argument("--receipt")
    handoff_apply.set_defaults(handler=cmd_apply_handoff)
    cancel_preflight = sub.add_parser("preflight-cancel-downstream")
    for name in ("space-id", "requirement-id", "delivery-id", "execution-id", "reason", "idempotency-key"):
        cancel_preflight.add_argument(f"--{name}", required=True)
    cancel_preflight.add_argument("--project-name")
    cancel_preflight.add_argument("--test-task-id")
    cancel_preflight.add_argument("--protected-id", action="append", default=[])
    cancel_preflight.add_argument("--output")
    cancel_preflight.set_defaults(handler=cmd_preflight_cancel)
    cancel_apply = sub.add_parser("apply-cancel-downstream")
    cancel_apply.add_argument("--preflight", required=True)
    cancel_apply.add_argument("--receipt")
    cancel_apply.set_defaults(handler=cmd_apply_cancel)
    rollback_preflight = sub.add_parser("preflight-rollback-to-design")
    for name in ("space-id", "requirement-id", "delivery-id", "old-design-id", "reason", "idempotency-key"):
        rollback_preflight.add_argument(f"--{name}", required=True)
    rollback_preflight.add_argument("--project-name")
    rollback_preflight.add_argument("--output")
    rollback_preflight.set_defaults(handler=cmd_preflight_rollback)
    rollback_apply = sub.add_parser("apply-rollback-to-design")
    rollback_apply.add_argument("--preflight", required=True)
    rollback_apply.add_argument("--receipt")
    rollback_apply.set_defaults(handler=cmd_apply_rollback)
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
