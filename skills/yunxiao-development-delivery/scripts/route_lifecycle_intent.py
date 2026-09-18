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
WORK_ITEM_PATTERN = re.compile(r"(?<![A-Z0-9-])([A-Z][A-Z0-9_]*-\d+)(?![A-Z0-9-])", re.IGNORECASE)

ROUTES: list[tuple[str, tuple[str, ...]]] = [
    ("cleanup", ("清理分支", "删掉分支", "删除分支")),
    ("complete_bug", ("完成修复", "bug修完", "缺陷修完", "可以复测")),
    ("start_bug", ("开始修复", "开始处理bug", "开始处理缺陷")),
    ("accept_test_bug_repair", ("处理测试修复请求", "接收测试修复", "处理测试提的bug", "测试缺陷修复")),
    ("fix_bug", ("修复bug", "修复缺陷", "把这个问题修掉", "解决这个bug")),
    ("complete_development", ("完成开发", "开发完成", "交给测试", "做完了")),
    ("submit", ("提交代码", "代码提交", "提交到远端", "推送代码", "推到远端", "提mr", "创建mr", "把代码提交")),
    ("test_deploy", ("上测试", "部署测试", "先测一下", "测试环境看看")),
    ("start_development", ("开始开发", "开始做", "进入开发")),
    ("implement", ("实现", "开发", "做完", "修改代码", "优化", "改一下", "改造", "重构", "修复")),
]

DISCUSSION = (
    "方案", "分析", "模拟", "是否", "是不是", "能不能", "为什么", "有什么缺口", "怎么设计",
    "核对", "查看", "看看", "看下", "检查", "查一下", "查状态", "怎么回事", "处理逻辑",
)
ACTION_AUTHORITY = ("直接执行", "执行修改", "核对后执行", "检查后执行", "改吧", "修吧", "做吧")
TEST_PIPELINE_WORDS = ("执行测试流水线", "跑测试流水线", "部署测试", "上测试", "交给测试", "交测")
MERGE_ONLY_WORDS = ("仅合并", "只合并", "只完成代码合并", "不执行测试", "不跑测试", "不部署测试", "不部署")


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
    asks_discussion = any(word in normalized for word in DISCUSSION) \
        or bool(re.search(r"(?:吗|呢|么)[？?]?$", normalized)) \
        or normalized.startswith(("怎么", "如何"))
    has_action_authority = any(word in normalized for word in ACTION_AUTHORITY)
    is_discussion = asks_discussion and not has_action_authority
    action = "audit" if is_discussion else "unknown"
    if not is_discussion:
        completion_phrase = re.search(
            r"(?:完成|做完).*?(?:开发|交(?:给)?测试)|开发.*?(?:完成|做完)|交(?:给)?测试",
            normalized,
        )
        if completion_phrase:
            action = "complete_development"
        else:
            for candidate, words in ROUTES:
                if any(word in normalized for word in words):
                    action = candidate
                    break

    work_item_id = str(context.get("workItemId") or "").strip()
    text_serials = list(dict.fromkeys(
        match.group(1).upper() for match in WORK_ITEM_PATTERN.finditer(text)
    ))
    context_serial = str(context.get("workItemSerial") or "").strip().upper()
    work_item_serial = text_serials[0] if len(text_serials) == 1 else context_serial or None
    delivery_unit_id = str(context.get("deliveryUnitId") or "").strip()
    unique_mapping = context.get("mappingUnique") is True and bool(work_item_id)
    mapping_mode = "formal" if unique_mapping else "temporary"
    if action in {"audit", "unknown", "cleanup"}:
        mapping_mode = "not_applicable" if action in {"audit", "unknown"} else mapping_mode

    has_temporary_mapping = bool(delivery_unit_id) and context.get("temporaryLedgerVerified") is True
    requires_resolution = action in {
        "submit", "complete_development", "complete_bug", "accept_test_bug_repair", "test_deploy", "cleanup"
    } and not unique_mapping and not has_temporary_mapping
    canonical_command = None
    if action == "complete_development" and work_item_serial and len(text_serials) <= 1:
        canonical_command = f"完成开发:任务={work_item_serial}"
    elif action == "implement" and work_item_serial and len(text_serials) <= 1:
        canonical_command = f"开发任务:任务={work_item_serial}"
    if any(word in normalized for word in MERGE_ONLY_WORDS):
        test_delivery_mode = "merge_only"
    elif any(word in normalized for word in TEST_PIPELINE_WORDS):
        test_delivery_mode = "execute"
    else:
        test_delivery_mode = "ask"
    return {
        "schemaVersion": SCHEMA,
        "originalText": text,
        "action": action,
        "mappingMode": mapping_mode,
        "workItemId": work_item_id or None,
        "workItemSerial": work_item_serial,
        "canonicalCommand": canonical_command,
        "testDeliveryMode": test_delivery_mode,
        "testDeliveryReason": {
            "execute": "用户明确要求交测或执行测试流水线",
            "merge_only": "用户明确要求只完成代码合并或不部署",
            "ask": "用户未明确选择测试部署路径",
        }[test_delivery_mode],
        "serialCandidates": text_serials,
        "autoCompleteOnSuccess": action == "implement" and bool(work_item_serial or unique_mapping),
        "assessCompletionAfterSubmit": action == "submit",
        "deliveryUnitId": delivery_unit_id or None,
        "requiresItemResolution": requires_resolution,
        "mayCreateTempBranch": action in {"start_development", "implement", "fix_bug", "accept_test_bug_repair"} and not unique_mapping,
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
