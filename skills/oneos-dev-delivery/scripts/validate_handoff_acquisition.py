#!/usr/bin/env python3
"""Validate a OneOS handoff manifest and acquisition receipt."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


MANIFEST_SCHEMA = "oneos.handoff-materials/v1"
RECEIPT_SCHEMA = "oneos.handoff-acquisition-receipt/v1"
RESULT_STATUSES = {"verified", "missing", "partial", "conflict", "inaccessible"}
RECEIPT_STATUSES = {"complete", "incomplete", "conflict", "legacy-unverified"}


def _extract_json_fence(text: str, language: str) -> tuple[dict[str, Any] | None, list[str]]:
    blocks = re.findall(rf"```{re.escape(language)}\s*\r?\n(.*?)\r?\n```", text, re.DOTALL)
    if not blocks:
        return None, []
    if len(blocks) != 1:
        return None, [f"expected exactly one {language} block, found {len(blocks)}"]
    try:
        value = json.loads(blocks[0])
    except json.JSONDecodeError as exc:
        return None, [f"invalid {language} JSON: {exc.msg} at line {exc.lineno}"]
    if not isinstance(value, dict):
        return None, [f"{language} block must contain a JSON object"]
    return value, []


def _duplicates(values: list[str]) -> list[str]:
    seen: set[str] = set()
    repeated: set[str] = set()
    for value in values:
        if value in seen:
            repeated.add(value)
        seen.add(value)
    return sorted(repeated)


def validate_manifest(manifest: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if manifest.get("schema") != MANIFEST_SCHEMA:
        errors.append(f"manifest schema must be {MANIFEST_SCHEMA}")
    for field in ("packageId", "waveId"):
        if not isinstance(manifest.get(field), str) or not manifest[field].strip():
            errors.append(f"manifest {field} is required")
    materials = manifest.get("materials")
    if not isinstance(materials, list) or not materials:
        return errors + ["manifest materials must be a non-empty array"]
    ids: list[str] = []
    for index, material in enumerate(materials):
        prefix = f"materials[{index}]"
        if not isinstance(material, dict):
            errors.append(f"{prefix} must be an object")
            continue
        material_id = material.get("id")
        if not isinstance(material_id, str) or not material_id.strip():
            errors.append(f"{prefix}.id is required")
        else:
            ids.append(material_id)
        if not isinstance(material.get("required"), bool):
            errors.append(f"{prefix}.required must be boolean")
        for field in ("type", "source", "acquisitionMethod"):
            if not isinstance(material.get(field), str) or not material[field].strip():
                errors.append(f"{prefix}.{field} is required")
        expected_coverage = material.get("expectedCoverage")
        if expected_coverage is not None and not isinstance(expected_coverage, dict):
            errors.append(f"{prefix}.expectedCoverage must be an object")
        if material.get("required") and material.get("type") == "online-prototype":
            coverage = expected_coverage if isinstance(expected_coverage, dict) else {}
            for field in ("routes", "states", "viewports"):
                if not isinstance(coverage.get(field), list) or not coverage[field]:
                    errors.append(f"{prefix}.expectedCoverage.{field} is required for an online prototype")
        if material.get("required") and material.get("type") in {"markdown", "text"}:
            coverage = expected_coverage if isinstance(expected_coverage, dict) else {}
            if coverage.get("eof") is not True:
                errors.append(f"{prefix}.expectedCoverage.eof must be true for complete text acquisition")
    duplicate_ids = _duplicates(ids)
    if duplicate_ids:
        errors.append(f"duplicate material ids: {', '.join(duplicate_ids)}")
    return errors


def _missing_coverage(expected: dict[str, Any], actual: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    for key, expected_value in expected.items():
        actual_value = actual.get(key)
        if isinstance(expected_value, list):
            actual_items = actual_value if isinstance(actual_value, list) else []
            absent = [item for item in expected_value if item not in actual_items]
            if absent:
                missing.append(f"{key}={absent}")
        elif actual_value != expected_value:
            missing.append(f"{key}={expected_value!r}")
    return missing


def _is_local_source(source: str) -> bool:
    parsed = urlparse(source)
    return parsed.scheme == "" and source not in {"this-document", "inline"}


def _resolve_local_source(source: str, handoff_path: Path) -> Path:
    candidate = Path(source)
    if candidate.is_absolute():
        return candidate
    if source.startswith(("./", "../", ".\\", "..\\")):
        return handoff_path.parent / candidate
    for parent in (handoff_path.parent, *handoff_path.parents):
        if (parent / ".git").exists():
            return parent / candidate
    return handoff_path.parent / candidate


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _verify_local_evidence(
    material: dict[str, Any], result: dict[str, Any], handoff_path: Path | None
) -> list[str]:
    if handoff_path is None or not _is_local_source(str(material.get("source", ""))):
        return []
    evidence = result.get("evidence") if isinstance(result.get("evidence"), dict) else {}
    final_source = evidence.get("finalSource") or material.get("source")
    candidate = _resolve_local_source(str(final_source), handoff_path)
    if not candidate.exists() or not candidate.is_file():
        return [f"local source not found: {candidate}"]
    errors: list[str] = []
    expected = material.get("expected") if isinstance(material.get("expected"), dict) else {}
    actual_bytes = candidate.stat().st_size
    evidence_bytes = evidence.get("bytes")
    if not isinstance(evidence_bytes, int) or evidence_bytes < 0:
        errors.append("local evidence bytes is required")
    elif evidence_bytes != actual_bytes:
        errors.append(f"local evidence bytes mismatch: reported {evidence_bytes}, got {actual_bytes}")
    expected_bytes = expected.get("bytes")
    if isinstance(expected_bytes, int) and expected_bytes > 0 and actual_bytes != expected_bytes:
        errors.append(f"local bytes mismatch: expected {expected_bytes}, got {actual_bytes}")
    expected_sha = expected.get("sha256")
    evidence_sha = evidence.get("sha256")
    if (isinstance(expected_sha, str) and expected_sha.strip()) or (isinstance(evidence_sha, str) and evidence_sha.strip()):
        actual_sha = _sha256_file(candidate)
    if isinstance(expected_sha, str) and expected_sha.strip():
        if actual_sha.lower() != expected_sha.lower():
            errors.append("local sha256 mismatch")
    if isinstance(evidence_sha, str) and evidence_sha.strip() and actual_sha.lower() != evidence_sha.lower():
        errors.append("local evidence sha256 mismatch")
    return errors


def evaluate(
    manifest: dict[str, Any] | None,
    receipt: dict[str, Any] | None,
    handoff_path: Path | None = None,
) -> dict[str, Any]:
    if manifest is None:
        return {
            "valid": True,
            "status": "legacy-unverified",
            "allowedToParse": False,
            "errors": [],
            "missingRequired": [],
            "message": "handoff-manifest missing; build a temporary inventory and verify it before parsing",
        }

    errors = validate_manifest(manifest)
    if errors:
        return {"valid": False, "status": "invalid", "allowedToParse": False, "errors": errors}

    materials = manifest["materials"]
    required = [item for item in materials if item["required"]]
    if receipt is None:
        return {
            "valid": True,
            "status": "incomplete",
            "allowedToParse": False,
            "errors": [],
            "missingRequired": [item["id"] for item in required],
            "message": "acquisition receipt missing",
        }

    if receipt.get("schema") != RECEIPT_SCHEMA:
        errors.append(f"receipt schema must be {RECEIPT_SCHEMA}")
    if receipt.get("packageId") != manifest.get("packageId"):
        errors.append("receipt packageId does not match manifest")
    if receipt.get("status") not in RECEIPT_STATUSES:
        errors.append(f"receipt status must be one of {sorted(RECEIPT_STATUSES)}")
    if not isinstance(receipt.get("allowedToParse"), bool):
        errors.append("receipt allowedToParse must be boolean")

    results = receipt.get("materialResults")
    if not isinstance(results, list):
        errors.append("receipt materialResults must be an array")
        results = []
    result_ids = [item.get("id") for item in results if isinstance(item, dict) and isinstance(item.get("id"), str)]
    duplicate_result_ids = _duplicates(result_ids)
    if duplicate_result_ids:
        errors.append(f"duplicate receipt material ids: {', '.join(duplicate_result_ids)}")
    result_by_id = {item["id"]: item for item in results if isinstance(item, dict) and isinstance(item.get("id"), str)}

    missing_required: list[str] = []
    conflicts: list[str] = []
    verified_required = 0
    for material in materials:
        material_id = material["id"]
        result = result_by_id.get(material_id)
        if result is None:
            if material["required"]:
                missing_required.append(material_id)
            continue
        status = result.get("status")
        if status not in RESULT_STATUSES:
            errors.append(f"material result {material_id} has invalid status")
            continue
        evidence = result.get("evidence")
        if status == "verified" and not isinstance(evidence, dict):
            errors.append(f"verified material {material_id} requires evidence")
            continue
        if status == "verified":
            method = evidence.get("method")
            if method != material.get("acquisitionMethod"):
                conflicts.append(f"{material_id}: acquisition method mismatch")
            expected_coverage = material.get("expectedCoverage", {})
            actual_coverage = evidence.get("coverage", {}) if isinstance(evidence.get("coverage"), dict) else {}
            coverage_gaps = _missing_coverage(expected_coverage, actual_coverage)
            if coverage_gaps:
                conflicts.append(f"{material_id}: missing coverage {', '.join(coverage_gaps)}")
            local_errors = _verify_local_evidence(material, result, handoff_path)
            conflicts.extend(f"{material_id}: {message}" for message in local_errors)
            if not coverage_gaps and not local_errors and method == material.get("acquisitionMethod") and material["required"]:
                verified_required += 1
        elif status == "conflict":
            conflicts.append(f"{material_id}: receipt reports conflict")
        elif material["required"]:
            missing_required.append(material_id)

    actual_status = "conflict" if conflicts else ("complete" if not missing_required and verified_required == len(required) else "incomplete")
    actual_allowed = actual_status == "complete"
    expected_counts = {
        "manifestMaterialCount": len(materials),
        "requiredMaterialCount": len(required),
        "verifiedRequiredCount": verified_required,
    }
    for field, expected_value in expected_counts.items():
        if receipt.get(field) != expected_value:
            errors.append(f"receipt {field} must be {expected_value}")
    if receipt.get("status") != actual_status:
        errors.append(f"receipt status claims {receipt.get('status')!r}, computed status is {actual_status!r}")
    if receipt.get("allowedToParse") != actual_allowed:
        errors.append(f"receipt allowedToParse must be {str(actual_allowed).lower()}")

    return {
        "valid": not errors,
        "status": actual_status if not errors else "invalid",
        "computedStatus": actual_status,
        "allowedToParse": actual_allowed and not errors,
        "errors": errors,
        "missingRequired": sorted(set(missing_required)),
        "conflicts": conflicts,
        **expected_counts,
    }


def validate_files(handoff_path: Path, receipt_path: Path | None = None) -> dict[str, Any]:
    handoff_text = handoff_path.read_text(encoding="utf-8")
    manifest, manifest_errors = _extract_json_fence(handoff_text, "handoff-manifest")
    if manifest_errors:
        return {"valid": False, "status": "invalid", "allowedToParse": False, "errors": manifest_errors}
    receipt = None
    if receipt_path is not None:
        receipt_text = receipt_path.read_text(encoding="utf-8")
        receipt, receipt_errors = _extract_json_fence(receipt_text, "handoff-acquisition")
        if receipt_errors:
            return {"valid": False, "status": "invalid", "allowedToParse": False, "errors": receipt_errors}
    return evaluate(manifest, receipt, handoff_path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--handoff", required=True, type=Path)
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()
    try:
        result = validate_files(args.handoff, args.receipt)
    except (OSError, UnicodeError) as exc:
        result = {"valid": False, "status": "invalid", "allowedToParse": False, "errors": [str(exc)]}
    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"status={result['status']} allowedToParse={str(result['allowedToParse']).lower()}")
        for error in result.get("errors", []):
            print(f"ERROR: {error}")
    if not result.get("valid"):
        return 1
    return 0 if result.get("allowedToParse") else 2


if __name__ == "__main__":
    sys.exit(main())
