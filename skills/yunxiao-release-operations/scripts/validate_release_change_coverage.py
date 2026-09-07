#!/usr/bin/env python3
"""Read official commit histories and verify release patches in an isolated Git index.

No network Git, branch mutation, checkout, merge, or pipeline execution is performed.
Scope decisions remain evidence-backed judgments; graph reachability is not business scope.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any

HISTORY_SCHEMA = "oneos.release-history/v1"
COVERAGE_SCHEMA = "oneos.release-tree-coverage/v1"


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


def request(repository: str, head: str, page: int) -> dict:
    return {"operation": "codeup-list-commits", "args": [
        "--repository-id", repository, "--ref-name", head,
        "--page", str(page), "--per-page", "100",
        "--cli-query", "[].{id:id,parentIds:parentIds}"]}


def official_reader():
    import yunxiao_cli_gateway as gateway
    executable = gateway.core.find_aliyun()
    gateway.core.require_auth_env()

    def read(call):
        return gateway.core.unwrap(gateway.execute_read(executable, call))
    return read


def collect(repository: str, source: str, target: str, reader=None) -> dict:
    if any(not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", value) for value in (source, target)):
        raise ValueError("历史采集必须使用完整冻结提交SHA，不能使用可变分支名")
    # Lazy import keeps offline validation independent of CLI credentials/dependencies.
    if reader is None:
        reader = official_reader()

    result = {"schemaVersion": HISTORY_SCHEMA, "repositoryId": repository,
              "sourceHead": source, "targetBaseCommit": target}
    for key, head in (("sourcePages", source), ("targetPages", target)):
        pages = []
        seen = set()
        for page in range(1, 10001):
            call = request(repository, head, page)
            rows = reader(call)
            if not isinstance(rows, list):
                raise ValueError("Codeup提交列表返回值不是数组")
            pages.append({"request": call, "commits": rows})
            if not rows:
                break
            ids = [row.get("id") for row in rows if isinstance(row, dict)]
            if len(ids) != len(rows) or any(not value or value in seen for value in ids):
                raise ValueError("提交分页重复或无有效提交ID，保留已有证据后重新读取")
            seen.update(ids)
        else:
            raise ValueError("提交历史超过读取上限，不能声明完整")
        result[key] = pages
    history_graphs(result, repository, source, target)
    return result


def graph(pages: Any, repository: str, head: str) -> dict[str, list[str]]:
    if (not isinstance(pages, list) or not pages or not all(isinstance(p, dict) for p in pages)
            or pages[-1].get("commits") != []):
        raise ValueError("提交历史缺少终止空页")
    nodes = {}
    for page, entry in enumerate(pages, 1):
        if entry.get("request") != request(repository, head, page):
            raise ValueError("提交读取范围/分页与冻结版本不一致")
        rows = entry.get("commits")
        if not isinstance(rows, list) or (not rows and page != len(pages)):
            raise ValueError("提交历史分页不连续")
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError("提交记录必须是对象")
            sha, parents = row.get("id"), row.get("parentIds")
            if not isinstance(sha, str) or not sha or sha in nodes:
                raise ValueError("提交ID缺失或重复")
            if not isinstance(parents, list) or any(not isinstance(p, str) or not p for p in parents):
                raise ValueError(f"提交{sha}缺少真实父关系")
            nodes[sha] = parents
    if head not in nodes:
        raise ValueError("历史不包含冻结的HEAD")
    for sha, parents in nodes.items():
        if any(parent not in nodes for parent in parents):
            raise ValueError(f"提交{sha}存在未读取的父提交")
    ordered = topological(nodes)
    reachable = set()
    stack = [head]
    while stack:
        sha = stack.pop()
        if sha not in reachable:
            reachable.add(sha)
            stack.extend(nodes[sha])
    if reachable != set(ordered):
        raise ValueError("历史包含冻结HEAD不可达的提交")
    return nodes


def topological(nodes: dict[str, list[str]]) -> list[str]:
    import heapq
    children = {sha: [] for sha in nodes}
    degree = {sha: 0 for sha in nodes}
    for sha, parents in nodes.items():
        for parent in set(parents):
            if parent not in nodes:
                raise ValueError(f"依赖提交{parent}未读取")
            children[parent].append(sha)
            degree[sha] += 1
    ready = [sha for sha in nodes if degree[sha] == 0]
    heapq.heapify(ready)
    ordered = []
    while ready:
        sha = heapq.heappop(ready)
        ordered.append(sha)
        for child in children[sha]:
            degree[child] -= 1
            if degree[child] == 0:
                heapq.heappush(ready, child)
    if len(ordered) != len(nodes):
        raise ValueError("提交/依赖关系存在环")
    return ordered


def history_graphs(snapshot: dict, repository: str, source: str, target: str):
    if not isinstance(snapshot, dict):
        raise ValueError("historySnapshot必须是官方采集结果对象")
    if (snapshot.get("schemaVersion") != HISTORY_SCHEMA or
            snapshot.get("repositoryId") != repository or snapshot.get("sourceHead") != source or
            snapshot.get("targetBaseCommit") != target):
        raise ValueError("历史证据与仓库、冻结源或目标基线不一致")
    source_graph = graph(snapshot.get("sourcePages"), repository, source)
    target_graph = graph(snapshot.get("targetPages"), repository, target)
    for sha in source_graph.keys() & target_graph.keys():
        if source_graph[sha] != target_graph[sha]:
            raise ValueError("相同提交的父关系证据冲突")
    return source_graph, target_graph


def inspect_source(source: dict, repository: str, target: str, available: set | None = None) -> dict:
    owner = source.get("branchOwner") or {}
    if (not isinstance(owner, dict) or owner.get("type") not in {"development_task", "independent_bug"} or
            not owner.get("workItemId") or not owner.get("relationEvidenceId")):
        raise ValueError("分支直接所有者必须是有正式关系证据的开发任务或独立缺陷，不能是交付")
    if owner["type"] == "independent_bug" and owner.get("relatedWorkItemIds") != []:
        raise ValueError("独立缺陷必须核验无关联工作项；有关系时先追踪开发链")
    sg, tg = history_graphs(source.get("historySnapshot") or {}, repository,
                            source.get("sourceHead"), target)
    delta = set(sg) - set(tg)
    exact = source.get("exactCommitIds") or []
    if len(exact) != len(set(exact)) or not set(exact) <= set(sg):
        raise ValueError("精确提交重复或不在冻结源历史中")
    decisions = {}
    for row in source.get("sourceCommitHistory") or []:
        sha = row.get("commitId")
        if sha in decisions or sha not in sg or not isinstance(row.get("include"), bool) or not row.get("evidenceId"):
            raise ValueError("逐提交判定缺失、重复或没有范围证据")
        decisions[sha] = row
    if not delta <= decisions.keys():
        raise ValueError("真实历史存在未判定提交：" + ",".join(sorted(delta - decisions.keys())))
    included = {sha for sha, row in decisions.items() if row["include"]}
    if set(exact) - set(tg) != included - set(tg):
        raise ValueError("精确提交集合与真实历史纳入项不一致")
    if source.get("branchPurity") == "contained" and not set(exact) <= set(tg):
        raise ValueError("ALREADY_CONTAINED只能用于目标真实包含的提交；等价补丁走候选内容核验")
    parents = {sha: list(values) for sha, values in sg.items()}
    replay_parents = {}
    # A commit in target ancestry may have been reverted: still verify its content.
    equivalents = list(set(exact) & set(tg))
    for sha in exact:
        actual = sg[sha]
        chosen = decisions.get(sha, {}).get("replayParent")
        if len(actual) > 1 and chosen not in actual:
            raise ValueError(f"合并提交{sha}必须提供有证据的replayParent")
        replay_parents[sha] = chosen or (actual[0] if actual else None)
    for sha, row in decisions.items():
        if not row["include"] and sha in delta:
            if row.get("reason") != "out-of-scope":
                raise ValueError(f"排除提交{sha}必须说明范围外或目标补丁等价")
        if row.get("reason") == "target-equivalent":
            if not row["include"]:
                raise ValueError("等价补丁仍属于本次必要变更，必须include=true")
            equivalents.append(sha)
        required = (row.get("requiresCommitIds") or []) if row["include"] else []
        if not isinstance(required, list):
            raise ValueError("requiresCommitIds必须为数组")
        for dep in required:
            if dep not in tg and dep not in included and dep not in (available or set()):
                raise ValueError(f"提交{sha}的必要依赖{dep}未纳入或未证明目标包含")
            if dep in sg:
                parents[sha].append(dep)
            if dep in tg:
                dependency_parents = tg[dep]
                chosen = decisions.get(dep, {}).get("replayParent")
                if len(dependency_parents) > 1 and chosen not in dependency_parents:
                    raise ValueError(f"目标依赖{dep}是合并提交，需要明确内容核对父节点")
                equivalents.append(dep)
                replay_parents[dep] = chosen or (dependency_parents[0] if dependency_parents else None)
        if sha in included or row.get("reason") == "target-equivalent":
            actual = sg[sha]
            chosen = row.get("replayParent")
            if len(actual) > 1 and chosen not in actual:
                raise ValueError(f"合并提交{sha}必须提供有证据的replayParent")
            replay_parents[sha] = chosen or (actual[0] if actual else None)
    return {"graph": sg, "targetGraph": tg,
            "replayOrder": [sha for sha in topological(parents) if sha in included and sha not in tg and sha not in equivalents],
            "replayParents": replay_parents, "equivalentCommitIds": sorted(set(equivalents))}


def inspect_item(item: dict) -> dict:
    nodes, target_nodes, replay_parents, required = {}, {}, {}, {}
    selected, equivalent = set(), set()
    available = {sha for source in item["sources"] for sha in source.get("exactCommitIds", [])}
    for source in item["sources"]:
        info = inspect_source(source, item["repositoryId"], item["targetBaseCommit"], available)
        for dest, incoming in ((nodes, info["graph"]), (target_nodes, info["targetGraph"]),
                               (replay_parents, info["replayParents"])):
            for sha, value in incoming.items():
                if sha in dest and dest[sha] != value:
                    raise ValueError("多源提交证据或重放父节点冲突")
                dest[sha] = value
        for row in source.get("sourceCommitHistory") or []:
            if row["include"]:
                required.setdefault(row["commitId"], set()).update(row.get("requiresCommitIds") or [])
        selected.update(info["replayOrder"])
        equivalent.update(info["equivalentCommitIds"])
    if selected & equivalent:
        raise ValueError("同一补丁在多源中同时被纳入和标记等价")
    dependencies = {sha: list(parents) + [dep for dep in required.get(sha, []) if dep in nodes]
                    for sha, parents in nodes.items()}
    return {"replayOrder": [sha for sha in topological(dependencies) if sha in selected],
            "replayParents": replay_parents, "equivalentCommitIds": sorted(equivalent),
            "graph": nodes, "targetGraph": target_nodes}


def validate_plan(plan: dict) -> None:
    core = {key: value for key, value in plan.items() if key != "planHash"}
    if plan.get("planHash") != digest(core):
        raise ValueError("mergePlan内容哈希不一致")
    core.pop("mergePlanId", None)
    if plan.get("mergePlanId") != "MERGEPLAN-" + digest(core)[:20]:
        raise ValueError("mergePlanId与冻结内容不一致")
    if plan.get("coverageVersion") != 1 or plan.get("status") != "READY":
        raise ValueError("旧计划必须补读历史并生成新版本，不能直接执行")
    if not plan.get("items"):
        raise ValueError("mergePlan没有仓库")
    for item in plan["items"]:
        info = inspect_item(item)
        if item.get("replayOrder") != info["replayOrder"]:
            raise ValueError("冻结重放顺序与真实父关系不一致")
        if set(item["exactCommitIds"]) != {sha for source in item["sources"] for sha in source["exactCommitIds"]}:
            raise ValueError("仓库与来源提交集合不一致")


def repository_key(item: dict) -> str:
    return "|".join(str(item[key]) for key in ("repositoryId", "componentId", "targetBranch", "deploymentTarget"))


def root_tree_hash(entries: list, hash_length: int = 40) -> str:
    """Git tree objects embed subtree hashes, so the root commits to all descendants."""
    if not isinstance(entries, list):
        raise ValueError("官方根目录读取结果必须是数组")
    modes = {"40000": "tree", "100644": "blob", "100755": "blob", "120000": "blob", "160000": "commit"}
    rows, names = [], set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("官方文件树记录必须是对象")
        mode = str(entry.get("mode", "")).lstrip("0")
        kind, name, sha = entry.get("type"), entry.get("name"), entry.get("id")
        if (modes.get(mode) != kind or not isinstance(name, str) or not name or name in names or
                "/" in name or "\x00" in name or name in {".", ".."} or entry.get("path") != name or
                not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{" + str(hash_length) + "}", sha)):
            raise ValueError("官方根目录存在无效、重复或不完整的文件树记录")
        names.add(name)
        encoded = name.encode("utf-8")
        rows.append((encoded + (b"/" if kind == "tree" else b""),
                     mode.encode() + b" " + encoded + b"\0" + bytes.fromhex(sha)))
    content = b"".join(row for _, row in sorted(rows))
    algorithm = hashlib.sha256 if hash_length == 64 else hashlib.sha1
    return algorithm(b"tree " + str(len(content)).encode() + b"\0" + content).hexdigest()


def verify_tree(plan: dict, item: dict, repository: Path, revision: str, tree_reader=None) -> dict:
    validate_plan(plan)
    info = inspect_item(item)
    # Git is used only on already available local objects, never for cloud discovery.
    environment = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    environment.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull, GIT_NO_REPLACE_OBJECTS="1")

    def local(*args):
        result = subprocess.run(["git", "-C", str(repository), *args], env=environment,
                                capture_output=True, timeout=120)
        if result.returncode:
            raise ValueError("本地Git对象缺失或无法读取；先通过官方Codeup证据补齐对象")
        return result.stdout

    common = Path(local("rev-parse", "--path-format=absolute", "--git-common-dir").decode().strip())
    tree_evidence = None
    if tree_reader is not None:
        if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", revision):
            raise ValueError("官方内容核验必须使用完整候选或目标SHA")
        actual = revision
        call = {"operation": "codeup-list-files", "args": ["--repository-id", item["repositoryId"], "--ref", actual]}
        entries = tree_reader(call)
        actual_tree = root_tree_hash(entries, len(actual))
        tree_evidence = {"request": call, "entries": entries}
    else:
        actual = local("rev-parse", "--verify", "--end-of-options", revision + "^{commit}").decode().strip()
        actual_tree = local("rev-parse", actual + "^{tree}").decode().strip()
    base = item["targetBaseCommit"]
    frozen_graph = {**info["graph"], **info["targetGraph"]}
    for sha in frozen_graph:
        if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", sha):
            raise ValueError("官方历史提交ID必须是完整SHA")
    heads = list(dict.fromkeys([source["sourceHead"] for source in item["sources"]] + [base]))
    actual_graph = {}
    for line in local("rev-list", "--parents", *heads, "--").decode().splitlines():
        ids = line.split()
        actual_graph[ids[0]] = ids[1:]
    if actual_graph != frozen_graph:
        raise ValueError("本地对象父关系与官方历史证据不一致")
    with tempfile.TemporaryDirectory(prefix="oneos-release-coverage-") as directory:
        scratch = Path(directory)
        init = subprocess.run(["git", "init", "--bare", str(scratch / "repo")],
                              capture_output=True, env=environment, timeout=30)
        if init.returncode:
            raise ValueError("无法创建隔离验证仓库")
        env = dict(environment, GIT_INDEX_FILE=str(scratch / "index"),
                   GIT_ALTERNATE_OBJECT_DIRECTORIES=str(common / "objects"))

        def git(*args, data=None):
            proc = subprocess.run(["git", "--git-dir", str(scratch / "repo"), *args],
                                  input=data, capture_output=True, env=env, timeout=120)
            if proc.returncode:
                raise ValueError("补丁无法无冲突重放或等价检查失败；保留证据并修订计划")
            return proc.stdout

        def patch(sha):
            parent = info["replayParents"][sha]
            if parent:
                return git("diff", "--no-ext-diff", "--no-textconv", "--binary", "--full-index", parent, sha, "--")
            return git("diff-tree", "--root", "--no-commit-id", "-p", "--binary", "--full-index", sha, "--")

        git("read-tree", base)
        for sha in info["equivalentCommitIds"]:
            content = patch(sha)
            if content:
                git("apply", "--cached", "--reverse", "--check", "--whitespace=nowarn", data=content)
        for sha in info["replayOrder"]:
            content = patch(sha)
            if content:
                git("apply", "--cached", "--3way", "--whitespace=nowarn", data=content)
        expected = git("write-tree").decode().strip()
        if expected != actual_tree:
            raise ValueError("候选/目标最终文件树与冻结补丁重放结果不一致（缺项、额外变更或冲突处理改变内容）")
    proof = {"schemaVersion": COVERAGE_SCHEMA, "planHash": plan["planHash"],
             "repositoryKey": repository_key(item), "targetBaseCommit": base,
             "revision": actual, "expectedTree": expected, "actualTree": actual_tree}
    if tree_evidence is not None:
        proof["officialTreeRead"] = tree_evidence
    proof["proofHash"] = digest(proof)
    return proof


def validate_proof(proof: dict, plan_hash: str, key: str, base: str, revision: str) -> None:
    if (proof.get("schemaVersion") != COVERAGE_SCHEMA or proof.get("planHash") != plan_hash or
            proof.get("repositoryKey") != key or proof.get("targetBaseCommit") != base or
            not revision or proof.get("revision") != revision or not proof.get("actualTree") or
            proof.get("actualTree") != proof.get("expectedTree") or
            proof.get("proofHash") != digest({k: v for k, v in proof.items() if k != "proofHash"})):
        raise ValueError("缺少与当前计划、仓库、基线及实际版本绑定的文件树核验结果")
    if "officialTreeRead" in proof:
        read = proof["officialTreeRead"]
        expected_call = {"operation": "codeup-list-files", "args": ["--repository-id", key.split("|")[0], "--ref", revision]}
        if read.get("request") != expected_call or root_tree_hash(read.get("entries"), len(revision)) != proof["actualTree"]:
            raise ValueError("官方文件树证据与核验结果不一致")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    gather = sub.add_parser("collect")
    gather.add_argument("--repository-id", required=True)
    gather.add_argument("--source-head", required=True)
    gather.add_argument("--target-base", required=True)
    gather.add_argument("--output", required=True, type=Path)
    verify = sub.add_parser("verify-tree")
    verify.add_argument("--plan", required=True, type=Path)
    verify.add_argument("--repository-key", required=True)
    verify.add_argument("--repository", required=True, type=Path)
    verify.add_argument("--revision", required=True)
    verify.add_argument("--local-only", action="store_true", help="仅离线测试；正式执行默认使用官方文件树读回")
    verify.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        if args.command == "collect":
            result = collect(args.repository_id, args.source_head, args.target_base)
        else:
            plan = json.loads(args.plan.read_text(encoding="utf-8-sig"))
            matches = [item for item in plan["items"] if repository_key(item) == args.repository_key]
            if len(matches) != 1:
                raise ValueError("仓库键未唯一命中计划")
            result = verify_tree(plan, matches[0], args.repository, args.revision,
                                 None if args.local_only else official_reader())
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"status": "passed", "output": str(args.output)}, ensure_ascii=False))
        return 0
    except (ValueError, KeyError, TypeError, OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({"status": "blocked", "error": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    sys.exit(main())
