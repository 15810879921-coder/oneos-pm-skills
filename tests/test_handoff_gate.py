from __future__ import annotations

import copy
import importlib.util
import unittest
from pathlib import Path

from handoff_fixtures import make_bundle, seal

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "handoff_gate", ROOT / "skills/YunxiaoPM/scripts/handoff_gate.py")
hg = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(hg)


class HandoffGateTests(unittest.TestCase):
    def test_valid_scoped_bundle_at_each_stage(self):
        for stage in ("development", "qa-start", "qa-complete", "release"):
            with self.subTest(stage=stage):
                self.assertEqual(make_bundle(stage), hg.validate_bundle(make_bundle(stage), stage))

    def test_missing_material_or_hash_tampering_blocks(self):
        for field in ("manifest", "developmentReceipt", "qaReceipt", "qaResult"):
            b = make_bundle()
            b.pop(field)
            with self.subTest(field=field), self.assertRaises(ValueError):
                hg.validate_bundle(b, "release")
        b = make_bundle()
        b["manifest"]["version"] = "2"
        with self.assertRaises(ValueError):
            hg.validate_bundle(b, "release")

    def test_old_receipt_wrong_scope_wrong_commit_and_missing_read_block(self):
        mutations = [
            lambda b: b["qaReceipt"].update(handoffSha256="f" * 64),
            lambda b: b["qaReceipt"]["documentHashes"].pop("product-contract"),
            lambda b: b["qaResult"].update(deliveryVersion="commit:new"),
            lambda b: b["qaReceipt"].update(acceptanceIds=["AC-1"]),
            lambda b: b["qaReceipt"].update(exclusions=[]),
        ]
        for change in mutations:
            b = make_bundle(); change(b); b["qaReceipt"] = seal(b["qaReceipt"])
            with self.assertRaises(ValueError):
                hg.validate_bundle(b, "release")
        with self.assertRaises(ValueError):
            hg.validate_bundle(make_bundle(), "release", {"requirementId": "OTHER"})

    def test_nonformal_prototype_notrun_failed_duplicate_or_missing_cases_block(self):
        mutations = [
            lambda r: r.update(formal=False), lambda r: r.update(environment="prototype"),
            lambda r: r["cases"][0].update(result="NOT_RUN"),
            lambda r: r["cases"][0].update(result="FAIL"),
            lambda r: r["cases"].pop(),
            lambda r: r["cases"].append(copy.deepcopy(r["cases"][0])),
            lambda r: r["cases"][0].update(evidence=""),
        ]
        for change in mutations:
            b = make_bundle(); change(b["qaResult"])
            with self.assertRaises(ValueError):
                hg.validate_bundle(b, "release")

    def test_pending_blocks_affected_stage_but_not_unrelated_work(self):
        b = make_bundle()
        decision = b["developmentReceipt"]["engineeringDecisions"][0]
        decision.update(status="PENDING", blockingStages=["release"])
        b["developmentReceipt"] = seal(b["developmentReceipt"])
        hg.validate_bundle(b, "development")
        with self.assertRaises(ValueError):
            hg.validate_bundle(b, "release")

    def test_required_engineering_decision_cannot_be_omitted(self):
        b = make_bundle()
        b["manifest"]["requiredDecisionIds"].append("ED-2")
        b["manifest"] = seal(b["manifest"])
        for key in ("developmentReceipt", "qaReceipt"):
            b[key]["handoffSha256"] = b["manifest"]["sha256"]
            b[key] = seal(b[key])
        with self.assertRaisesRegex(ValueError, "工程决策检查项"):
            hg.validate_bundle(b, "release")

    def test_product_scope_upsert_preserves_other_delivery_and_manual_text(self):
        first = make_bundle()["manifest"]
        second = copy.deepcopy(first)
        second["scope"].update(deliveryId="DEL-2", scopeId="SCOPE-2")
        second = seal(second)
        text = hg.upsert_manifest("人工文字", first)
        text = hg.upsert_manifest(text, second)
        self.assertEqual(text, hg.upsert_manifest(text, second))
        self.assertIn("人工文字", text)
        self.assertEqual(first, hg.manifest_from_description(text, first["scope"]))
        self.assertEqual(second, hg.manifest_from_description(text, second["scope"]))

    def test_duplicate_managed_blocks_and_wrong_workitem_identity_block(self):
        b = make_bundle()
        text = hg.upsert_bundle("", b)
        with self.assertRaises(ValueError):
            hg.bundle_from_description(text + text)
        with self.assertRaises(ValueError):
            hg.verify_live_bundle(b, "release", lambda i: {"id": "wrong"})

    def test_current_live_sources_are_checked_again_at_use(self):
        b = make_bundle()
        scope = b["manifest"]["scope"]
        docs = {i: {"id": i, "description": hg.upsert_manifest("", b["manifest"])}
                for i in (scope["requirementId"], scope["deliveryId"])}
        docs["DEV-1"] = {"id": "DEV-1", "description": hg.upsert_bundle("", make_bundle("development"))}
        docs["TEST-1"] = {"id": "TEST-1", "description": hg.upsert_bundle("", b)}
        hg.verify_live_bundle(b, "release", docs.__getitem__)
        newer = copy.deepcopy(b["manifest"]); newer["version"] = "2"; newer = seal(newer)
        docs["REQ-1"]["description"] = hg.upsert_manifest("", newer)
        with self.assertRaises(ValueError):
            hg.verify_live_bundle(b, "release", docs.__getitem__)

    def test_document_bytes_are_checked_not_just_a_declared_hash(self):
        m = make_bundle()["manifest"]
        hg.verify_documents(m, lambda d: d["kind"].encode())
        with self.assertRaises(ValueError):
            hg.verify_documents(m, lambda d: b"changed after preflight")


if __name__ == "__main__":
    unittest.main()
