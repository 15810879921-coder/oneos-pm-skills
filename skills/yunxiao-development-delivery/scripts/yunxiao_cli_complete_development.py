#!/usr/bin/env python3
"""Execute the guarded Yunxiao closure and mandatory QA handoff for one development task."""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import re
import sys
from pathlib import Path
from typing import Any

import yunxiao_cli_gateway as gateway
import yunxiao_cli_runtime as core
import handoff_gate as hg
import yunxiao_cli_handoff as handoff_start


SCHEMA = "oneos.complete-development-plan/v1"
PREFLIGHT_SCHEMA = "oneos.complete-development-preflight/v1"
RECEIPT_SCHEMA = "oneos.complete-development-receipt/v1"
SUITE_VERSION = "10.2.14"
TEST_SCOPE_START = "<!-- ONEOS_TEST_SCOPE_START -->"
TEST_SCOPE_END = "<!-- ONEOS_TEST_SCOPE_END -->"
ALLOWED_TEST_MODES = {"formal-plan", "mandatory-test-task"}
TEST_DELIVERY_MODES = {"execute", "merge_only"}
STAGE_ORDER = (
    "effort", "testHandoff", "developmentComplete",
    "requirementDevelopmentComplete", "requirementHandoff",
)
CRITICAL_STAGES = {"testHandoff", "developmentComplete"}
STAGE_TOKEN_RE = re.compile(r"^\$\{stage\.([A-Za-z0-9_-]+)\.action\.(\d+)\.([A-Za-z0-9_.-]+)\}$")
STAGE_WRITE_OPERATIONS = {
    "effort": {"projex-create-effort-record", "projex-update-effort-record"},
    "testHandoff": {
        "projex-create-workitem", "projex-update-workitem",
        "projex-create-workitem-relation-record",
        "projex-create-workitem-ext-relation-record",
    },
    "developmentComplete": {"projex-update-workitem"},
    "requirementDevelopmentComplete": {"projex-update-workitem"},
    "requirementHandoff": {"projex-update-workitem"},
}


