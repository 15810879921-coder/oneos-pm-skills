#!/usr/bin/env python3
"""Classify whether a successful code submission may continue to development completion."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


SCHEMA = "oneos.development-completion-assessment/v1"


def classify(value: dict[str, Any]) -> dict[str, Any]:
    if value.get("schemaVersion") != SCHEMA:
        raise ValueError(f"schemaVersion必须为{SCHEMA}")

    allowed = {
        "taskResolution": {"unique", "none", "multiple"},
        "scopeMatch": {"confirmed", "likely", "conflict"},
        "implementation": {"complete", "likely", "incomplete"},
        "validation": {"passed", "unknown", "failed"},
        "remoteDelivery": {"verified", "pending", "failed"},
    }
    for field, choices in allowed.items():
        if value.get(field) not in choices:
            raise ValueError(f"{field}必须是{sorted(choices)}之一")
    remaining_changes = value.get("remainingTaskChanges")
    if remaining_changes is not True and remaining_changes is not False \
            and remaining_changes is not None:
        raise ValueError("remainingTaskChanges必须为true、false或null")
    blockers = value.get("knownBlockers")
    if not isinstance(blockers, list) or any(not str(item).strip() for item in blockers):
        raise ValueError("knownBlockers必须是非空文本数组或空数组")

    hard_reasons: list[str] = []
    if value["taskResolution"] != "unique":
        hard_reasons.append("开发任务未唯一定位")
    if value["scopeMatch"] == "conflict":
        hard_reasons.append("代码范围与开发任务冲突")
    if value["implementation"] == "incomplete":
        hard_reasons.append("实现仍不完整")
    if value["validation"] == "failed":
        hard_reasons.append("开发验证失败")
    if value["remoteDelivery"] != "verified":
        hard_reasons.append("远端交付版本未完成官方回读")
    if value["remainingTaskChanges"] is True:
        hard_reasons.append("仍有属于当前任务的未提交改动")
    hard_reasons.extend(str(item).strip() for item in blockers)

    if hard_reasons:
        decision = "incomplete"
        next_action = "stop_after_submit"
        reasons = hard_reasons
    else:
        uncertain: list[str] = []
        if value["scopeMatch"] == "likely":
            uncertain.append("任务范围匹配仍需业务确认")
        if value["implementation"] == "likely":
            uncertain.append("实现覆盖度只能判定为可能完整")
        if value["validation"] == "unknown":
            uncertain.append("完成节点仍需重新执行开发验证")
        if value["remainingTaskChanges"] is None:
            uncertain.append("剩余任务改动无法完全确认")
        if uncertain:
            decision = "likely"
            next_action = "ask_once"
            reasons = uncertain
        else:
            decision = "confirmed"
            next_action = "auto_complete"
            reasons = ["任务、范围、实现、验证、远端版本和剩余改动均已确认"]

    result = {
        "schemaVersion": SCHEMA,
        "decision": decision,
        "nextAction": next_action,
        "developmentTask": value.get("developmentTask"),
        "remoteVersion": value.get("remoteVersion"),
        "reasons": reasons,
        "prompt": None,
    }
    if decision == "likely":
        task = str(value.get("developmentTask") or "当前开发任务")
        result["prompt"] = f"代码已提交到远端，检测到{task}可能已经完成。是否继续执行完成开发并交测试？"
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        value = json.loads(args.input.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError("输入必须是JSON对象")
        result = classify(value)
        text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(text, encoding="utf-8")
        print(text, end="")
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(json.dumps({"status": "blocked", "error": str(error)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    sys.exit(main())
