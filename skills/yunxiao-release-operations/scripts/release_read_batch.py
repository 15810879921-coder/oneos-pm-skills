#!/usr/bin/env python3
"""Run independent official Yunxiao reads concurrently and preserve input order.

This helper never performs writes. Callers remain responsible for selecting the
exact release scope and for keeping dependent reads sequential.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sys
import time
from typing import Any, Callable

import yunxiao_cli_gateway as gateway

SCHEMA = "oneos.release-read-batch/v1"


def official_reader() -> Callable[[dict[str, Any]], Any]:
    executable = gateway.core.find_aliyun()
    gateway.core.require_auth_env()

    def read(call: dict[str, Any]) -> Any:
        return gateway.core.unwrap(gateway.execute_read(executable, call))
    return read


def run_batch(value: dict[str, Any], reader=None, workers: int = 4) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("schemaVersion") != SCHEMA:
        raise ValueError(f"批量读取schemaVersion必须为{SCHEMA}")
    requests = value.get("requests")
    if not isinstance(requests, list) or not requests or len(requests) > 32:
        raise ValueError("批量读取requests必须为1到32项")
    if not isinstance(workers, int) or not 1 <= workers <= 8:
        raise ValueError("批量读取workers必须为1到8")
    ids = [row.get("id") for row in requests if isinstance(row, dict)]
    if len(ids) != len(requests) or any(not isinstance(item, str) or not item for item in ids) or len(set(ids)) != len(ids):
        raise ValueError("批量读取请求ID必须完整且唯一")
    calls = []
    for row in requests:
        call = gateway.validate_call({
            "operation": row.get("operation"), "args": row.get("args", []),
        }, write=False)
        calls.append(call)
    if reader is None:
        reader = official_reader()
    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=min(workers, len(calls))) as executor:
        futures = [executor.submit(reader, call) for call in calls]
        results = []
        for request_id, call, future in zip(ids, calls, futures):
            try:
                result = future.result()
            except Exception as exc:  # preserve the exact request boundary, never retry implicitly
                raise ValueError(f"只读请求{request_id}失败：{exc}") from exc
            results.append({"id": request_id, "call": call, "value": result,
                            "valueHash": gateway.stable_hash(result)})
    return {"schemaVersion": SCHEMA, "status": "passed", "requestCount": len(results),
            "workers": min(workers, len(calls)),
            "elapsedMs": round((time.perf_counter() - started) * 1000),
            "results": results}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    try:
        value = json.loads(args.input.read_text(encoding="utf-8-sig"))
        result = run_batch(value, workers=args.workers)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.output.with_suffix(args.output.suffix + ".tmp")
        temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(args.output)
        print(json.dumps({"status": "passed", "requestCount": result["requestCount"],
                          "elapsedMs": result["elapsedMs"], "output": str(args.output)},
                         ensure_ascii=False))
        return 0
    except (ValueError, TypeError, OSError, json.JSONDecodeError, gateway.core.AdapterError) as exc:
        print(json.dumps({"status": "blocked", "error": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    sys.exit(main())
