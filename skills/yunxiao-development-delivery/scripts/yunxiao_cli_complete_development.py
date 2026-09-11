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
import verify_lifecycle_suite as suite


SCHEMA = "oneos.complete-development-plan/v1"
PREFLIGHT_SCHEMA = "oneos.complete-development-preflight/v1"
RECEIPT_SCHEMA = "oneos.complete-development-receipt/v1"
SUITE_VERSION = "10.1.1"
TEST_SCOPE_START = "<!-- ONEOS_TEST_SCOPE_START -->"
TEST_SCOPE_END = "<!-- ONEOS_TEST_SCOPE_END -->"
ALLOWED_TEST_MODES = {"formal-plan", "mandatory-test-task"}
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
    description = str(expect.get("description") or "")
    for required in (
        TEST_SCOPE_START, TEST_SCOPE_END, str(scope["developmentTaskId"]),
        str(scope["requirementId"]), str(scope["deliveryId"]), str(scope["testMode"]),
        str(scope["scopeId"]), str(scope["deliveryEnd"]),
    ):
        if required not in description:
            raise core.AdapterError(f"测试任务描述回读缺少受管范围字段：{required}")

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


def _verify_suite_state(value: dict[str, Any]) -> dict[str, Any]:
    if value.get("schemaVersion") != suite.SCHEMA:
        raise core.AdapterError(f"suite-state必须为{suite.SCHEMA}。")
    if value.get("suiteVersion") != SUITE_VERSION or value.get("verified") is not True:
        raise core.AdapterError(f"五个生命周期Skill必须全部回读为{SUITE_VERSION}。")
    evidence = value.get("evidencePaths")
    if not isinstance(evidence, dict) or set(evidence) != suite.REQUIRED:
        raise core.AdapterError("suite-state缺少五个生命周期Skill的精确安装路径。")
    try:
        actual = suite.verify([f"{name}={evidence[name]}" for name in sorted(suite.REQUIRED)])
    except (OSError, ValueError) as error:
        raise core.AdapterError(f"无法实时回读生命周期Skill：{error}") from error
    if actual.get("verified") is not True or actual.get("suiteVersion") != SUITE_VERSION:
        raise core.AdapterError(f"生命周期Skill实时版本未全部对齐{SUITE_VERSION}。")
    return actual


def validate_plan(value: dict[str, Any]) -> dict[str, Any]:
    gateway.assert_no_secrets(value)
    if value.get("schemaVersion") != SCHEMA:
        raise core.AdapterError(f"计划schemaVersion必须为{SCHEMA}。")
    if value.get("suiteVersion") != SUITE_VERSION:
        raise core.AdapterError(f"计划suiteVersion必须为{SUITE_VERSION}。")
    idempotency_key = str(value.get("idempotencyKey") or "").strip()
    if not idempotency_key:
        raise core.AdapterError("完成开发计划缺少稳定idempotencyKey。")

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
        if resolution.get("decision") != "formal-plan" \
                or not isinstance(test_plan, dict) or not valid_ref(test_plan.get("id")) \
                or not isinstance(directories, list) or not directories:
            raise core.AdapterError("formal-plan必须包含唯一测试计划和非空端侧目录回执。")
    elif resolution.get("decision") not in {"test-task-required", "scope-unconfigured"}:
        raise core.AdapterError("mandatory-test-task必须来自无计划或端侧未配置回执。")

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
    for target, _ in _status_updates(stages["testHandoff"]):
        if target in {scope["developmentTaskId"], scope["requirementId"], scope["deliveryId"]}:
            raise core.AdapterError("testHandoff阶段不得提前修改开发、需求或交付状态。")
    stage_scope = dict(scope)
    stage_scope["testTaskRef"] = _stage_test_ref(str(scope["testTaskRef"]))
    _require_test_readbacks(stages["testHandoff"]["verifications"], stage_scope)

    development_updates = _status_updates(stages["developmentComplete"])
    if development_updates != [(str(scope["developmentTaskId"]), "已完成")]:
        raise core.AdapterError("developmentComplete阶段必须且只能把当前开发任务推进到已完成。")

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

    return {
        "schemaVersion": SCHEMA,
        "suiteVersion": SUITE_VERSION,
        "idempotencyKey": idempotency_key,
        "scope": scope,
        "evidence": evidence,
        "stages": stages,
        "finalReadbacks": final_calls,
    }


def _stage_dir(output: Path) -> Path:
    return output.parent / f"{output.stem}-stages"


def _call_gateway(func: Any, args: argparse.Namespace) -> None:
    with contextlib.redirect_stdout(io.StringIO()):
        func(args)


def command_preflight(args: argparse.Namespace) -> int:
    suite_state = _verify_suite_state(load_object(args.suite_state))
    plan = validate_plan(load_object(args.plan))
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
        "suiteState": suite_state,
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
    _verify_suite_state(preflight.get("suiteState") or {})
    plan = validate_plan(preflight.get("plan") or {})
    fingerprint = gateway.stable_hash(plan)
    if fingerprint != preflight.get("fingerprint"):
        raise core.AdapterError("完成开发预检指纹不一致。")
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
        try:
            _call_gateway(
                gateway.cmd_apply,
                argparse.Namespace(preflight=stage_preflight["path"],
                                   receipt=str(stage_receipt_path)),
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
            if name == "effort":
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
                      "scope": progress["scope"], "verified": True},
                     ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    preflight = sub.add_parser("preflight")
    preflight.add_argument("--plan", required=True)
    preflight.add_argument("--suite-state", required=True)
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
