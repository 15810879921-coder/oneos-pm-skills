#!/usr/bin/env python3
"""Classify whether a successful code submission may continue to development completion."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


SCHEMA = "oneos.development-completion-assessment/v1"
RECOVERY_STEPS = {"formal_handoff", "code_mapping", "managed_test_scope"}


def classify(value: dict[str, Any]) -> dict[str, Any]:
    if value.get("schemaVersion") != SCHEMA:
        raise ValueError(f"schemaVersion必须为{SCHEMA}")

    allowed = {
        "taskResolution": {"unique", "none", "multiple"},
        "scopeMatch": {"confirmed", "likely", "conflict"},
        "implementation": {"complete", "likely", "incomplete"},
        "validation": {"passed", "unknown", "failed"},
        "remoteDelivery": {"verified", "recoverable", "pending", "failed"},
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
    recovery_needed = value.get("recoveryNeeded", [])
    if not isinstance(recovery_needed, list) or any(item not in RECOVERY_STEPS for item in recovery_needed):
        raise ValueError(f"recoveryNeeded只能包含{sorted(RECOVERY_STEPS)}")
    if len(recovery_needed) != len(set(recovery_needed)):
        raise ValueError("recoveryNeeded不得包含重复项")
    warnings = []
    if "formal_handoff" in recovery_needed:
        warnings.append("产品交接记录待产品补齐；不阻断完成开发或创建测试任务。")
        recovery_needed = [item for item in recovery_needed if item != "formal_handoff"]
    candidate_code_refs = value.get("candidateCodeRefs", [])
    if not isinstance(candidate_code_refs, list) or any(not str(item).strip() for item in candidate_code_refs):
        raise ValueError("candidateCodeRefs必须是非空文本数组或空数组")
    if len(candidate_code_refs) != len(set(candidate_code_refs)):
        raise ValueError("candidateCodeRefs不得包含重复项")
    if value["remoteDelivery"] == "recoverable":
        if "code_mapping" not in recovery_needed or not candidate_code_refs:
            raise ValueError("remoteDelivery=recoverable必须包含code_mapping和非空candidateCodeRefs")
    elif "code_mapping" in recovery_needed:
        raise ValueError("code_mapping恢复只适用于remoteDelivery=recoverable")

    hard_reasons: list[str] = []
    if value["taskResolution"] != "unique":
        hard_reasons.append("开发任务未唯一定位")
    if value["scopeMatch"] == "conflict":
        hard_reasons.append("代码范围与开发任务冲突")
    if value["implementation"] == "incomplete":
        hard_reasons.append("实现仍不完整")
    if value["validation"] == "failed":
        hard_reasons.append("开发验证失败")
    if value["remoteDelivery"] in {"pending", "failed"}:
        hard_reasons.append("远端交付版本未完成官方回读")
    if value["remainingTaskChanges"] is True:
        hard_reasons.append("仍有属于当前任务的未提交改动")
    hard_reasons.extend(str(item).strip() for item in blockers)

    if hard_reasons:
        decision = "incomplete"
        next_action = "stop_after_submit"
        reasons = hard_reasons
    elif recovery_needed:
        decision = "recovery_required"
        next_action = "recover_then_complete"
        labels = {
            "formal_handoff": "正式交棒证据需要补录并重新校验",
            "code_mapping": "历史分支、MR或提交需要确认归属并补录代码映射",
            "managed_test_scope": "既有测试任务需要补齐受管测试范围",
        }
        reasons = [labels[item] for item in recovery_needed]
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
        "recoveryNeeded": recovery_needed,
        "warnings": warnings,
        "candidateCodeRefs": candidate_code_refs,
        "reasons": reasons,
        "prompt": None,
    }
    if decision == "likely":
        task = str(value.get("developmentTask") or "当前开发任务")
        result["prompt"] = f"代码已提交到远端，检测到{task}可能已经完成。是否继续执行完成开发并交测试？"
    elif decision == "recovery_required" and "code_mapping" in recovery_needed:
        task = str(value.get("developmentTask") or "当前开发任务")
        result["prompt"] = (
            f"已找到{task}的{len(candidate_code_refs)}条历史代码候选，但任务尚未记录其归属。"
            "请确认展示的精确MR/提交集合；确认后补录代码映射，再继续完成开发。"
        )
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
