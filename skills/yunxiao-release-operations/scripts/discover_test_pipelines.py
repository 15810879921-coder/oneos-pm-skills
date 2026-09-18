#!/usr/bin/env python3
"""Discover uniquely matching Yunxiao test pipelines and verified deploy baselines.

This command is read-only.  It never starts, copies, or changes a pipeline.  The
caller supplies the frozen delivery components (repository and target branch)
and receives an auditable candidate table.  Pipeline names are display data
only; source, branch, logical environment, and deploy target are the matching
evidence.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Callable

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import yunxiao_cli_gateway as gateway
import yunxiao_cli_runtime as core


SCHEMA = "oneos.test-pipeline-candidates/v1"
SHA_RE = re.compile(r"^[0-9a-f]{40,64}$", re.I)
ACTIVE_BAD = ("disabled", "archived", "deleted", "retired", "停用", "归档")
TEST_MARKERS = ("test", "测试", "qa", "验收", "日常")
PROD_MARKERS = ("prod", "production", "生产", "线上")
SUCCESS = {"success", "succeeded", "successful", "passed", "pass", "成功", "已成功"}


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


def text(value: Any) -> str:
    if value is None or isinstance(value, (dict, list)):
        return ""
    return str(value).strip()


def rows(value: Any, labels: tuple[str, ...]) -> list[dict[str, Any]]:
    """Unwrap the official CLI response without assuming one response shape."""
    value = core.unwrap(value)
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        for label in labels:
            candidate = value.get(label)
            if isinstance(candidate, list):
                return [item for item in candidate if isinstance(item, dict)]
        for candidate in value.values():
            if isinstance(candidate, dict):
                found = rows(candidate, labels)
                if found:
                    return found
    return []


def paged(reader: Callable[[dict[str, Any]], Any], operation: str,
          base_args: list[str], labels: tuple[str, ...], per_page: int) -> tuple[list[dict[str, Any]], int]:
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    page_count = 0
    for page in range(1, 10001):
        call = {"operation": operation,
                "args": [*base_args, "--page", str(page), "--per-page", str(per_page)]}
        page_rows = rows(reader(call), labels)
        page_count = page
        for item in page_rows:
            key = text(item.get("pipelineId") or item.get("pipelineRunId") or
                       item.get("id") or item.get("runId"))
            if key and key in seen:
                raise core.AdapterError(f"{operation}分页出现重复对象：{key}")
            if key:
                seen.add(key)
            result.append(item)
        if len(page_rows) < per_page:
            return result, page_count
    raise core.AdapterError(f"{operation}超过分页读取上限，不能声明完整。")


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


def scalar_leaves(value: Any) -> list[str]:
    if isinstance(value, dict):
        result: list[str] = []
        for child in value.values():
            result.extend(scalar_leaves(child))
        return result
    if isinstance(value, list):
        result: list[str] = []
        for child in value:
            result.extend(scalar_leaves(child))
        return result
    candidate = text(value)
    return [candidate] if candidate else []


def values_for_keys(value: Any, keys: set[str]) -> list[tuple[str, str]]:
    result: list[tuple[str, str]] = []
    for path, key, child in walk(value):
        if key.lower() in {item.lower() for item in keys}:
            for candidate in scalar_leaves(child):
                result.append((path, candidate))
    return result


def normalise_repo(value: str) -> str:
    value = value.strip().rstrip("/")
    return value.lower()


def config_of(pipeline: dict[str, Any]) -> dict[str, Any]:
    config = pipeline.get("pipelineConfig")
    return config if isinstance(config, dict) else pipeline


def source_rows(pipeline: dict[str, Any]) -> list[dict[str, Any]]:
    config = config_of(pipeline)
    raw = config.get("sources")
    result: list[dict[str, Any]] = []
    if isinstance(raw, list):
        for item in raw:
            data = item.get("data") if isinstance(item, dict) else None
            if not isinstance(data, dict):
                data = item if isinstance(item, dict) else {}
            repo = text(data.get("repo") or data.get("repositoryId") or
                        data.get("repository") or data.get("httpUrl") or data.get("path"))
            branch = text(data.get("branch") or data.get("ref") or
                          data.get("branchName") or data.get("triggerFilter"))
            if repo or branch:
                result.append({"repository": repo, "branch": branch,
                               "label": text(data.get("label") or item.get("label") if isinstance(item, dict) else "")})
    # Some Flow versions expose source settings outside pipelineConfig.sources.
    if not result:
        repos = values_for_keys(pipeline, {"repo", "repositoryId", "repository", "httpUrl"})
        branches = values_for_keys(pipeline, {"branch", "branchName", "ref", "targetBranch"})
        for index, (path, repo) in enumerate(repos):
            branch = branches[index][1] if index < len(branches) else ""
            result.append({"repository": repo, "branch": branch, "path": path})
    return result


def logical_environment(pipeline: dict[str, Any]) -> tuple[str, list[str]]:
    evidence: list[str] = []
    values = values_for_keys(pipeline, {
        "environment", "environmentName", "envName", "deployEnvironment",
        "deploymentTarget", "deployTarget", "targetEnvironment", "stage",
    })
    joined = " ".join(value.lower() for _, value in values)
    if any(marker in joined for marker in PROD_MARKERS):
        return "prod", [path for path, _ in values]
    if any(marker in joined for marker in TEST_MARKERS):
        evidence = [path for path, _ in values]
        return "test", evidence
    return "unknown", evidence


def deployment_targets(pipeline: dict[str, Any]) -> list[str]:
    values = values_for_keys(pipeline, {"deploymentTarget", "deployTarget", "service", "serviceName", "component", "componentName"})
    return sorted({value for _, value in values if value})


def active(pipeline: dict[str, Any]) -> tuple[bool, str]:
    name = text(pipeline.get("name") or pipeline.get("pipelineName"))
    status = text(pipeline.get("status") or pipeline.get("state")).lower()
    lowered_name = name.lower()
    explicit_retired = values_for_keys(pipeline, {"disabled", "archived", "isDisabled", "isArchived", "lifecycleState"})
    retired_text = " ".join(value.lower() for _, value in explicit_retired)
    if any(marker in lowered_name for marker in ACTIVE_BAD) or any(marker in retired_text for marker in ACTIVE_BAD) or status in {"disabled", "archived", "inactive", "停用", "归档"}:
        return False, "流水线已停用、归档或标记为旧定义"
    if not name:
        return False, "流水线缺少名称"
    return True, "active"


def project_matches(pipeline: dict[str, Any], project_id: str) -> tuple[bool, str]:
    values = values_for_keys(pipeline, {"projectId", "projectIdentifier", "spaceIdentifier"})
    project_values = {normalise_repo(value) for _, value in values if value}
    expected = normalise_repo(project_id)
    if not project_values:
        return False, "流水线详情没有可核验的项目标识"
    if expected not in project_values:
        return False, f"项目不匹配：期望{project_id}，实际={sorted(project_values)}"
    return True, f"项目={project_id}"


def component_matches(pipeline: dict[str, Any], component: dict[str, Any]) -> tuple[bool, str]:
    repository = normalise_repo(text(component.get("repositoryId") or component.get("repository") or component.get("repositoryUrl")))
    branch = text(component.get("targetBranch") or component.get("branch"))
    if not repository or not branch:
        return False, "scope缺少repositoryId或targetBranch"
    candidates = []
    for source in source_rows(pipeline):
        source_repo = normalise_repo(source.get("repository", ""))
        source_branch = text(source.get("branch"))
        repo_ok = source_repo == repository or repository in source_repo or source_repo.endswith("/" + repository)
        if repo_ok and source_branch == branch:
            candidates.append(source)
    expected_target = text(component.get("deploymentTarget") or component.get("deployTarget") or component.get("service") or component.get("componentId"))
    if len(candidates) == 1:
        if expected_target:
            actual_targets = {normalise_repo(value) for value in deployment_targets(pipeline)}
            if normalise_repo(expected_target) not in actual_targets:
                return False, f"代码库/分支匹配但部署目标不匹配：期望{expected_target}，实际={sorted(actual_targets)}"
        return True, f"代码库={repository};分支={branch}"
    if len(candidates) > 1:
        return False, f"代码源重复匹配={len(candidates)}"
    if expected_target:
        actual_targets = {normalise_repo(value) for value in deployment_targets(pipeline)}
        if normalise_repo(expected_target) not in actual_targets:
            return False, f"代码库/分支匹配但部署目标不匹配：期望{expected_target}，实际={sorted(actual_targets)}"
    return False, f"代码库/分支不匹配：期望{repository}/{branch}"


def match_pipeline(pipeline: dict[str, Any], project_id: str, components: list[dict[str, Any]],
                   selected_name: str | None = None) -> dict[str, Any]:
    is_active, active_reason = active(pipeline)
    environment, env_paths = logical_environment(pipeline)
    name = text(pipeline.get("name") or pipeline.get("pipelineName"))
    reasons = []
    matched: list[str] = []
    project_ok, project_reason = project_matches(pipeline, project_id)
    if not project_ok:
        reasons.append(project_reason)
    if not is_active:
        reasons.append(active_reason)
    if environment != "test":
        reasons.append(f"逻辑环境={environment}，不是test")
    for component in components:
        ok, reason = component_matches(pipeline, component)
        key = text(component.get("componentId") or component.get("service") or component.get("repositoryId"))
        (matched if ok else reasons).append(key if ok else f"{key}:{reason}")
    if selected_name and selected_name not in {name, text(pipeline.get("pipelineId") or pipeline.get("id"))}:
        reasons.append("未命中用户指定的流水线名称或ID")
    exact = bool(is_active and environment == "test" and components and len(matched) == len(components) and not reasons)
    return {
        "pipelineId": text(pipeline.get("pipelineId") or pipeline.get("id")),
        "pipelineName": name,
        "services": deployment_targets(pipeline),
        "branches": sorted({text(item.get("branch")) for item in source_rows(pipeline) if text(item.get("branch"))}),
        "environment": environment,
        "environmentEvidence": env_paths,
        "match": "exact" if exact else "rejected",
        "matchedComponents": matched,
        "reasons": reasons,
        "definitionEvidence": {"sources": source_rows(pipeline)},
    }


def parse_time(value: Any) -> dt.datetime | None:
    raw = text(value)
    if not raw:
        return None
    if raw.isdigit():
        stamp = float(raw)
        if stamp > 10_000_000_000:
            stamp /= 1000
        return dt.datetime.fromtimestamp(stamp, tz=dt.timezone.utc)
    try:
        return dt.datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def run_status(run: dict[str, Any]) -> str:
    return text(run.get("status") or run.get("result") or run.get("state") or run.get("executionStatus")).lower()


def deployed_revision(run: dict[str, Any]) -> tuple[str, str] | None:
    for path, key, value in walk(run):
        if key.lower() in {"commitid", "commitsha", "revision", "deployedversion", "sourcecommit", "gitcommit"}:
            candidate = text(value)
            if candidate and SHA_RE.fullmatch(candidate):
                return candidate, path
    return None


def latest_baseline(reader: Callable[[dict[str, Any]], Any], pipeline_id: str) -> dict[str, Any]:
    runs, page_count = paged(reader, "flow-list-pipeline-runs", ["--pipeline-id", pipeline_id],
                             ("runs", "pipelineRuns", "items"), 100)
    verified: list[dict[str, Any]] = []
    detail_count = 0
    for row in runs:
        run_id = text(row.get("pipelineRunId") or row.get("runId") or row.get("id"))
        if not run_id:
            continue
        detail = core.unwrap(reader({"operation": "flow-get-pipeline-run", "args": ["--pipeline-run-id", run_id]}))
        detail_count += 1
        if not isinstance(detail, dict):
            continue
        merged = {**row, **detail}
        if run_status(merged) not in SUCCESS:
            continue
        revision = deployed_revision(merged)
        if not revision:
            continue
        finished = next((parse_time(merged.get(key)) for key in ("finishedAt", "completedAt", "endTime", "updateTime", "modifiedAt", "startTime") if parse_time(merged.get(key))), None)
        verified.append({"runId": run_id, "revision": revision[0], "revisionEvidence": revision[1],
                         "completedAt": finished.isoformat().replace("+00:00", "Z") if finished else None,
                         "status": run_status(merged)})
    verified.sort(key=lambda item: item.get("completedAt") or "", reverse=True)
    return {"status": "verified" if verified else "unavailable", "value": verified[0] if verified else None,
            "runPages": page_count, "runDetailsRead": detail_count,
            "reason": None if verified else "没有同时具备终态成功和实际部署版本证据的流水线运行记录"}


def pending_for_component(reader: Callable[[dict[str, Any]], Any], component: dict[str, Any],
                          baseline_revision: str | None) -> dict[str, Any]:
    repository = text(component.get("repositoryId") or component.get("repository"))
    branch = text(component.get("targetBranch") or component.get("branch"))
    if not baseline_revision or not SHA_RE.fullmatch(baseline_revision):
        return {"status": "unavailable", "reason": "上次成功部署记录没有完整提交SHA"}
    commits: list[dict[str, Any]] = []
    seen: set[str] = set()
    for page in range(1, 10001):
        value = reader({"operation": "codeup-list-commits", "args": [
            "--repository-id", repository, "--ref-name", branch,
            "--page", str(page), "--per-page", "100",
        ]})
        page_rows = rows(value, ("commits", "items", "result"))
        if not page_rows:
            break
        for commit in page_rows:
            commit_id = text(commit.get("id") or commit.get("commitId") or commit.get("sha"))
            if not commit_id or commit_id in seen:
                if commit_id in seen:
                    raise core.AdapterError(f"codeup-list-commits分页出现重复提交：{commit_id}")
                continue
            seen.add(commit_id)
            commits.append(commit)
            if commit_id.lower() == baseline_revision.lower():
                return {"status": "calculated", "baselineRevision": baseline_revision,
                        "currentHead": text(commits[0].get("id") or commits[0].get("commitId") or commits[0].get("sha")),
                        "count": len(commits) - 1,
                        "commits": commits[:-1]}
        if len(page_rows) < 100:
            break
    return {"status": "unavailable", "baselineRevision": baseline_revision,
            "currentHead": text(commits[0].get("id") or commits[0].get("commitId") or commits[0].get("sha")) if commits else None,
            "reason": "目标分支完整历史中找不到上次成功部署的基线提交，不能安全计算待部署变更"}


def build_scope(scope: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    project_id = text(scope.get("projectId"))
    components = scope.get("components")
    if not project_id or not isinstance(components, list) or not components:
        raise core.AdapterError("scope必须包含projectId和非空components。")
    for index, item in enumerate(components):
        if not isinstance(item, dict) or not text(item.get("repositoryId") or item.get("repository")) or not text(item.get("targetBranch") or item.get("branch")):
            raise core.AdapterError(f"scope.components[{index}]必须包含代码库和目标分支。")
    return project_id, components


def discover(scope: dict[str, Any], reader: Callable[[dict[str, Any]], Any], selected_name: str | None = None) -> dict[str, Any]:
    project_id, components = build_scope(scope)
    pipelines, pipeline_pages = paged(reader, "flow-list-pipelines", [], ("pipelines", "items"), 10)
    candidates: list[dict[str, Any]] = []
    for summary in pipelines:
        pipeline_id = text(summary.get("pipelineId") or summary.get("id"))
        if not pipeline_id:
            continue
        detail = core.unwrap(reader({"operation": "flow-get-pipeline", "args": ["--pipeline-id", pipeline_id]}))
        if not isinstance(detail, dict):
            continue
        # Flow detail responses differ by plugin version; retain summary-level
        # project and display fields while letting the detail override them.
        detail = {**summary, **detail}
        match = match_pipeline(detail, project_id, components, selected_name)
        if match["match"] != "exact":
            continue
        baseline = latest_baseline(reader, pipeline_id)
        match["baseline"] = baseline
        match["lastSuccessfulDeploymentAt"] = (baseline.get("value") or {}).get("completedAt")
        match["baselineRevision"] = (baseline.get("value") or {}).get("revision")
        pending_components = [pending_for_component(reader, item, match["baselineRevision"])
                              for item in components]
        pending_status = "calculated" if all(item.get("status") == "calculated" for item in pending_components) else "unavailable"
        match["pendingChanges"] = {"status": pending_status, "components": [
            {"componentId": text(item.get("componentId") or item.get("service") or item.get("repositoryId")),
             "repositoryId": text(item.get("repositoryId") or item.get("repository")),
             "targetBranch": text(item.get("targetBranch") or item.get("branch")),
             **pending}
            for item, pending in zip(components, pending_components)]}
        if pending_status != "calculated":
            match["reasons"].append("待部署变更无法由Codeup完整历史计算")
        candidates.append(match)
    status = "ready" if len(candidates) == 1 and candidates[0]["baseline"]["status"] == "verified" and candidates[0]["pendingChanges"]["status"] == "calculated" else "needs-selection"
    blockers: list[str] = []
    if not candidates:
        blockers.append("没有找到同时满足项目范围、代码库、目标分支和逻辑测试环境的唯一流水线")
    elif len(candidates) > 1:
        blockers.append(f"候选流水线不唯一：{len(candidates)}条，需要显式选择pipelineId")
    if any(item["baseline"]["status"] != "verified" for item in candidates):
        blockers.append("候选流水线缺少可核验的上次成功部署版本")
    if any(item["pendingChanges"]["status"] != "calculated" for item in candidates):
        blockers.append("候选流水线的上次部署基线不在目标分支完整历史中，无法计算待部署变更")
    return {"schemaVersion": SCHEMA, "result": status, "projectId": project_id,
            "scopeHash": digest(scope), "pipelinePages": pipeline_pages,
            "candidateCount": len(candidates), "candidates": candidates,
            "blockers": blockers, "readOnly": True, "generatedAt": core.now_utc()}


def official_reader():
    executable = core.find_aliyun()
    core.require_auth_env()
    return executable, lambda call: gateway.execute_read(executable, call)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", required=True, help="冻结的项目/仓库/分支范围JSON")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--pipeline", help="仅在已结构匹配后按精确名称或ID缩小候选")
    args = parser.parse_args()
    try:
        scope = json.loads(Path(args.scope).read_text(encoding="utf-8"))
        if not isinstance(scope, dict):
            raise core.AdapterError("scope必须是JSON对象。")
        _, reader = official_reader()
        result = discover(scope, reader, args.pipeline)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["result"] == "ready" else 2
    except (OSError, json.JSONDecodeError, core.AdapterError) as exc:
        print(json.dumps({"schemaVersion": SCHEMA, "result": "blocked", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
