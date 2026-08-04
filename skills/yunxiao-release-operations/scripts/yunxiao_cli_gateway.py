#!/usr/bin/env python3
"""Guarded transaction gateway for all remaining Yunxiao CLI operations."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml

import yunxiao_cli_runtime as core


SCHEMA = "oneos.yunxiao-cli-transaction/v1"
PLAN_SCHEMA = "oneos.yunxiao-cli-transaction-plan/v1"
READ_PREFIXES = (
    "base-get-", "projex-get-", "projex-list-", "projex-search-",
    "codeup-get-", "codeup-list-", "flow-get-", "flow-list-",
    "app-stack-get-", "app-stack-list-", "app-stack-search-",
    "app-stack-find-",
)
WRITE_OPERATIONS = {
    "projex-create-workitem", "projex-update-workitem",
    "projex-create-workitem-comment", "projex-create-workitem-relation-record",
    "projex-create-workitem-ext-relation-record", "projex-update-custom-field",
    "projex-create-estimated-effort", "projex-update-estimated-effort",
    "projex-create-effort-record", "projex-update-effort-record",
    "codeup-create-branch", "codeup-create-change-request",
    "codeup-update-change-request", "codeup-update-change-request-related-person",
    "codeup-merge-change-request", "codeup-delete-branch",
    "flow-create-pipeline-run", "flow-execute-pipeline-job-action",
    "flow-create-smoke-pipeline",
    "flow-execute-pipeline-job-run", "flow-rerun-pipeline-job-run",
    "flow-retry-pipeline-job-run", "flow-resume-vm-deploy-order",
    "flow-retry-vm-deploy-machine", "flow-pass-pipeline-validate",
    "flow-refuse-pipeline-validate", "flow-update-pipeline-run",
    "app-stack-create-change-request", "app-stack-create-change-order",
    "app-stack-execute-change-request-release-stage",
    "app-stack-cancel-execution-release-stage",
    "app-stack-retry-change-request-stage-pipeline",
    "app-stack-skip-change-request-stage-pipeline",
    "app-stack-pass-release-stage-pipeline-validate",
    "app-stack-refuse-release-stage-pipeline-validate",
    "app-stack-close-change-request", "app-stack-cancel-change-request",
}
SECRET_RE = re.compile(
    r"(?i)(access[_-]?token|authorization|password|secret|access[_-]?key|private[_-]?key|cookie)"
)
TOKEN_RE = re.compile(r"^\$\{action\.(\d+)\.([A-Za-z0-9_.-]+)\}$")


def stable_hash(value: Any) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def assert_no_secrets(value: Any, path: str = "plan") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if SECRET_RE.search(str(key)):
                raise core.AdapterError(f"{path}不得包含凭据字段：{key}")
            assert_no_secrets(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            assert_no_secrets(child, f"{path}[{index}]")
    elif isinstance(value, str) and SECRET_RE.search(value):
        raise core.AdapterError(f"{path}不得包含凭据或敏感参数。")


def load_object(path: str) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise core.AdapterError(f"{path}必须是JSON对象。")
    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def validate_args(args: Any) -> list[str]:
    if not isinstance(args, list) or not all(isinstance(v, str) for v in args):
        raise core.AdapterError("CLI args必须是字符串数组。")
    for value in args:
        if "\x00" in value or "\r" in value or "\n" in value:
            raise core.AdapterError("CLI参数不得包含换行或NUL。")
        if SECRET_RE.search(value):
            raise core.AdapterError("计划/回执不得包含凭据或敏感参数；请使用云效受保护变量。")
    return list(args)


def is_read(operation: str) -> bool:
    return any(operation.startswith(prefix) for prefix in READ_PREFIXES)


def validate_call(call: Any, write: bool) -> dict[str, Any]:
    if not isinstance(call, dict):
        raise core.AdapterError("调用定义必须是JSON对象。")
    operation = str(call.get("operation") or "")
    if write:
        if operation not in WRITE_OPERATIONS:
            raise core.AdapterError(f"写操作不在白名单：{operation}")
    elif not is_read(operation):
        raise core.AdapterError(f"只读操作不在白名单：{operation}")
    return {"operation": operation, "args": validate_args(call.get("args", []))}


def get_path(value: Any, path: str) -> Any:
    current = core.unwrap(value)
    if not path:
        return current
    for part in path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        elif isinstance(current, list) and part.isdigit() and int(part) < len(current):
            current = current[int(part)]
        else:
            raise core.AdapterError(f"回执模板路径不存在：{path}")
    return current


def resolve_args(args: list[str], action_outputs: list[Any]) -> list[str]:
    resolved: list[str] = []
    for value in args:
        match = TOKEN_RE.fullmatch(value)
        if not match:
            resolved.append(value)
            continue
        index = int(match.group(1))
        if index >= len(action_outputs):
            raise core.AdapterError(f"动作回执尚不存在：action.{index}")
        replacement = get_path(action_outputs[index], match.group(2))
        if isinstance(replacement, (dict, list)):
            replacement = json.dumps(replacement, ensure_ascii=False, separators=(",", ":"))
        resolved.append(str(replacement))
    return resolved


def parse_flag_args(args: list[str], required: set[str]) -> dict[str, str]:
    if len(args) % 2:
        raise core.AdapterError("模拟生产流水线参数必须为成对的--参数 值。")
    values: dict[str, str] = {}
    for index in range(0, len(args), 2):
        key, value = args[index], args[index + 1]
        if not key.startswith("--") or key in values:
            raise core.AdapterError("模拟生产流水线参数重复或格式无效。")
        values[key] = value
    if set(values) != required:
        raise core.AdapterError("模拟生产流水线参数不完整或包含未允许字段。")
    return values


def strip_pipeline_plugins(flow: str) -> str:
    """Remove notification/plugin blocks so copied YAML never carries secrets."""
    output: list[str] = []
    lines = flow.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        match = re.match(r"^(\s*)plugins:\s*$", line)
        if not match:
            output.append(line)
            index += 1
            continue
        indent = len(match.group(1))
        output.append(" " * indent + "plugins: []")
        index += 1
        while index < len(lines):
            candidate = lines[index]
            if candidate.strip() and len(candidate) - len(candidate.lstrip(" ")) <= indent:
                break
            index += 1
    return "\n".join(output) + "\n"


def build_smoke_pipeline_flow(source: dict[str, Any]) -> str:
    config = source.get("pipelineConfig") or {}
    flow = str(config.get("flow") or "")
    sources = config.get("sources") or []
    if not flow or not isinstance(sources, list) or len(sources) != 1:
        raise core.AdapterError("源test流水线缺少唯一的YAML或Codeup代码源。")
    source_data = sources[0].get("data") if isinstance(sources[0], dict) else None
    if not isinstance(source_data, dict):
        raise core.AdapterError("源test流水线代码源格式无效。")
    repo = str(source_data.get("repo") or "")
    branch = str(source_data.get("branch") or "")
    if not repo or not branch:
        raise core.AdapterError("源test流水线缺少仓库或分支。")
    clean_flow = strip_pipeline_plugins(flow)
    if SECRET_RE.search(clean_flow):
        raise core.AdapterError("源流水线脱敏后仍含敏感配置，拒绝复制。")
    try:
        document = yaml.safe_load(clean_flow)
    except yaml.YAMLError as exc:
        raise core.AdapterError(f"源test流水线YAML无法解析：{exc}") from exc
    if not isinstance(document, dict) or document.get("schema") != "tb":
        raise core.AdapterError("源test流水线不是受支持的YAML格式。")
    legacy_pipeline = document.pop("pipeline", None)
    if not isinstance(legacy_pipeline, list) or not legacy_pipeline:
        raise core.AdapterError("源test流水线缺少可转换的阶段配置。")
    # 旧版 UI 配置将构建组保存在任务参数中；创建 API 要求将其显式映射为
    # runsOn。只接受源流水线已经在用的唯一标识，绝不猜测或创建构建组。
    source_runs_on = ""
    for phase in legacy_pipeline:
        if not isinstance(phase, dict):
            continue
        for phase_stage in phase.get("stages") or []:
            for job in (phase_stage.get("jobs") if isinstance(phase_stage, dict) else []) or []:
                params = job.get("params") if isinstance(job, dict) else None
                candidate = str((params or {}).get("buildNodeGroup") or "").strip()
                if candidate:
                    source_runs_on = candidate
                    break
            if source_runs_on:
                break
        if source_runs_on:
            break
    if not source_runs_on:
        raise core.AdapterError("源test流水线未声明可继承的构建组，拒绝猜测runsOn。")
    stages: dict[str, Any] = {}
    for phase_index, phase in enumerate(legacy_pipeline, start=1):
        if not isinstance(phase, dict) or not str(phase.get("name") or "").strip():
            raise core.AdapterError("源test流水线阶段配置无效。")
        phase_stages = phase.get("stages")
        if not isinstance(phase_stages, list) or len(phase_stages) != 1:
            raise core.AdapterError("源test流水线阶段层级不支持安全复制。")
        phase_stage = phase_stages[0]
        jobs_raw = phase_stage.get("jobs") if isinstance(phase_stage, dict) else None
        if not isinstance(jobs_raw, list) or not jobs_raw:
            raise core.AdapterError("源test流水线缺少可运行任务。")
        jobs: dict[str, Any] = {}
        for job_index, job in enumerate(jobs_raw, start=1):
            if not isinstance(job, dict):
                raise core.AdapterError("源test流水线任务配置无效。")
            converted_job = dict(job)
            display_name = str(converted_job.pop("displayName", "") or "")
            if display_name:
                converted_job["name"] = display_name
            # 旧版 Flow UI 导出的任务未显式写出运行集群；创建 API 的 YAML
            # 则要求 runsOn。只继承源测试流水线已经在用的构建组。
            if not str(converted_job.get("runsOn") or "").strip():
                converted_job["runsOn"] = source_runs_on
            jobs[f"smoke_job_{phase_index}_{job_index}"] = converted_job
        stages[f"smoke_stage_{phase_index}"] = {"name": str(phase["name"]), "jobs": jobs}
    document["stages"] = stages
    document["sources"] = {
        "smoke_source": {
            "type": "codeup",
            "name": "ln-one-os-web",
            "endpoint": repo,
            "branch": branch,
            "certificate": {"type": "serviceConnection", "serviceConnection": "${SMOKE_CODEUP_CONNECTION}"},
        }
    }
    document["defaultWorkspace"] = "smoke_source"
    return yaml.safe_dump(document, allow_unicode=True, sort_keys=False)


def execute_smoke_pipeline_create(executable: str, args: list[str]) -> dict[str, Any]:
    flags = parse_flag_args(
        args,
        {"--source-pipeline-id", "--pipeline-name", "--env-id"},
    )
    source_id = flags["--source-pipeline-id"]
    name = flags["--pipeline-name"]
    if flags["--env-id"] != "0":
        raise core.AdapterError("模拟生产流水线只能创建在日常环境（env-id=0）。")
    lowered = name.lower()
    if "smoke" not in lowered or "prod" not in lowered or lowered == "oneos-web-prod":
        raise core.AdapterError("模拟生产流水线名称必须包含smoke和prod，且不得为真实prod名称。")
    source = core.unwrap(core.run_devops(executable, ["flow-get-pipeline", "--pipeline-id", source_id]))
    if not isinstance(source, dict):
        raise core.AdapterError("源test流水线无法回读。")
    source_name = str(source.get("name") or "").lower()
    if "test" not in source_name or source.get("envId") != 0:
        raise core.AdapterError("源流水线必须是日常环境的test流水线。")
    connections = core.unwrap(core.run_devops(executable, [
        "flow-list-service-connections", "--service-connection-type", "Codeup",
    ]))
    if not isinstance(connections, list) or len(connections) != 1:
        raise core.AdapterError("无法唯一解析可用的Codeup服务连接。")
    connection_uuid = str((connections[0] or {}).get("uuid") or "")
    if not connection_uuid:
        raise core.AdapterError("Codeup服务连接缺少UUID。")
    flow = build_smoke_pipeline_flow(source).replace("${SMOKE_CODEUP_CONNECTION}", connection_uuid)
    created = core.unwrap(core.run_devops(executable, [
        "flow-create-pipeline", "--name", name, "--content", flow,
    ]))
    if not isinstance(created, dict):
        raise core.AdapterError("创建模拟生产流水线后未返回流水线信息。")
    pipeline_id = created.get("id") or created.get("pipelineId")
    if pipeline_id is None:
        raise core.AdapterError("创建模拟生产流水线后未返回流水线ID。")
    return {
        "pipelineId": str(pipeline_id),
        "pipelineName": name,
        "sourcePipelineId": source_id,
        "environment": "日常环境",
        "releaseMode": "smoke",
        "pluginsStripped": True,
    }


def assert_expect(value: Any, expect: Any, label: str) -> None:
    if expect is None:
        return
    if not isinstance(expect, dict):
        raise core.AdapterError(f"{label}.expect必须是路径到期望值的对象。")
    for path, expected in expect.items():
        actual = get_path(value, str(path))
        if actual != expected:
            raise core.AdapterError(
                f"{label}校验失败：{path} 当前={actual!r} 期望={expected!r}"
            )


def execute_read(executable: str, call: dict[str, Any], outputs: list[Any] | None = None) -> Any:
    args = resolve_args(call["args"], outputs or [])
    return core.run_devops(executable, [call["operation"], *args])


def validate_plan(value: dict[str, Any]) -> dict[str, Any]:
    assert_no_secrets(value)
    if value.get("schema") != PLAN_SCHEMA:
        raise core.AdapterError(f"计划schema必须为{PLAN_SCHEMA}。")
    authority = value.get("authority")
    if authority not in {"apply", "execute", "cleanup"}:
        raise core.AdapterError("计划authority必须为apply、execute或cleanup。")
    idempotency_key = str(value.get("idempotencyKey") or "").strip()
    if not idempotency_key:
        raise core.AdapterError("计划必须提供稳定的idempotencyKey。")
    guards = [validate_call(item, False) | {"expect": item.get("expect")}
              for item in value.get("guards", [])]
    actions = [validate_call(item, True) for item in value.get("actions", [])]
    verifications = [validate_call(item, False) | {"expect": item.get("expect")}
                     for item in value.get("verifications", [])]
    if not guards or not actions or not verifications:
        raise core.AdapterError("事务计划必须同时包含guards、actions和verifications。")
    if any(item["operation"] == "codeup-delete-branch" for item in actions):
        if authority != "cleanup" or value.get("destructiveConfirmation") is not True:
            raise core.AdapterError("删除分支必须使用cleanup权限并显式确认destructiveConfirmation=true。")
    return {
        "schema": PLAN_SCHEMA,
        "label": str(value.get("label") or "Yunxiao CLI transaction"),
        "authority": authority,
        "idempotencyKey": idempotency_key,
        "guards": guards,
        "actions": actions,
        "verifications": verifications,
        "destructiveConfirmation": bool(value.get("destructiveConfirmation", False)),
    }


def cmd_doctor(_: argparse.Namespace) -> int:
    executable = core.find_aliyun()
    flags = core.require_auth_env()
    user = core.current_user(executable)
    result = {
        "schema": SCHEMA, "result": "ok", "cli": executable,
        "auth": flags, "currentUser": user, "checkedAt": core.now_utc(),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def cmd_read(args: argparse.Namespace) -> int:
    executable = core.find_aliyun()
    core.require_auth_env()
    request = validate_call(load_object(args.request), False)
    value = execute_read(executable, request)
    print(json.dumps({"schema": SCHEMA, "result": "ok", "request": request,
                      "value": value, "readAt": core.now_utc()},
                     ensure_ascii=False, indent=2))
    return 0


def cmd_preflight(args: argparse.Namespace) -> int:
    executable = core.find_aliyun()
    core.require_auth_env()
    plan = validate_plan(load_object(args.plan))
    guard_receipts = []
    for index, guard in enumerate(plan["guards"]):
        value = execute_read(executable, guard)
        assert_expect(value, guard.get("expect"), f"guard[{index}]")
        guard_receipts.append({"call": guard, "sha256": stable_hash(value)})
    fingerprint = stable_hash(plan)
    receipt = {
        "schema": SCHEMA, "stage": "preflight", "result": "ready",
        "fingerprint": fingerprint, "plan": plan, "guards": guard_receipts,
        "currentUser": core.current_user(executable), "createdAt": core.now_utc(),
    }
    output = Path(args.output) if args.output else core.output_dir() / f"yunxiao-preflight-{fingerprint[:16]}.json"
    write_json(output, receipt)
    print(json.dumps({"result": "ready", "preflight": str(output),
                      "fingerprint": fingerprint}, ensure_ascii=False, indent=2))
    return 0


def cmd_apply(args: argparse.Namespace) -> int:
    executable = core.find_aliyun()
    core.require_auth_env()
    preflight = load_object(args.preflight)
    if preflight.get("schema") != SCHEMA or preflight.get("stage") != "preflight":
        raise core.AdapterError("无效的CLI事务预检回执。")
    plan = validate_plan(preflight.get("plan") or {})
    fingerprint = stable_hash(plan)
    if fingerprint != preflight.get("fingerprint"):
        raise core.AdapterError("预检计划指纹不匹配。")
    ledger_key = stable_hash(plan["idempotencyKey"])
    ledger = core.output_dir() / f"yunxiao-applied-{ledger_key}.json"
    if ledger.is_file():
        prior = load_object(str(ledger))
        if prior.get("fingerprint") != fingerprint:
            raise core.AdapterError("相同idempotencyKey已有不同计划的成功回执，拒绝重复写入。")
        print(json.dumps(prior, ensure_ascii=False, indent=2))
        return 0
    expected_guards = preflight.get("guards") or []
    for index, guard in enumerate(plan["guards"]):
        value = execute_read(executable, guard)
        assert_expect(value, guard.get("expect"), f"guard[{index}]")
        if index >= len(expected_guards) or stable_hash(value) != expected_guards[index].get("sha256"):
            raise core.AdapterError(f"guard[{index}]发生漂移，拒绝写入。")
    action_outputs: list[Any] = []
    for action in plan["actions"]:
        resolved = resolve_args(action["args"], action_outputs)
        if action["operation"] == "flow-create-smoke-pipeline":
            action_outputs.append(execute_smoke_pipeline_create(executable, resolved))
        else:
            # 写接口沿用 CLI 外层响应包装；事务模板只能引用业务返回体。
            # 统一拆包后，${action.0.pipelineRunId} 等回读模板可稳定解析。
            action_outputs.append(core.unwrap(core.run_devops(executable, [action["operation"], *resolved])))
    verification_receipts = []
    for index, verification in enumerate(plan["verifications"]):
        value = execute_read(executable, verification, action_outputs)
        assert_expect(value, verification.get("expect"), f"verification[{index}]")
        verification_receipts.append({"call": verification, "value": value})
    receipt = {
        "schema": SCHEMA, "stage": "apply", "result": "applied",
        "fingerprint": fingerprint, "idempotencyKey": plan["idempotencyKey"],
        "actions": [{"operation": item["operation"], "result": action_outputs[index]}
                    for index, item in enumerate(plan["actions"])],
        "verifications": verification_receipts,
        "currentUser": core.current_user(executable), "appliedAt": core.now_utc(),
    }
    write_json(ledger, receipt)
    if args.receipt:
        write_json(Path(args.receipt), receipt)
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    doctor = sub.add_parser("doctor", help="校验官方CLI、环境变量和PAT用户")
    doctor.set_defaults(func=cmd_doctor)
    read = sub.add_parser("read", help="执行白名单内只读CLI请求")
    read.add_argument("--request", required=True)
    read.set_defaults(func=cmd_read)
    preflight = sub.add_parser("preflight", help="执行守卫读取并生成不可变预检回执")
    preflight.add_argument("--plan", required=True)
    preflight.add_argument("--output")
    preflight.set_defaults(func=cmd_preflight)
    apply = sub.add_parser("apply", help="复核漂移后执行一次写入并定向回读")
    apply.add_argument("--preflight", required=True)
    apply.add_argument("--receipt")
    apply.set_defaults(func=cmd_apply)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        return int(args.func(args))
    except (core.AdapterError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"schema": SCHEMA, "result": "blocked",
                          "error": core.scrub(str(exc))}, ensure_ascii=False, indent=2),
              file=sys.stderr)
        return 69


if __name__ == "__main__":
    raise SystemExit(main())
