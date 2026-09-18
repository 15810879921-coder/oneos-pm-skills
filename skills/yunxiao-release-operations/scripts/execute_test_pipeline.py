#!/usr/bin/env python3
"""Prepare, execute, and monitor one verified Yunxiao test pipeline.

Discovery remains read-only.  The only write in this command is the single
``flow-create-pipeline-run`` action submitted through ``yunxiao_cli_gateway``
after the candidate receipt, pipeline-definition drift guard, and idempotency
checks pass.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
from pathlib import Path
from typing import Any, Callable

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import discover_test_pipelines as discovery
import yunxiao_cli_runtime as core


def _load_local_gateway():
    """Avoid test-suite collisions with the development gateway module name."""
    expected = SCRIPT_DIR / "yunxiao_cli_gateway.py"
    cached = sys.modules.get("yunxiao_cli_gateway")
    if cached is not None and Path(getattr(cached, "__file__", "")).resolve() == expected:
        return cached
    spec = importlib.util.spec_from_file_location("_oneos_release_gateway", expected)
    if spec is None or spec.loader is None:
        raise ImportError(f"无法加载{expected}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gateway = _load_local_gateway()


PLAN_SCHEMA = gateway.PLAN_SCHEMA
RUN_SCHEMA = "oneos.test-pipeline-execution/v1"
TERMINAL_SUCCESS = {"success", "succeeded", "successful", "passed", "pass", "成功", "已成功"}
TERMINAL_FAILURE = {
    "failed", "failure", "error", "canceled", "cancelled", "timeout", "timedout",
    "失败", "已取消", "超时", "异常",
}


def text(value: Any) -> str:
    return "" if value is None or isinstance(value, (dict, list)) else str(value).strip()


def run_status(value: Any) -> str:
    if not isinstance(value, dict):
        return ""
    for key in ("status", "result", "state", "executionStatus", "pipelineRunStatus"):
        candidate = text(value.get(key)).lower()
        if candidate:
            return candidate
    for child in value.values():
        if isinstance(child, dict):
            candidate = run_status(child)
            if candidate:
                return candidate
    return ""


def walk(value: Any, path: str = ""):
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            yield child_path, key, child
            yield from walk(child, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            child_path = f"{path}[{index}]"
            yield child_path, str(index), child
            yield from walk(child, child_path)


def extract_run_id(value: Any) -> str:
    if isinstance(value, dict):
        for key in ("pipelineRunId", "runId", "executionId", "id"):
            candidate = text(value.get(key))
            if candidate:
                return candidate
        for child in value.values():
            candidate = extract_run_id(child)
            if candidate:
                return candidate
    elif isinstance(value, list):
        for child in value:
            candidate = extract_run_id(child)
            if candidate:
                return candidate
    return ""


def load_json(path: str) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise core.AdapterError(f"{path}必须是JSON对象。")
    return value


def validate_candidates(value: dict[str, Any], pipeline: str | None = None) -> dict[str, Any]:
    if value.get("schemaVersion") != discovery.SCHEMA:
        raise core.AdapterError("候选回执schema不是oneos.test-pipeline-candidates/v1。")
    if value.get("result") != "ready" or value.get("candidateCount") != 1:
        raise core.AdapterError("候选回执不是唯一READY结果，禁止启动测试流水线。")
    candidates = value.get("candidates")
    if not isinstance(candidates, list) or len(candidates) != 1 or not isinstance(candidates[0], dict):
        raise core.AdapterError("候选回执缺少唯一候选。")
    candidate = candidates[0]
    pipeline_id = text(candidate.get("pipelineId"))
    if not pipeline_id:
        raise core.AdapterError("候选流水线缺pipelineId。")
    if pipeline and pipeline not in {pipeline_id, text(candidate.get("pipelineName"))}:
        raise core.AdapterError("用户指定流水线未命中已结构匹配的候选。")
    if (candidate.get("baseline") or {}).get("status") != "verified":
        raise core.AdapterError("候选流水线缺已核验的成功部署基线。")
    if (candidate.get("pendingChanges") or {}).get("status") != "calculated":
        raise core.AdapterError("候选流水线缺完整待部署变更计算。")
    return value


def build_plan(candidates: dict[str, Any]) -> dict[str, Any]:
    validate_candidates(candidates)
    candidate = candidates["candidates"][0]
    pipeline_id = text(candidate["pipelineId"])
    pending = candidate.get("pendingChanges", {}).get("components", [])
    current_heads = [text(item.get("currentHead")) for item in pending if isinstance(item, dict)]
    identity = f"{candidates.get('scopeHash')}:{pipeline_id}:{','.join(current_heads)}"
    return {
        "schema": PLAN_SCHEMA,
        "label": f"执行测试流水线：{text(candidate.get('pipelineName')) or pipeline_id}",
        "authority": "execute",
        "idempotencyKey": f"test-pipeline:{gateway.stable_hash(identity)}",
        "releaseGateStage": "test-pipeline",
        "testPipelineEvidence": candidates,
        "guards": [{
            "operation": "flow-get-pipeline",
            "args": ["--pipeline-id", pipeline_id],
        }],
        "actions": [{
            "operation": "flow-create-pipeline-run",
            "args": ["--pipeline-id", pipeline_id],
        }],
        "verifications": [{
            "operation": "flow-get-pipeline-run",
            "args": ["--pipeline-id", pipeline_id,
                     "--pipeline-run-id", "${action.0.pipelineRunId}"],
        }],
    }


def read_run(executable: str, pipeline_id: str, run_id: str) -> dict[str, Any]:
    value = core.unwrap(core.run_devops(executable, [
        "flow-get-pipeline-run", "--pipeline-id", pipeline_id,
        "--pipeline-run-id", run_id,
    ], timeout=120))
    return value if isinstance(value, dict) else {"raw": value}


def failure_evidence(detail: dict[str, Any]) -> dict[str, Any]:
    failed_paths: list[str] = []
    log_paths: list[str] = []
    for path, key, value in walk(detail):
        lowered = str(key).lower()
        candidate = text(value).lower()
        if lowered in {"status", "result", "state", "executionstatus"} and candidate in TERMINAL_FAILURE:
            failed_paths.append(path)
        if lowered in {"log", "logcontent", "logurl", "consolelog", "message"} and text(value):
            log_paths.append(path)
    return {
        "firstFailedPath": failed_paths[0] if failed_paths else None,
        "logEvidencePaths": log_paths[:5],
        "logRead": bool(log_paths),
        "note": "仅记录官方执行回读中可见的失败/日志字段；未发现日志字段时不推断根因。",
    }


def monitor(executable: str, pipeline_id: str, run_id: str,
            reader: Callable[[dict[str, Any]], Any] | None = None,
            timeout_seconds: int = 1800, interval_seconds: int = 15,
            emit: Callable[[dict[str, Any]], None] | None = None) -> dict[str, Any]:
    if not run_id:
        raise core.AdapterError("缺少pipelineRunId，不能跟踪测试流水线。")
    if timeout_seconds < 1 or timeout_seconds > 86400:
        raise core.AdapterError("timeout-seconds必须在1到86400之间。")
    if interval_seconds < 1 or interval_seconds > 60:
        raise core.AdapterError("poll-seconds必须在1到60之间。")
    reader = reader or (lambda call: core.run_devops(executable, [call["operation"], *call["args"]], timeout=120))
    deadline = time.monotonic() + timeout_seconds
    while True:
        raw = reader({"operation": "flow-get-pipeline-run", "args": [
            "--pipeline-id", pipeline_id, "--pipeline-run-id", run_id,
        ]})
        detail = core.unwrap(raw)
        if not isinstance(detail, dict):
            detail = {"raw": detail}
        status = run_status(detail)
        result = {"schema": RUN_SCHEMA, "pipelineId": pipeline_id,
                  "pipelineRunId": run_id, "status": status or "unknown",
                  "readAt": core.now_utc()}
        if status in TERMINAL_SUCCESS:
            result["result"] = "succeeded"
            if emit:
                emit(result)
            return result
        if status in TERMINAL_FAILURE:
            result["result"] = "failed"
            result["failureEvidence"] = failure_evidence(detail)
            if emit:
                emit(result)
            return result
        if time.monotonic() >= deadline:
            result["result"] = "timeout-waiting"
            result["note"] = "流水线仍未进入终态；保留执行ID，未将其判定为失败。"
            if emit:
                emit(result)
            return result
        if emit:
            emit(result)
        time.sleep(interval_seconds)


def write_json(path: str | None, value: dict[str, Any]) -> None:
    if not path:
        return
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def cmd_prepare(args: argparse.Namespace) -> int:
    candidates = load_json(args.candidates)
    validate_candidates(candidates, args.pipeline)
    plan = build_plan(candidates)
    write_json(args.output, plan)
    print(json.dumps({"result": "ready", "plan": args.output, "pipelineId": plan["actions"][0]["args"][1],
                      "idempotencyKey": plan["idempotencyKey"]}, ensure_ascii=False, indent=2))
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    if bool(args.scope) == bool(args.candidates):
        raise core.AdapterError("run必须二选一提供--scope或--candidates。")
    executable = core.find_aliyun()
    core.require_auth_env()
    if args.scope:
        scope = load_json(args.scope)
        result = discovery.discover(scope, lambda call: gateway.execute_read(executable, call), args.pipeline)
        if args.candidates:
            raise core.AdapterError("内部参数冲突。")
    else:
        result = load_json(args.candidates)
        validate_candidates(result, args.pipeline)
    validate_candidates(result, args.pipeline)
    plan = build_plan(result)
    output_dir = core.output_dir()
    plan_path = Path(args.plan) if args.plan else output_dir / f"test-pipeline-plan-{plan['idempotencyKey'][-16:]}.json"
    preflight_path = Path(args.preflight) if args.preflight else output_dir / f"test-pipeline-preflight-{plan['idempotencyKey'][-16:]}.json"
    receipt_path = Path(args.receipt) if args.receipt else output_dir / f"test-pipeline-receipt-{plan['idempotencyKey'][-16:]}.json"
    write_json(str(plan_path), plan)
    gateway.cmd_preflight(argparse.Namespace(plan=str(plan_path), output=str(preflight_path)))
    gateway.cmd_apply(argparse.Namespace(preflight=str(preflight_path), receipt=str(receipt_path)))
    applied = load_json(str(receipt_path))
    run_id = extract_run_id(applied.get("actions", [{}])[0].get("result"))
    pipeline_id = text(plan["actions"][0]["args"][1])
    if not args.no_monitor:
        monitor(pipeline_id=pipeline_id, run_id=run_id, executable=executable,
                timeout_seconds=args.timeout_seconds, interval_seconds=args.poll_seconds,
                emit=lambda item: print(json.dumps(item, ensure_ascii=False)))
    print(json.dumps({"result": "started", "pipelineId": pipeline_id,
                      "pipelineRunId": run_id, "receipt": str(receipt_path)},
                     ensure_ascii=False, indent=2))
    return 0


def cmd_monitor(args: argparse.Namespace) -> int:
    executable = core.find_aliyun()
    core.require_auth_env()
    result = monitor(executable, args.pipeline_id, args.pipeline_run_id,
                     timeout_seconds=args.timeout_seconds, interval_seconds=args.poll_seconds,
                     emit=lambda item: print(json.dumps(item, ensure_ascii=False)))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("result") in {"succeeded", "timeout-waiting"} else 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prepare = sub.add_parser("prepare", help="将唯一READY候选转换为测试流水线事务计划")
    prepare.add_argument("--candidates", required=True)
    prepare.add_argument("--pipeline")
    prepare.add_argument("--output", required=True)
    prepare.set_defaults(func=cmd_prepare)
    run = sub.add_parser("run", help="发现候选、预检、执行并跟踪一次测试流水线")
    run.add_argument("--scope")
    run.add_argument("--candidates")
    run.add_argument("--pipeline")
    run.add_argument("--plan")
    run.add_argument("--preflight")
    run.add_argument("--receipt")
    run.add_argument("--no-monitor", action="store_true")
    run.add_argument("--timeout-seconds", type=int, default=1800)
    run.add_argument("--poll-seconds", type=int, default=15)
    run.set_defaults(func=cmd_run)
    monitor_parser = sub.add_parser("monitor", help="跟踪已启动的测试流水线到终态")
    monitor_parser.add_argument("--pipeline-id", required=True)
    monitor_parser.add_argument("--pipeline-run-id", required=True)
    monitor_parser.add_argument("--timeout-seconds", type=int, default=1800)
    monitor_parser.add_argument("--poll-seconds", type=int, default=15)
    monitor_parser.set_defaults(func=cmd_monitor)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        return int(args.func(args))
    except (core.AdapterError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"schema": RUN_SCHEMA, "result": "blocked", "error": core.scrub(str(exc))},
                         ensure_ascii=False, indent=2), file=sys.stderr)
        return 69


if __name__ == "__main__":
    raise SystemExit(main())