def load_object(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise core.AdapterError(f"{path}必须是JSON对象。")
    return value


def valid_ref(value: object) -> bool:
    text = str(value or "").strip()
    return bool(text) and text.lower() not in {"none", "null", "n/a", "无", "..."} \
        and "<" not in text and ">" not in text


def _arg_value(args: list[str], name: str) -> str | None:
    try:
        index = args.index(name)
    except ValueError:
        return None
    return args[index + 1] if index + 1 < len(args) else None


def _serialized(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _managed_scope(description: str) -> dict[str, Any]:
    start = description.find(TEST_SCOPE_START)
    end = description.find(TEST_SCOPE_END)
    if start < 0 or end <= start:
        raise core.AdapterError("测试任务描述缺少受管测试范围区块。")
    body = description[start + len(TEST_SCOPE_START):end].strip()
    match = re.fullmatch(r"<!--\s*(\{.*\})\s*-->", body, flags=re.DOTALL)
    if not match:
        raise core.AdapterError("受管测试范围必须使用oneos.test-scope/v1单行JSON。")
    try:
        value = json.loads(match.group(1))
    except json.JSONDecodeError as error:
        raise core.AdapterError("受管测试范围JSON无效。") from error
    if not isinstance(value, dict) or value.get("schemaVersion") != "oneos.test-scope/v1":
        raise core.AdapterError("受管测试范围schemaVersion必须为oneos.test-scope/v1。")
    return value


def _status_updates(plan: dict[str, Any]) -> list[tuple[str, str | None]]:
    result: list[tuple[str, str | None]] = []
    for action in plan["actions"]:
        if gateway._status_value(action) is None:
            continue
        target = _arg_value(action.get("args") or [], "--id") or ""
        result.append((target, gateway._expected_status(plan, target)))
    return result


def _require_status_readback(calls: list[dict[str, Any]], workitem_id: str,
                             expected_status: str, label: str) -> None:
    for call in calls:
        if call["operation"] != "projex-get-workitem":
            continue
        if _arg_value(call["args"], "--id") != workitem_id:
            continue
        if (call.get("expect") or {}).get("status.displayName") == expected_status:
            return
    raise core.AdapterError(f"finalReadbacks缺少{label}={expected_status}的官方回读。")


def _require_test_readbacks(calls: list[dict[str, Any]], scope: dict[str, Any]) -> None:
    test_ref = str(scope["testTaskRef"])
    test_get = [
        call for call in calls
        if call["operation"] == "projex-get-workitem"
        and _arg_value(call["args"], "--id") == test_ref
    ]
    if len(test_get) != 1:
        raise core.AdapterError("finalReadbacks必须精确回读一个测试任务。")
    expect = test_get[0].get("expect") or {}
    if str(expect.get("assignedTo.id") or "") != str(scope["testSupervisorId"]):
        raise core.AdapterError("测试任务回读必须校验负责人等于唯一测试主管。")
    if expect.get("status.displayName") not in {"待处理", "处理中", "已完成"}:
        raise core.AdapterError("测试任务回读必须校验真实测试状态。")
    managed = _managed_scope(str(expect.get("description") or ""))
    expected_fields = {
        "developmentTaskId": str(scope["developmentTaskId"]),
        "requirementId": str(scope["requirementId"]),
        "deliveryId": str(scope["deliveryId"]),
        "testMode": str(scope["testMode"]),
        "scopeId": str(scope["scopeId"]),
        "deliveryEnd": str(scope["deliveryEnd"]),
        "testPlanId": scope["testPlanId"],
        "directoryIds": scope["directoryIds"],
        "selectedCaseIds": scope["selectedCaseIds"],
    }
    for field, expected in expected_fields.items():
        if managed.get(field) != expected:
            raise core.AdapterError(f"测试任务描述回读的{field}与完成开发范围不一致。")

    relation_expectations = {
        "PARENT": str(scope["deliveryId"]),
        "ASSOCIATED": str(scope["requirementId"]),
    }
    for relation_type, expected_id in relation_expectations.items():
        matching = [
            call for call in calls
            if call["operation"] == "projex-list-workitem-relation-records"
            and _arg_value(call["args"], "--id") == test_ref
            and _arg_value(call["args"], "--relation-type") == relation_type
            and expected_id in _serialized(call.get("expect") or {})
        ]
        if len(matching) != 1:
            raise core.AdapterError(
                f"finalReadbacks必须精确校验测试任务{relation_type}关系到{expected_id}。"
            )


def _stage_test_ref(test_ref: str) -> str:
    match = STAGE_TOKEN_RE.fullmatch(test_ref)
    if not match:
        return test_ref
    stage_name, index, path = match.groups()
    if stage_name != "testHandoff":
        raise core.AdapterError("新测试任务只能引用testHandoff阶段的动作回执。")
    return f"${{action.{index}.{path}}}"


def _require_stage_operations(name: str, stage: dict[str, Any]) -> None:
    allowed = STAGE_WRITE_OPERATIONS[name]
    unexpected = sorted({item["operation"] for item in stage["actions"]} - allowed)
    if unexpected:
        raise core.AdapterError(f"{name}阶段包含越权写操作：{unexpected}")
    if name in {
        "developmentComplete", "requirementDevelopmentComplete", "requirementHandoff",
    } and len(stage["actions"]) != 1:
        raise core.AdapterError(f"{name}阶段必须且只能包含一个状态写动作。")


def validate_plan(value: dict[str, Any]) -> dict[str, Any]:
    gateway.assert_no_secrets(value)
    if value.get("schemaVersion") != SCHEMA:
        raise core.AdapterError(f"计划schemaVersion必须为{SCHEMA}。")
    if value.get("suiteVersion") != SUITE_VERSION:
        raise core.AdapterError(f"计划suiteVersion必须为{SUITE_VERSION}。")
    idempotency_key = str(value.get("idempotencyKey") or "").strip()
    if not idempotency_key:
        raise core.AdapterError("完成开发计划缺少稳定idempotencyKey。")

    requested_delivery = str(value.get("testDeliveryMode") or "merge_only")
    if requested_delivery not in TEST_DELIVERY_MODES:
        raise core.AdapterError("testDeliveryMode必须为execute或merge_only；询问应在生成计划前完成。")
    scope = value.get("scope")
    if not isinstance(scope, dict):
        raise core.AdapterError("scope必须是对象。")
    required_scope = (
        "projectId", "developmentTaskId", "requirementId", "deliveryId",
        "developmentTaskSerial", "requirementSerial",
        "testTaskRef", "testSupervisorId", "testMode", "requirementTargetStatus",
        "scopeId", "deliveryEnd",
    )
    for field in required_scope:
        if not valid_ref(scope.get(field)):
            raise core.AdapterError(f"scope.{field}缺少有效值。")
    for field in ("testPlanId", "directoryIds", "selectedCaseIds"):
        if field not in scope:
            raise core.AdapterError(f"scope.{field}必须显式声明。")
    if scope["testPlanId"] is not None and not valid_ref(scope["testPlanId"]):
        raise core.AdapterError("scope.testPlanId必须为有效ID或null。")
    if not isinstance(scope["directoryIds"], list) or not isinstance(scope["selectedCaseIds"], list):
        raise core.AdapterError("scope.directoryIds和scope.selectedCaseIds必须是数组。")
    if any(not valid_ref(item) for item in scope["directoryIds"] + scope["selectedCaseIds"]):
        raise core.AdapterError("测试目录和用例ID不得包含空值。")
    if len(scope["directoryIds"]) != len(set(map(str, scope["directoryIds"]))) \
            or len(scope["selectedCaseIds"]) != len(set(map(str, scope["selectedCaseIds"]))):
        raise core.AdapterError("测试目录和用例ID必须去重。")
    if scope["testMode"] not in ALLOWED_TEST_MODES:
        raise core.AdapterError("testMode只允许formal-plan或mandatory-test-task。")
    if scope["deliveryEnd"] not in {"Web", "小程序", "跨端"}:
        raise core.AdapterError("deliveryEnd只允许Web、小程序或跨端。")
    if scope["requirementTargetStatus"] not in {"待测试", "测试中"}:
        raise core.AdapterError("完成开发不得把需求推进到测试完成或其他阶段。")
    matching = scope.get("matchingTestTaskIds")
    if not isinstance(matching, list) or len(matching) > 1:
        raise core.AdapterError("预检必须声明零个或一个精确匹配的测试任务。")
    if matching and str(scope["testTaskRef"]) != str(matching[0]):
        raise core.AdapterError("复用测试任务时testTaskRef必须等于唯一匹配任务ID。")
    if not matching:
        match = STAGE_TOKEN_RE.fullmatch(str(scope["testTaskRef"]))
        if not match or match.group(1) != "testHandoff":
            raise core.AdapterError("新建测试任务时testTaskRef必须引用testHandoff动作回执。")

    evidence = value.get("evidence")
    if not isinstance(evidence, dict):
        raise core.AdapterError("evidence必须是对象。")
    if not valid_ref(evidence.get("trustedDeliveryVersion")):
        raise core.AdapterError("缺少可信交付版本，不能执行完成开发。")
    try:
        bundle = hg.validate_bundle(evidence.get("handoffEvidence"), "development",
                                    scope, evidence["trustedDeliveryVersion"])
        hg.validate_receipt(bundle["developmentReceipt"], bundle["manifest"],
                            "development", str(scope["developmentTaskId"]))
    except ValueError as error:
        raise core.AdapterError(str(error)) from error
    validation = evidence.get("developmentValidation")
    if not isinstance(validation, dict) or validation.get("status") not in {"passed", "skipped"} \
            or not valid_ref(validation.get("evidence")):
        raise core.AdapterError("开发验证必须为passed或有规则依据的skipped，并提供证据。")
    if validation["status"] == "skipped" and scope["deliveryEnd"] != "小程序":
        raise core.AdapterError("只有小程序范围允许按规则跳过开发侧完成验证。")
    resolution = evidence.get("testScopeResolution")
    if not isinstance(resolution, dict) \
            or resolution.get("schemaVersion") != "oneos.test-scope-resolution/v2" \
            or resolution.get("testTaskRequired") is not True \
            or resolution.get("testMode") != scope["testMode"] \
            or str(resolution.get("projectId") or "") != str(scope["projectId"]) \
            or str(resolution.get("requirement") or "") != str(scope["requirementSerial"]) \
            or str(resolution.get("developmentTask") or "") != str(scope["developmentTaskSerial"]) \
            or str(resolution.get("deliveryEnd") or "") != str(scope["deliveryEnd"]):
        raise core.AdapterError("缺少与当前范围一致的测试模式解析回执。")
    if scope["testMode"] == "formal-plan":
        test_plan = resolution.get("testPlan")
        directories = resolution.get("scopeDirectories")
        directory_ids = resolution.get("directoryIds")
        case_ids = resolution.get("selectedCaseIds")
        if resolution.get("decision") != "formal-plan" \
                or not isinstance(test_plan, dict) or not valid_ref(test_plan.get("id")) \
                or not isinstance(directories, list) or not directories \
                or not isinstance(directory_ids, list) or not directory_ids \
                or not isinstance(case_ids, list) or not case_ids:
            raise core.AdapterError("formal-plan必须包含唯一测试计划、非空端侧目录和具体用例回执。")
        if str(scope["testPlanId"]) != str(test_plan["id"]) \
                or scope["directoryIds"] != directory_ids \
                or scope["selectedCaseIds"] != case_ids:
            raise core.AdapterError("formal-plan的测试计划、目录或具体用例与解析回执不一致。")
        if resolution.get("formalTestValidationSkipped") is not False \
                or resolution.get("skipReason") is not None:
            raise core.AdapterError("formal-plan不得标记为跳过正式测试计划验证。")
    elif resolution.get("decision") not in {
        "test-task-required", "scope-unconfigured", "scope-empty", "plan-read-skipped",
    }:
        raise core.AdapterError(
            "mandatory-test-task必须来自无计划、端侧未配置、正式范围为空或真实读取失败的回执。"
        )
    elif scope["testPlanId"] is not None or scope["directoryIds"] or scope["selectedCaseIds"]:
        raise core.AdapterError("mandatory-test-task不得伪造正式计划、目录或具体用例。")
    elif resolution.get("decision") == "plan-read-skipped":
        discovery = resolution.get("planDiscovery")
        if isinstance(discovery, dict) and discovery.get("status") == "unavailable-json-api":
            if discovery.get("transport") != "official-openapi-json" \
                    or discovery.get("contentType") != "application/json" \
                    or discovery.get("jsonReadAttempted") is not True \
                    or discovery.get("jsonReadSucceeded") is not False \
                    or not isinstance(discovery.get("jsonReadError"), str) \
                    or not discovery["jsonReadError"].strip():
                raise core.AdapterError("跳过测试计划读取必须携带真实JSON失败诊断回执。")
            if resolution.get("formalTestValidationSkipped") is not True \
                    or resolution.get("skipReason") != "plan-read-unavailable-json-api":
                raise core.AdapterError("JSON读取失败必须显式标记跳过正式测试计划验证。")
        else:
            # Read historical receipts without requiring new calls to the broken CLI.
            if not isinstance(discovery, dict) \
                    or discovery.get("status") != "unavailable-after-plugin-upgrade" \
                    or discovery.get("plugin") != "aliyun-cli-devops" \
                    or discovery.get("upgradeAttempted") is not True \
                    or discovery.get("retryAttempted") is not True \
                    or not valid_ref(discovery.get("versionBefore")) \
                    or not valid_ref(discovery.get("versionAfter")) \
                    or not isinstance(discovery.get("initialError"), str) \
                    or not discovery["initialError"].strip() \
                    or not isinstance(discovery.get("retryError"), str) \
                    or not discovery["retryError"].strip():
                raise core.AdapterError("跳过测试计划读取必须携带插件升级、重试和失败诊断回执。")
            if resolution.get("formalTestValidationSkipped") is not True \
                    or resolution.get("skipReason") != "plan-read-unavailable-after-plugin-upgrade":
                raise core.AdapterError("插件升级重试失败后必须显式标记跳过正式测试计划验证。")
    else:
        discovery = resolution.get("planDiscovery")
        if not isinstance(discovery, dict) or discovery.get("status") not in {
            "available", "recovered-after-plugin-upgrade", "recovered-after-json-api", "available-json-api",
        }:
            raise core.AdapterError("无正式计划或用例的结论必须来自成功的测试计划读取回执。")
        if discovery.get("status") in {"recovered-after-json-api", "available-json-api"} and (
            discovery.get("jsonReadAttempted") is not True
            or discovery.get("jsonReadSucceeded") is not True
            or discovery.get("transport") != "official-openapi-json"
            or discovery.get("contentType") != "application/json"
        ):
            raise core.AdapterError("JSON恢复读取必须携带成功的官方API读取回执。")
        expected_skip_reason = {
            "test-task-required": "no-associated-test-plan",
            "scope-unconfigured": "scope-unconfigured",
            "scope-empty": "scope-empty",
        }[resolution["decision"]]
        if resolution.get("formalTestValidationSkipped") is not True \
                or resolution.get("skipReason") != expected_skip_reason:
            raise core.AdapterError("mandatory-test-task必须显式记录跳过正式测试计划验证的原因。")

    stages_raw = value.get("stages")
    if not isinstance(stages_raw, dict):
        raise core.AdapterError("stages必须是对象。")
    stages: dict[str, dict[str, Any]] = {}
    for name in STAGE_ORDER:
        raw = stages_raw.get(name)
        if raw is None:
            continue
        if not isinstance(raw, dict):
            raise core.AdapterError(f"stages.{name}必须是事务计划对象。")
        stages[name] = gateway.validate_plan(raw)
        _require_stage_operations(name, stages[name])
    if not CRITICAL_STAGES.issubset(stages):
        raise core.AdapterError("必须同时提供testHandoff和developmentComplete阶段。")

    keys = [stage["idempotencyKey"] for stage in stages.values()]
    if len(keys) != len(set(keys)):
        raise core.AdapterError("各阶段idempotencyKey必须唯一。")

    test_serialized = _serialized(stages["testHandoff"])
    for required in (
        str(scope["developmentTaskId"]), str(scope["requirementId"]),
        str(scope["deliveryId"]), str(scope["testSupervisorId"]),
        str(scope["testMode"]), str(scope["scopeId"]), str(scope["deliveryEnd"]),
        TEST_SCOPE_START, TEST_SCOPE_END,
    ):
        if required not in test_serialized:
            raise core.AdapterError(f"testHandoff阶段缺少范围约束：{required}")
    for required in scope["directoryIds"] + scope["selectedCaseIds"]:
        if str(required) not in test_serialized:
            raise core.AdapterError(f"testHandoff阶段缺少测试范围ID：{required}")
    for target, _ in _status_updates(stages["testHandoff"]):
        if target in {scope["developmentTaskId"], scope["requirementId"], scope["deliveryId"]}:
            raise core.AdapterError("testHandoff阶段不得提前修改开发、需求或交付状态。")
    stage_scope = dict(scope)
    stage_scope["testTaskRef"] = _stage_test_ref(str(scope["testTaskRef"]))
    _require_test_readbacks(stages["testHandoff"]["verifications"], stage_scope)

    development_updates = _status_updates(stages["developmentComplete"])
    if development_updates != [(str(scope["developmentTaskId"]), "已完成")]:
        raise core.AdapterError("developmentComplete阶段必须且只能把当前开发任务推进到已完成。")
    _require_receipt_write(stages["developmentComplete"], bundle)

    requirement_stage = stages.get("requirementHandoff")
    if requirement_stage is not None:
        if scope["requirementTargetStatus"] != "待测试":
            raise core.AdapterError("需求已为测试中时不得由开发执行器再次推进状态。")
        expected = (str(scope["requirementId"]), str(scope["requirementTargetStatus"]))
        if _status_updates(requirement_stage) != [expected]:
            raise core.AdapterError("requirementHandoff阶段必须且只能推进当前需求到声明的待测状态。")
    requirement_complete_stage = stages.get("requirementDevelopmentComplete")
    if requirement_complete_stage is not None:
        expected = (str(scope["requirementId"]), "开发完成")
        if _status_updates(requirement_complete_stage) != [expected]:
            raise core.AdapterError(
                "requirementDevelopmentComplete阶段必须且只能推进当前需求到开发完成。"
            )

    final_raw = value.get("finalReadbacks")
    if not isinstance(final_raw, list) or not final_raw:
        raise core.AdapterError("finalReadbacks不能为空。")
    final_calls = [
        gateway.validate_call(item, False) | {"expect": item.get("expect")}
        for item in final_raw
    ]
    _require_status_readback(final_calls, str(scope["developmentTaskId"]), "已完成", "开发任务")
    _require_status_readback(
        final_calls, str(scope["requirementId"]), str(scope["requirementTargetStatus"]), "需求",
    )
    _require_status_readback(final_calls, str(scope["deliveryId"]), "处理中", "交付任务")
    _require_test_readbacks(final_calls, scope)
    dev_readback = next(call for call in final_calls if call["operation"] == "projex-get-workitem"
                        and _arg_value(call["args"], "--id") == str(scope["developmentTaskId"]))
    try:
        if hg.bundle_from_description((dev_readback.get("expect") or {}).get("description", "")) != bundle:
            raise ValueError("开发回执与计划不一致")
    except ValueError as error:
        raise core.AdapterError(f"交棒回执缺少 finalReadbacks：{error}") from error

    return {
        "schemaVersion": SCHEMA,
        "suiteVersion": SUITE_VERSION,
        "idempotencyKey": idempotency_key,
        "scope": scope,
        "evidence": evidence,
        "testDeliveryMode": requested_delivery,
        "stages": stages,
        "finalReadbacks": final_calls,
    }


def _require_receipt_write(stage: dict, bundle: dict) -> None:
    description = gateway._description_value(stage["actions"][0])
    try:
        if hg.bundle_from_description(description or "") != bundle:
            raise ValueError("开发回执与计划不一致")
    except ValueError as error:
        raise core.AdapterError(f"交棒回执必须随开发完成写入开发任务：{error}") from error
    matches = [call for call in stage["verifications"]
               if call["operation"] == "projex-get-workitem"
               and _arg_value(call["args"], "--id") == bundle["developmentReceipt"]["taskId"]
               and (call.get("expect") or {}).get("description") == description]
    if len(matches) != 1:
        raise core.AdapterError("交棒理解回执必须在 developmentComplete 阶段内完整回读。")


def _verify_handoff(plan: dict) -> None:
    """Fresh authoritative reads before preflight and every lifecycle write."""
    executable = core.find_aliyun()
    core.require_auth_env()
    # Cache only within this fresh gate call; never reuse an earlier stage's reads.
    items: dict[str, dict] = {}
    def read(item_id):
        if item_id not in items:
            items[item_id] = core.unwrap(gateway.execute_read(executable, {
                "operation": "projex-get-workitem", "args": ["--id", item_id]}))
        return items[item_id]
    bundle = plan["evidence"]["handoffEvidence"]
    try:
        scope = plan["scope"]
        for field in ("developmentTaskId", "deliveryId", "requirementId"):
            item_id = str(scope[field])
            item = read(item_id)
            if not isinstance(item, dict) or str(item.get("id")) != item_id:
                raise ValueError("完成开发工作项身份无法唯一回读")
            space = item.get("space") or {}
            project_id = str((space.get("id") if isinstance(space, dict) else "") or
                             item.get("spaceIdentifier") or item.get("spaceId") or item.get("projectId") or "")
            if project_id != str(scope["projectId"]):
                raise ValueError("完成开发工作项项目归属不一致或无法回读")
        relations = core.unwrap(gateway.execute_read(executable, {
            "operation": "projex-list-workitem-relation-records",
            "args": ["--id", str(scope["deliveryId"]), "--relation-type", "ASSOCIATED"]}))
        if not isinstance(relations, list) or str(scope["requirementId"]) not in {
            str(row.get("resourceId") or "") for row in relations if isinstance(row, dict)
        }:
            raise ValueError("交付任务与需求的真实关联无法回读或不一致")
        hg.verify_live_bundle(bundle, "development", read, plan["scope"],
                              plan["evidence"]["trustedDeliveryVersion"])
        hg.verify_documents(bundle["manifest"])
        item = read(plan["scope"]["developmentTaskId"])
        if not isinstance(item, dict) or str(item.get("id")) != plan["scope"]["developmentTaskId"]:
            raise ValueError("官方开发任务身份无法唯一回读")
        handoff_start.verify_task_binding(executable, item, bundle["manifest"]["scope"])
        planned = gateway._description_value(
            plan["stages"]["developmentComplete"]["actions"][0]
        )
        if planned != hg.upsert_bundle(str(item.get("description") or ""), bundle):
            raise ValueError("开发描述已变化或计划覆盖了人工正文，须刷新计划")
    except (ValueError, OSError) as error:
        raise core.AdapterError(f"交棒实时校验失败：{error}") from error


def _stage_dir(output: Path) -> Path:
    return output.parent / f"{output.stem}-stages"


def _call_gateway(func: Any, args: argparse.Namespace) -> None:
    with contextlib.redirect_stdout(io.StringIO()):
        func(args)


def command_preflight(args: argparse.Namespace) -> int:
    plan = validate_plan(load_object(args.plan))
    _verify_handoff(plan)
    output = Path(args.output) if args.output else core.output_dir() / \
        f"complete-development-preflight-{gateway.stable_hash(plan)[:16]}.json"
    stages_root = _stage_dir(output)
    stage_receipts: dict[str, Any] = {}
    for name in STAGE_ORDER:
        stage = plan["stages"].get(name)
        if stage is None:
            continue
        plan_path = stages_root / f"{name}-plan.json"
        preflight_path = stages_root / f"{name}-preflight.json"
        gateway.write_json(plan_path, stage)
        try:
            _call_gateway(
                gateway.cmd_preflight,
                argparse.Namespace(plan=str(plan_path), output=str(preflight_path)),
            )
            receipt = gateway.load_object(str(preflight_path))
            stage_receipts[name] = {"status": "ready", "path": str(preflight_path),
                                    "fingerprint": receipt.get("fingerprint")}
        except Exception as error:
            if name != "effort":
                raise
            stage_receipts[name] = {"status": "skipped", "error": core.scrub(str(error))}
    receipt = {
        "schemaVersion": PREFLIGHT_SCHEMA,
        "suiteVersion": SUITE_VERSION,
        "result": "ready",
        "fingerprint": gateway.stable_hash(plan),
        "plan": plan,
        "stagePreflights": stage_receipts,
        "createdAt": core.now_utc(),
    }
    gateway.write_json(output, receipt)
    print(json.dumps({"result": "ready", "preflight": str(output),
                      "fingerprint": receipt["fingerprint"]}, ensure_ascii=False, indent=2))
    return 0


def _resolve_stage_token(value: Any, outcomes: dict[str, Any]) -> Any:
    if isinstance(value, dict):
        return {key: _resolve_stage_token(child, outcomes) for key, child in value.items()}
    if isinstance(value, list):
        return [_resolve_stage_token(child, outcomes) for child in value]
    if not isinstance(value, str):
        return value
    match = STAGE_TOKEN_RE.fullmatch(value)
    if not match:
        return value
    stage_name, raw_index, path = match.groups()
    stage = outcomes.get(stage_name) or {}
    actions = ((stage.get("receipt") or {}).get("actions") or [])
    index = int(raw_index)
    if index >= len(actions):
        raise core.AdapterError(f"阶段动作回执不存在：{value}")
    return gateway.get_path(actions[index].get("result"), path)


def _run_final_readbacks(plan: dict[str, Any], outcomes: dict[str, Any]) -> list[dict[str, Any]]:
    executable = core.find_aliyun()
    core.require_auth_env()
    receipts: list[dict[str, Any]] = []
    for index, raw in enumerate(plan["finalReadbacks"]):
        call = _resolve_stage_token(raw, outcomes)
        value = gateway.execute_read(executable, call)
        gateway.assert_expect(value, call.get("expect"), f"finalReadbacks[{index}]")
        receipts.append({"index": index, "call": call, "sha256": gateway.stable_hash(value)})
    return receipts


def command_apply(args: argparse.Namespace) -> int:
    preflight = load_object(args.preflight)
    if preflight.get("schemaVersion") != PREFLIGHT_SCHEMA or preflight.get("result") != "ready":
        raise core.AdapterError("无效的完成开发预检回执。")
    plan = validate_plan(preflight.get("plan") or {})
    fingerprint = gateway.stable_hash(plan)
    if fingerprint != preflight.get("fingerprint"):
        raise core.AdapterError("完成开发预检指纹不一致。")
    _verify_handoff(plan)
    output = Path(args.output) if args.output else core.output_dir() / \
        f"complete-development-{gateway.stable_hash(plan['idempotencyKey'])[:16]}.json"
    progress = load_object(output) if output.is_file() else {
        "schemaVersion": RECEIPT_SCHEMA,
        "suiteVersion": SUITE_VERSION,
        "result": "applying",
        "fingerprint": fingerprint,
        "idempotencyKey": plan["idempotencyKey"],
        "scope": plan["scope"],
        "evidence": plan["evidence"],
        "testDeliveryMode": plan["testDeliveryMode"],
        "stages": {},
        "startedAt": core.now_utc(),
    }
    if progress.get("fingerprint") != fingerprint:
        raise core.AdapterError("完成开发回执与当前计划不一致。")
    if not isinstance(progress.get("stages"), dict):
        raise core.AdapterError("完成开发回执stages损坏，禁止继续执行。")
    if progress.get("result") == "complete":
        print(json.dumps(progress, ensure_ascii=False, indent=2))
        return 0
    gateway.write_json(output, progress)

    preflights = preflight.get("stagePreflights") or {}
    for name in STAGE_ORDER:
        stage = plan["stages"].get(name)
        if stage is None:
            continue
        existing = progress["stages"].get(name) or {}
        if existing.get("status") in {"applied", "skipped"}:
            continue
        stage_preflight = preflights.get(name) or {}
        if stage_preflight.get("status") != "ready":
            if name == "effort":
                progress["stages"][name] = {"status": "skipped",
                                                   "error": stage_preflight.get("error")}
                gateway.write_json(output, progress)
                continue
            raise core.AdapterError(f"关键阶段{name}缺少ready预检。")
        stage_receipt_path = _stage_dir(Path(args.preflight)) / f"{name}-apply.json"
        handoff_checked = False
        try:
            _verify_handoff(plan)
            handoff_checked = True
            _call_gateway(
                gateway.cmd_apply,
                argparse.Namespace(preflight=stage_preflight["path"],
                                   receipt=str(stage_receipt_path), resume=True,
                                   predecessors=[
                                       {"plan": plan["stages"][previous], "receipt": outcome["receipt"]}
                                       for previous, outcome in progress["stages"].items()
                                       if outcome.get("status") == "applied"
                                   ]),
            )
            stage_receipt = gateway.load_object(str(stage_receipt_path))
            progress["stages"][name] = {"status": "applied", "receipt": stage_receipt}
            gateway.write_json(output, progress)
        except Exception as error:
            progress["stages"][name] = {"status": "failed", "error": core.scrub(str(error)),
                                                "receiptPath": str(stage_receipt_path)}
            progress["result"] = "partial"
            progress["failedStage"] = name
            progress["failedAt"] = core.now_utc()
            gateway.write_json(output, progress)
            if name == "effort" and handoff_checked:
                progress["stages"][name]["status"] = "skipped"
                progress["result"] = "applying"
                progress.pop("failedStage", None)
                progress.pop("failedAt", None)
                gateway.write_json(output, progress)
                continue
            raise

    try:
        progress["finalReadbacks"] = _run_final_readbacks(plan, progress["stages"])
    except Exception as error:
        progress["result"] = "partial"
        progress["failedStage"] = "finalReadbacks"
        progress["failedAt"] = core.now_utc()
        progress["error"] = core.scrub(str(error))
        gateway.write_json(output, progress)
        raise
    progress["result"] = "complete"
    progress["completedAt"] = core.now_utc()
    progress.pop("failedStage", None)
    progress.pop("failedAt", None)
    gateway.write_json(output, progress)
    print(json.dumps({"result": "complete", "receipt": str(output),
                      "scope": progress["scope"], "testDeliveryMode": progress["testDeliveryMode"],
                      "nextAction": "execute-test-pipeline" if progress["testDeliveryMode"] == "execute"
                      else "pending-deployment-test-handoff", "verified": True},
                     ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    preflight = sub.add_parser("preflight")
    preflight.add_argument("--plan", required=True)
    preflight.add_argument("--suite-state", help="已弃用；兼容旧命令但不读取或校验其他Skill安装")
    preflight.add_argument("--output")
    preflight.set_defaults(func=command_preflight)
    apply = sub.add_parser("apply")
    apply.add_argument("--preflight", required=True)
    apply.add_argument("--output")
    apply.set_defaults(func=command_apply)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        return int(args.func(args))
    except (core.AdapterError, OSError, ValueError, json.JSONDecodeError) as error:
        print(json.dumps({"result": "blocked", "error": core.scrub(str(error))},
                         ensure_ascii=False, indent=2), file=sys.stderr)
        return 69


if __name__ == "__main__":
    raise SystemExit(main())
