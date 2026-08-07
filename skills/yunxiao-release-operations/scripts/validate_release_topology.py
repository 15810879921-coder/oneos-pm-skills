#!/usr/bin/env python3
"""Validate a frozen PC-single or shared-service-dual release topology."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def fail(message: str) -> None:
    raise ValueError(message)


def required_string(value: Any, label: str) -> str:
    text = str(value or "").strip()
    if not text:
        fail(f"缺少{label}")
    return text


def validate_component(component: dict[str, Any], version: str) -> dict[str, Any]:
    name = required_string(component.get("name"), "组件名称")
    required = component.get("deployRequired")
    if not isinstance(required, bool):
        fail(f"组件{name}的deployRequired必须为布尔值")
    if not required:
        if component.get("pipelineId") or component.get("pipelineSourceBranch"):
            fail(f"无需部署组件{name}不得绑定生产流水线")
        return {"name": name, "deployRequired": False}
    source_branch = required_string(component.get("sourceBranch"), f"组件{name}的已测来源分支")
    if not (source_branch.startswith("feature/") or source_branch.startswith("fix/")):
        fail(f"组件{name}的来源分支必须为feature/*或fix/*")
    expected_release = f"release/{version}"
    if component.get("releaseBranch") != expected_release:
        fail(f"组件{name}的发布候选分支必须为{expected_release}")
    if component.get("masterMerged") is not True:
        fail(f"组件{name}缺少已合并master证据")
    required_string(component.get("pipelineId"), f"组件{name}的生产流水线ID")
    if component.get("pipelineSourceBranch") != "master":
        fail(f"组件{name}的生产流水线源分支必须为master")
    return {"name": name, "deployRequired": True, "kind": component.get("kind")}


def validate(document: dict[str, Any]) -> dict[str, Any]:
    version = required_string(document.get("iteration"), "迭代名称")
    mode = required_string(document.get("topology"), "发布拓扑")
    terminals = document.get("terminals")
    components = document.get("components")
    if not isinstance(terminals, list) or not all(isinstance(item, str) and item for item in terminals):
        fail("terminals必须为非空字符串数组")
    if not isinstance(components, list) or not components:
        fail("components必须为非空数组")
    normalized = [item.strip() for item in terminals]
    if len(normalized) != len(set(normalized)):
        fail("terminals不得重复")
    if mode == "pc_single":
        if normalized != ["PC"]:
            fail("pc_single只允许终端PC")
    elif mode == "shared_service_dual":
        if len(normalized) != 2 or "PC" not in normalized:
            fail("shared_service_dual必须恰有PC和一个明确第二终端")
    else:
        fail("topology仅支持pc_single或shared_service_dual")
    checked = [validate_component(item, version) for item in components if isinstance(item, dict)]
    if len(checked) != len(components):
        fail("components中的每项必须为对象")
    if mode == "shared_service_dual" and not any(
        item.get("deployRequired") and item.get("kind") == "shared_service" for item in checked
    ):
        fail("shared_service_dual必须包含一个必发shared_service组件")
    return {
        "schemaVersion": "oneos.release-topology-check/v1",
        "result": "passed",
        "iteration": version,
        "topology": mode,
        "terminals": normalized,
        "requiredComponents": [item["name"] for item in checked if item["deployRequired"]],
        "noDeployComponents": [item["name"] for item in checked if not item["deployRequired"]],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    args = parser.parse_args()
    try:
        raw = json.loads(Path(args.input).read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            fail("输入必须是JSON对象")
        print(json.dumps(validate(raw), ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"result": "blocked", "error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 69


if __name__ == "__main__":
    raise SystemExit(main())
