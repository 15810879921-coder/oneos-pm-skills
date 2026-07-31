#!/usr/bin/env python
"""校验发布回调HMAC、时间窗与业务锚点；不连接或修改云效。"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import sys
import time
from pathlib import Path
from typing import Any


def read_body(path: str) -> bytes:
    return sys.stdin.buffer.read() if path == "-" else Path(path).read_bytes()


def normalized_signature(value: str) -> str:
    text = value.strip()
    return text.split("=", 1)[1] if text.lower().startswith("sha256=") else text


def main() -> None:
    parser = argparse.ArgumentParser(description="校验云效发布回调")
    parser.add_argument("--body", required=True, help="原始JSON Body文件；- 表示stdin")
    parser.add_argument("--signature", required=True)
    parser.add_argument("--timestamp", required=True, type=int)
    parser.add_argument("--release-task-id", required=True)
    parser.add_argument("--execution-id", required=True)
    parser.add_argument("--environment", default="prod")
    parser.add_argument("--scope", required=True, help="逗号分隔的需求编号")
    parser.add_argument("--idempotency-key", required=True)
    parser.add_argument("--seen-idempotency", action="append", default=[])
    parser.add_argument("--max-age-seconds", type=int, default=300)
    parser.add_argument(
        "--secret-env", default="YUNXIAO_RELEASE_WEBHOOK_SECRET"
    )
    args = parser.parse_args()

    errors: list[str] = []
    secret = os.environ.get(args.secret_env)
    if not secret:
        errors.append(f"环境变量{args.secret_env}未设置")
    if args.max_age_seconds <= 0:
        errors.append("max-age-seconds必须大于0")
    now = int(time.time())
    if abs(now - args.timestamp) > args.max_age_seconds:
        errors.append("时间戳过期或超前")

    try:
        body = read_body(args.body)
        payload = json.loads(body.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("Body根节点不是对象")
    except (OSError, UnicodeDecodeError, ValueError, json.JSONDecodeError) as error:
        payload = {}
        body = b""
        errors.append(f"Body无效：{error}")

    signature_valid = False
    if secret and body:
        signed = str(args.timestamp).encode("ascii") + b"." + body
        expected = hmac.new(secret.encode("utf-8"), signed, hashlib.sha256).hexdigest()
        signature_valid = hmac.compare_digest(
            expected, normalized_signature(args.signature)
        )
        if not signature_valid:
            errors.append("HMAC签名不匹配")

    expected_scope = sorted(
        {item.strip() for item in args.scope.split(",") if item.strip()}
    )
    actual_scope = sorted(
        {str(item).strip() for item in payload.get("scope", []) if str(item).strip()}
    ) if isinstance(payload.get("scope"), list) else []
    checks = {
        "releaseTaskId": args.release_task_id,
        "executionId": args.execution_id,
        "environment": args.environment,
        "idempotencyKey": args.idempotency_key,
    }
    for key, expected_value in checks.items():
        if str(payload.get(key) or "") != expected_value:
            errors.append(f"{key}不匹配")
    if actual_scope != expected_scope:
        errors.append("scope不匹配")
    if args.idempotency_key in set(args.seen_idempotency):
        errors.append("幂等键已处理，疑似重放")

    result: dict[str, Any] = {
        "ok": not errors,
        "signatureValid": signature_valid,
        "timestampValid": not any("时间戳" in error for error in errors),
        "anchorsValid": not any("不匹配" in error for error in errors),
        "replayValid": not any("重放" in error for error in errors),
        "errors": errors,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["ok"] else 3)


if __name__ == "__main__":
    main()
