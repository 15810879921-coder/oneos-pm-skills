"""Synthetic, offline-only handoff examples; never use these as live evidence."""
from __future__ import annotations

import copy
import hashlib
import json


def seal(value):
    value = copy.deepcopy(value)
    value.pop("sha256", None)
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    value["sha256"] = hashlib.sha256(raw.encode()).hexdigest()
    return value


def make_bundle(stage="release"):
    manifest = seal({
        "schemaVersion": "oneos.delivery-handoff/v1",
        "handoffId": "HO-1", "version": "1",
        "scope": {"projectId": "PROJECT-1", "requirementId": "REQ-1",
                  "deliveryId": "DEL-1", "scopeId": "SCOPE-DEV-1"},
        "documents": [
            {"id": kind, "kind": kind, "uri": f"https://example.test/{kind}.md",
             "sha256": hashlib.sha256(kind.encode()).hexdigest(), "required": True}
            for kind in ("product-contract", "acceptance", "engineering-decisions")
        ],
        "requiredAcceptanceIds": ["AC-1", "AC-2"],
        "requiredDecisionIds": ["ED-1"],
        "exclusions": ["不新增视频播放"],
    })
    def receipt(role, task):
        return seal({
            "schemaVersion": "oneos.handoff-receipt/v1", "role": role,
            "taskId": task, "reader": role + "-operator", "readAt": "2026-09-15T08:00:00Z",
            "handoffSha256": manifest["sha256"],
            "documentHashes": {d["id"]: d["sha256"] for d in manifest["documents"]},
            "scopeSummary": "验证付款登记与重复提交的既定规则，不改变权限。",
            "exclusions": manifest["exclusions"],
            "acceptanceIds": manifest["requiredAcceptanceIds"],
            "engineeringDecisions": [{"id": "ED-1", "status": "CONFIRMED",
                "owner": "dev-owner", "conclusion": "沿用已核验的幂等与权限约束",
                "evidence": "https://example.test/decision/ED-1",
                "blockingStages": ["development", "qa", "release"]}],
            "reviewer": role + "-owner", "reviewEvidence": "https://example.test/review/1",
        })
    bundle = {"schemaVersion": "oneos.handoff-evidence/v1", "manifest": manifest,
              "developmentReceipt": receipt("development", "DEV-1"),
              "deliveryVersion": "commit:abc123"}
    if stage != "development":
        bundle["qaReceipt"] = receipt("qa", "TEST-1")
    if stage in {"release", "qa-complete"}:
        bundle["qaResult"] = {"formal": True, "environment": "test",
            "deliveryVersion": "commit:abc123", "executionId": "RUN-1",
            "evidence": "https://example.test/test/RUN-1",
            "cases": [{"acceptanceId": key, "result": "PASS",
                       "evidence": "https://example.test/test/" + key}
                      for key in manifest["requiredAcceptanceIds"]]}
    return bundle
