#!/usr/bin/env python3
"""Validate complete Web work-item -> repository -> component -> pipeline coverage."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


def _text(value: Any) -> str:
    return str(value or "").strip()


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("input root must be a JSON object")
    return value


def validate(data: dict[str, Any]) -> tuple[list[str], dict[str, Any]]:
    errors: list[str] = []
    suite_version = _text(data.get("suiteVersion"))
    new_contract = bool(suite_version)
    if new_contract and suite_version != "10.0.0":
        errors.append("suiteVersion must be 10.0.0 for the delivery-ledger contract")
    if new_contract:
        ledger_validation = data.get("ledgerValidation")
        if not isinstance(ledger_validation, dict) or ledger_validation.get("status") != "passed":
            errors.append("ledgerValidation.status must be passed for suiteVersion 10.0.0")
    scope_items = data.get("releaseCodeItems") or []
    anchors = data.get("codeAnchors") or []
    components = data.get("componentMatrix") or []

    if not isinstance(scope_items, list) or not isinstance(anchors, list) or not isinstance(components, list):
        return ["releaseCodeItems, codeAnchors and componentMatrix must be arrays"], {}

    web_item_ids: list[str] = []
    seen_scope: set[str] = set()
    for index, item in enumerate(scope_items):
        if not isinstance(item, dict):
            errors.append(f"releaseCodeItems[{index}] must be an object")
            continue
        item_id = _text(item.get("itemId"))
        channel = _text(item.get("channel"))
        if not item_id:
            errors.append(f"releaseCodeItems[{index}].itemId is required")
            continue
        if item_id in seen_scope:
            errors.append(f"duplicate releaseCodeItem: {item_id}")
            continue
        seen_scope.add(item_id)
        if channel.lower() in {"web", "pc"}:
            web_item_ids.append(item_id)

    anchors_by_item: dict[str, list[dict[str, Any]]] = defaultdict(list)
    anchors_by_component: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for index, anchor in enumerate(anchors):
        if not isinstance(anchor, dict):
            errors.append(f"codeAnchors[{index}] must be an object")
            continue
        item_id = _text(anchor.get("itemId"))
        repository_id = _text(anchor.get("repositoryId"))
        target_branch = _text(anchor.get("targetBranch"))
        deployment_target = _text(anchor.get("deploymentTarget"))
        target_branch_verified = anchor.get("targetBranchVerified") is True
        commit = _text(anchor.get("commit"))
        source_branch = _text(anchor.get("sourceBranch"))
        changed_paths = anchor.get("changedPaths") or []
        waived = bool(anchor.get("codeAnchorWaived"))

        if new_contract:
            for field in ("deliveryUnitId", "branchInstanceId", "ledgerEventId"):
                if not _text(anchor.get(field)):
                    errors.append(f"codeAnchors[{index}].{field} is required for suiteVersion 10.0.0")
            exact_commits = anchor.get("exactCommitIds") or []
            if not isinstance(exact_commits, list) or not exact_commits:
                errors.append(f"codeAnchors[{index}].exactCommitIds is required for suiteVersion 10.0.0")
            elif commit and commit not in {str(value) for value in exact_commits}:
                errors.append(f"codeAnchors[{index}].commit must be included in exactCommitIds")

        if item_id not in web_item_ids:
            errors.append(f"code anchor references non-Web or unknown item: {item_id or index}")
        for field, value in (
            ("repositoryId", repository_id),
            ("targetBranch", target_branch),
            ("deploymentTarget", deployment_target),
        ):
            if not value:
                errors.append(f"codeAnchors[{index}].{field} is required")
        if not waived and (not commit or not source_branch):
            errors.append(f"codeAnchors[{index}] requires sourceBranch and commit")
        if not target_branch_verified:
            errors.append(f"codeAnchors[{index}].targetBranchVerified must be true")
        if not isinstance(changed_paths, list) or not changed_paths:
            errors.append(f"codeAnchors[{index}].changedPaths must contain the verified patch tree")

        anchors_by_item[item_id].append(anchor)
        if repository_id and target_branch and deployment_target:
            anchors_by_component[(repository_id, target_branch, deployment_target)].append(anchor)

    for item_id in web_item_ids:
        if not anchors_by_item.get(item_id):
            errors.append(f"Web release code item has no code anchor: {item_id}")

    component_rows: dict[tuple[str, str, str], dict[str, Any]] = {}
    pipeline_ids: set[str] = set()
    for index, component in enumerate(components):
        if not isinstance(component, dict):
            errors.append(f"componentMatrix[{index}] must be an object")
            continue
        repository_id = _text(component.get("repositoryId"))
        target_branch = _text(component.get("targetBranch"))
        deployment_target = _text(component.get("deploymentTarget"))
        pipeline_id = _text(component.get("pipelineId"))
        pipeline_name = _text(component.get("pipelineName"))
        pipeline_repository_id = _text(component.get("pipelineRepositoryId"))
        pipeline_target_branch = _text(component.get("pipelineTargetBranch"))
        pipeline_deployment_target = _text(component.get("pipelineDeploymentTarget"))
        environment = _text(component.get("environment")).lower()
        source_item_ids = component.get("sourceItemIds") or []
        key = (repository_id, target_branch, deployment_target)

        for field, value in (
            ("repositoryId", repository_id),
            ("targetBranch", target_branch),
            ("deploymentTarget", deployment_target),
            ("pipelineId", pipeline_id),
            ("pipelineName", pipeline_name),
            ("pipelineRepositoryId", pipeline_repository_id),
            ("pipelineTargetBranch", pipeline_target_branch),
            ("pipelineDeploymentTarget", pipeline_deployment_target),
        ):
            if not value:
                errors.append(f"componentMatrix[{index}].{field} is required")
        if environment != "prod":
            errors.append(f"componentMatrix[{index}].environment must be prod")
        if pipeline_repository_id != repository_id:
            errors.append(f"componentMatrix[{index}] pipeline repository mismatch")
        if pipeline_target_branch != target_branch:
            errors.append(f"componentMatrix[{index}] pipeline target branch mismatch")
        if pipeline_deployment_target != deployment_target:
            errors.append(f"componentMatrix[{index}] pipeline deployment target mismatch")
        if key in component_rows:
            errors.append(f"duplicate component row: {key}")
        component_rows[key] = component
        if pipeline_id:
            pipeline_ids.add(pipeline_id)

        expected_items = {str(item.get("itemId")) for item in anchors_by_component.get(key, [])}
        actual_items = {str(value) for value in source_item_ids}
        if expected_items != actual_items:
            errors.append(
                f"component {key} sourceItemIds mismatch: expected {sorted(expected_items)}, got {sorted(actual_items)}"
            )

    for key in anchors_by_component:
        if key not in component_rows:
            errors.append(f"changed repository/component has no production matrix row: {key}")
    for key in component_rows:
        if key not in anchors_by_component:
            errors.append(f"component matrix row has no changed-code anchor: {key}")

    result = {
        "schemaVersion": "oneos.release-component-matrix-validation/v1",
        "suiteVersion": suite_version or "legacy-compatible",
        "status": "blocked" if errors else "passed",
        "webReleaseCodeItems": sorted(web_item_ids),
        "coveredWebItems": sorted(item_id for item_id in web_item_ids if anchors_by_item.get(item_id)),
        "changedComponentCount": len(anchors_by_component),
        "matrixRowCount": len(component_rows),
        "distinctProductionPipelineIds": sorted(pipeline_ids),
        "errors": errors,
    }
    return errors, result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    args = parser.parse_args()
    try:
        errors, result = validate(_load(args.input))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "blocked", "errors": [str(exc)]}, ensure_ascii=False, indent=2))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 2 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
