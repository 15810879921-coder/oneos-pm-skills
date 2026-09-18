"""Validate merged-code repair evidence independently of test deployment."""
from __future__ import annotations

import hashlib
import html
import json
import re
from pathlib import Path
from typing import Callable

SCHEMA = "oneos.bug-fix-evidence/v1"
VALIDATION_SCHEMA = "oneos.bug-development-validation/v1"
MERGE_SCHEMA = "oneos.yunxiao-cli-bug-delivery-merges/v1"
START = "<!-- ONEOS_BUG_FIX_START -->"
END = "<!-- ONEOS_BUG_FIX_END -->"
SHA = re.compile(r"^[0-9a-fA-F]{40}$")


def digest(value: dict) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":")).encode()).hexdigest()


def object_file(path: str) -> dict:
    value = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError("修复证据必须为JSON对象")
    return value


def verify_mr(group: dict, read_mr: Callable[[str, str], dict]) -> None:
    detail = read_mr(str(group["repositoryId"]), str(group["localId"]))
    if not isinstance(detail, dict) or any(str(detail.get(key) or "") != str(expected)
        for key, expected in (("projectId", group["repositoryId"]), ("localId", group["localId"]),
                              ("sourceBranch", group["sourceBranch"]), ("targetBranch", group["targetBranch"]),
                              ("mergedRevision", group["mergedRevision"]))):
        raise ValueError("MR仓库、编号、分支或合并版本回读不一致")
    if str(detail.get("state") or detail.get("status") or "").upper() != "MERGED":
        raise ValueError("MR尚未实际合并，不能标记已修复")


def validate(merge_path: str, validation_path: str, snapshot: dict,
             requested: set[str], read_mr: Callable[[str, str], dict]) -> dict[str, dict]:
    merges = object_file(merge_path)
    canonical = {k: v for k, v in merges.items() if k not in {"hash", "receiptPath"}}
    if merges.get("schema") != MERGE_SCHEMA or merges.get("hash") != digest(canonical):
        raise ValueError("合并回执schema或哈希无效")
    if merges.get("snapshotHash") != snapshot.get("snapshotHash") or \
            str((merges.get("user") or {}).get("id")) != str((snapshot.get("currentUser") or {}).get("id")):
        raise ValueError("合并回执与当前Bug快照/用户不一致")
    validation = object_file(validation_path)
    if validation.get("schemaVersion") != VALIDATION_SCHEMA or validation.get("snapshotHash") != snapshot.get("snapshotHash"):
        raise ValueError("开发验证清单与当前Bug快照不一致")
    rows = validation.get("results")
    groups = merges.get("results")
    if not isinstance(rows, list) or not isinstance(groups, list) or not groups:
        raise ValueError("合并回执和开发验证清单必须包含结果")
    if any(not isinstance(g, dict) or not isinstance(g.get("bugSerials"), list) or not g["bugSerials"] for g in groups):
        raise ValueError("合并回执丢失分组Bug范围，无法排除遗漏的失败仓库")
    output = {}
    for bug in sorted(requested):
        relevant = [g for g in groups if isinstance(g, dict) and bug in g.get("bugSerials", [])]
        if not relevant:
            raise ValueError(f"{bug}没有对应合并结果")
        seen = set()
        verified = []
        for group in relevant:
            group_id = str(group.get("groupId") or "")
            if not group_id or group_id in seen:
                raise ValueError(f"{bug}合并分组缺失或重复")
            seen.add(group_id)
            if group.get("result") not in {"merged", "idempotent"} or group.get("state") != "MERGED" or \
                    not SHA.fullmatch(str(group.get("mergedRevision") or "")):
                raise ValueError(f"{bug}/{group_id}未成功合并")
            if any(not str(group.get(k) or "").strip() for k in
                   ("repositoryId", "localId", "sourceBranch", "targetBranch")):
                raise ValueError("合并证据缺仓库/MR/分支")
            checks = [r for r in rows if isinstance(r, dict) and r.get("bugSerialNumber") == bug and r.get("groupId") == group_id]
            if len(checks) != 1:
                raise ValueError(f"{bug}/{group_id}必须有唯一开发验证结果")
            check = checks[0]
            revisions = {str(group["mergedRevision"])}
            # Source validation is accepted only when merge executor freshly verified
            # the exact source head before merging, not for arbitrary old receipts.
            if group.get("sourceVerifiedAtMerge") is True:
                revisions.add(str(group.get("expectedSourceCommit") or ""))
            if check.get("status") != "passed" or check.get("revision") not in revisions or \
                    not str(check.get("repairSummary") or "").strip():
                raise ValueError(f"{bug}/{group_id}缺少版本匹配的通过验证或修复说明")
            report = Path(str(check.get("reportPath") or ""))
            if not report.is_absolute():
                report = Path(validation_path).resolve().parent / report
            if not report.is_file() or not report.stat().st_size or \
                    hashlib.sha256(report.read_bytes()).hexdigest() != check.get("reportSha256"):
                raise ValueError(f"{bug}/{group_id}开发验证报告缺失或哈希不符")
            verify_mr(group, read_mr)
            verified.append({**{k: group[k] for k in ("repositoryId", "localId", "sourceBranch", "targetBranch", "mergedRevision")},
                "groupId": group_id, "repairSummary": check["repairSummary"],
                "validation": {"status": "passed", "revision": check["revision"],
                               "reportSha256": check["reportSha256"]}})
        record = {"schemaVersion": SCHEMA, "bugSerialNumber": bug,
                  "snapshotHash": snapshot["snapshotHash"], "mergeReceiptHash": merges["hash"],
                  "groups": verified, "codeDelivery": "merged", "deploymentStatus": "pending",
                  "testHandoffStatus": "pending", "qaReady": False}
        record["fingerprint"] = digest(record)
        output[bug] = record
    return output


