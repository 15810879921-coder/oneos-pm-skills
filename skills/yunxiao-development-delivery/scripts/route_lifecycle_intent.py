#!/usr/bin/env python3
"""Normalize natural-language development intent without selecting or mutating a work item."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


SCHEMA = "oneos.development-intent/v1"

ROUTES: list[tuple[str, tuple[str, ...]]] = [
    ("cleanup", ("清理分支", "删掉分支", "删除分支")),
    ("complete_bug", ("完成修复", "bug修完", "缺陷修完", "可以复测")),
    ("start_bug", ("开始修复", "开始处理bug", "开始处理缺陷")),
    ("fix_bug", ("修复bug", "修复缺陷", "把这个问题修掉", "解决这个bug")),
    ("complete_development", ("完成开发", "开发完成", "交给测试", "做完了")),
    ("submit", ("提交代码", "推送代码", "提mr", "创建mr", "把代码提交")),
    ("test_deploy", ("上测试", "部署测试", "先测一下", "测试环境看看")),
    ("start_development", ("开始开发", "开始做", "进入开发")),
    ("implement", ("实现", "开发", "修改代码", "优化", "改一下", "改造", "重构", "修复")),
]

DISCUSSION = ("方案", "分析", "模拟", "是否", "能不能", "为什么", "有什么缺口", "怎么设计")
ACTION_AUTHORITY = ("帮我", "请", "直接", "现在", "开始", "执行", "继续", "改吧", "修吧", "做吧")


def _load_context(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("context必须是JSON对象")
    return value


def route(text: str, context: dict[str, Any]) -> dict[str, Any]:
    normalized = re.sub(r"\s+", "", text).lower()
    explicit_action = any(keyword in normalized for _, words in ROUTES for keyword in words)
    asks_discussion = any(word in normalized for word in DISCUSSION)
    has_action_authority = any(word in normalized for word in ACTION_AUTHORITY)
    is_discussion = asks_discussion and not has_action_authority
    action = "audit" if is_discussion else "unknown"
    if not is_discussion:
        for candidate, words in ROUTES:
            if any(word in normalized for word in words):
                action = candidate
                break

    work_item_id = str(context.get("workItemId") or "").strip()
    delivery_unit_id = str(context.get("deliveryUnitId") or "").strip()
    unique_mapping = context.get("mappingUnique") is True and bool(work_item_id)
    mapping_mode = "formal" if unique_mapping else "temporary"
    if action in {"audit", "unknown", "cleanup"}:
        mapping_mode = "not_applicable" if action in {"audit", "unknown"} else mapping_mode

    has_temporary_mapping = bool(delivery_unit_id) and context.get("temporaryLedgerVerified") is True
    requires_resolution = action in {
        "submit", "complete_development", "complete_bug", "test_deploy", "cleanup"
    } and not unique_mapping and not has_temporary_mapping
    return {
        "schemaVersion": SCHEMA,
        "originalText": text,
        "action": action,
        "mappingMode": mapping_mode,
        "workItemId": work_item_id or None,
        "deliveryUnitId": delivery_unit_id or None,
        "requiresItemResolution": requires_resolution,
        "mayCreateTempBranch": action in {"start_development", "implement", "fix_bug"} and not unique_mapping,
        "mayWriteProduction": False,
        "reason": "讨论/查询保持只读" if action == "audit" else "仅完成意图归一，正式写入仍走原门禁",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="把自然语言开发请求归一为内部生命周期动作")
    parser.add_argument("--text", required=True)
    parser.add_argument("--context", type=Path)
    args = parser.parse_args()
    try:
        result = route(args.text, _load_context(args.context))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "blocked", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
