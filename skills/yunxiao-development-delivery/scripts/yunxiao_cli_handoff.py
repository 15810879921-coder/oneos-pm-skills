#!/usr/bin/env python3
"""Read-only, official-CLI handoff preflight before formal development writes."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import handoff_gate as hg
import yunxiao_cli_gateway as gateway
import yunxiao_cli_runtime as core


def verify_task_binding(executable: str, task: dict, scope: dict) -> None:
    space = task.get("space") or {}
    project_id = str((space.get("id") if isinstance(space, dict) else "") or
                     task.get("spaceIdentifier") or task.get("spaceId") or task.get("projectId") or "")
    if project_id != scope["projectId"]:
        raise core.AdapterError("开发任务项目归属与本次交棒不一致或无法回读。")
    parent = task.get("parent") or {}
    parent_id = str(task.get("parentId") or (parent.get("id") if isinstance(parent, dict) else "") or "")
    if not parent_id:
        values = core.unwrap(gateway.execute_read(executable, {
            "operation": "projex-list-workitem-relation-records",
            "args": ["--id", str(task["id"]), "--relation-type", "PARENT"]}))
        if not isinstance(values, list):
            raise core.AdapterError("开发任务父交付归属查询结构异常。")
        ids = {str(row.get("resourceId") or "") for row in values if isinstance(row, dict)} - {""}
        if len(ids) != 1:
            raise core.AdapterError("开发任务无法唯一绑定父交付；须补齐真实归属，不能猜测。")
        parent_id = next(iter(ids))
    if parent_id != scope["deliveryId"]:
        raise core.AdapterError("开发任务父交付归属与本次交棒不一致。")


def verify_start(executable: str, bundle: dict, task_id: str) -> dict:
    try:
        hg.validate_bundle(bundle, "development")
        hg.validate_receipt(bundle["developmentReceipt"], bundle["manifest"], "development", task_id)
        def read(item_id):
            value = core.unwrap(gateway.execute_read(executable, {
                "operation": "projex-get-workitem", "args": ["--id", item_id]}))
            if not isinstance(value, dict) or str(value.get("id") or "") != item_id:
                raise ValueError("官方开发交棒工作项无法唯一回读")
            return value
        task = read(task_id)
        verify_task_binding(executable, task, bundle["manifest"]["scope"])
        hg.verify_live_bundle(bundle, "development", read)
        hashes = hg.verify_documents(bundle["manifest"])
    except (ValueError, OSError) as error:
        raise core.AdapterError(str(error)) from error
    return {
        "schemaVersion": "oneos.handoff-preflight/v1", "verified": True,
        "checkedAt": core.now_utc(), "stage": "development",
        "scope": bundle["manifest"]["scope"], "developmentTaskId": task_id,
        "handoffSha256": bundle["manifest"]["sha256"],
        "bundleSha256": hg.seal(bundle)["sha256"], "documentHashes": hashes,
        "taskReadbackSha256": gateway.stable_hash(task),
        "boundary": "只读时点校验，不创建任务或分支、不修改状态、不证明真人批准；来源变化须重跑",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("verify",))
    parser.add_argument("--bundle", required=True)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()
    try:
        value = json.loads(Path(args.bundle).read_text(encoding="utf-8-sig"))
        gateway.assert_no_secrets(value)
        executable = core.find_aliyun()
        core.require_auth_env()
        result = verify_start(executable, value, args.task_id)
        if args.output:
            gateway.write_json(Path(args.output), result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (core.AdapterError, ValueError, OSError) as error:
        print(json.dumps({"verified": False, "error": core.scrub(str(error))}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