def existing_record(description: str) -> dict | None:
    if START not in description and END not in description:
        return None
    if description.count(START) != 1 or description.count(END) != 1:
        raise ValueError("修复记录受管区块损坏或重复")
    content = description.split(START, 1)[1].split(END, 1)[0]
    found = re.search(r'<!--\s*(\{.*\})\s*-->', content, re.S)
    if not found:
        raise ValueError("修复记录缺少可回读数据")
    result = json.loads(found.group(1))
    if not isinstance(result, dict):
        raise ValueError("修复记录数据无效")
    return result


def append_record(description: str, record: dict, format_type: str, *, allow_new_cycle: bool = False) -> str:
    old = existing_record(description)
    if old is not None:
        if old != record and not allow_new_cycle:
            raise ValueError("已有修复记录与本次不同，须重新核对，不能覆盖历史交测记录")
        if old == record:
            return description
        old_id = hashlib.sha256(json.dumps(old, sort_keys=True).encode()).hexdigest()[:16]
        description = description.replace(START, f"<!-- ONEOS_BUG_FIX_HISTORY:{old_id}:START -->", 1)
        description = description.replace(END, f"<!-- ONEOS_BUG_FIX_HISTORY:{old_id}:END -->", 1)
    data = json.dumps(record, ensure_ascii=False, sort_keys=True).replace('<', '\\u003c').replace('>', '\\u003e')
    label = "【研发完成】代码已合并；交测情况：待部署、待交付测试。已修复不代表测试环境已包含修复。"
    details = [f"修复：{g['repairSummary']}；开发验证：通过（{g['validation']['revision']}）；"
               f"仓库：{g['repositoryId']}；目标分支：{g['targetBranch']}；MR：!{g['localId']}；"
               f"合并提交：{g['mergedRevision']}" for g in record['groups']]
    if format_type.upper() == "HTML":
        label = "<p>" + label + "</p>" + ''.join('<p>' + html.escape(v) + '</p>' for v in details)
    else:
        label += '\n' + '\n'.join('- ' + v.replace('\n', ' ') for v in details)
    return description + f"\n{START}\n{label}\n<!-- {data} -->\n{END}"
