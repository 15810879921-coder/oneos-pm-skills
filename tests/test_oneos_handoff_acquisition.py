import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "skills" / "oneos-dev-delivery" / "scripts" / "validate_handoff_acquisition.py"
SPEC = importlib.util.spec_from_file_location("validate_handoff_acquisition", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def manifest(materials=None):
    return {
        "schema": "oneos.handoff-materials/v1",
        "packageId": "HANDOFF-1",
        "waveId": "P0",
        "materials": materials
        or [
            {
                "id": "prototype",
                "type": "online-prototype",
                "required": True,
                "source": "https://example.test/prototype",
                "acquisitionMethod": "browser_route_state_walk",
                "expectedCoverage": {
                    "routes": ["/list", "/detail"],
                    "states": ["list", "detail", "edit"],
                    "viewports": ["1440x900"],
                },
            }
        ],
    }


def receipt(results, status="complete", allowed=True, material_count=1, required_count=1, verified_count=1):
    return {
        "schema": "oneos.handoff-acquisition-receipt/v1",
        "packageId": "HANDOFF-1",
        "status": status,
        "allowedToParse": allowed,
        "manifestMaterialCount": material_count,
        "requiredMaterialCount": required_count,
        "verifiedRequiredCount": verified_count,
        "materialResults": results,
    }


def verified_prototype(states=None):
    return {
        "id": "prototype",
        "status": "verified",
        "evidence": {
            "method": "browser_route_state_walk",
            "finalSource": "https://example.test/prototype",
            "coverage": {
                "routes": ["/list", "/detail"],
                "states": states or ["list", "detail", "edit"],
                "viewports": ["1440x900"],
            },
        },
    }


class HandoffAcquisitionTests(unittest.TestCase):
    def test_complete_receipt_passes(self):
        result = MODULE.evaluate(manifest(), receipt([verified_prototype()]))
        self.assertTrue(result["valid"])
        self.assertEqual("complete", result["status"])
        self.assertTrue(result["allowedToParse"])

    def test_missing_required_material_blocks(self):
        result = MODULE.evaluate(
            manifest(),
            receipt([], status="incomplete", allowed=False, verified_count=0),
        )
        self.assertTrue(result["valid"])
        self.assertEqual("incomplete", result["status"])
        self.assertEqual(["prototype"], result["missingRequired"])

    def test_false_complete_claim_is_invalid(self):
        partial = {"id": "prototype", "status": "partial", "evidence": {}}
        result = MODULE.evaluate(manifest(), receipt([partial]))
        self.assertFalse(result["valid"])
        self.assertEqual("incomplete", result["computedStatus"])

    def test_missing_prototype_state_is_conflict(self):
        result = MODULE.evaluate(
            manifest(),
            receipt([verified_prototype(states=["list", "detail"])], status="conflict", allowed=False, verified_count=0),
        )
        self.assertTrue(result["valid"])
        self.assertEqual("conflict", result["status"])
        self.assertIn("edit", " ".join(result["conflicts"]))

    def test_required_prototype_scope_is_required(self):
        prototype = manifest()["materials"][0]
        prototype.pop("expectedCoverage")
        result = MODULE.evaluate(manifest([prototype]), None)
        self.assertFalse(result["valid"])
        self.assertIn("materials[0].expectedCoverage.routes is required for an online prototype", result["errors"])

    def test_duplicate_material_ids_are_rejected(self):
        item = manifest()["materials"][0]
        result = MODULE.evaluate(manifest([item, dict(item)]), None)
        self.assertFalse(result["valid"])
        self.assertIn("duplicate material ids: prototype", result["errors"])

    def test_package_id_mismatch_is_rejected(self):
        bad_receipt = receipt([verified_prototype()])
        bad_receipt["packageId"] = "HANDOFF-OTHER"
        result = MODULE.evaluate(manifest(), bad_receipt)
        self.assertFalse(result["valid"])
        self.assertIn("receipt packageId does not match manifest", result["errors"])

    def test_optional_material_can_be_absent(self):
        materials = manifest()["materials"] + [
            {
                "id": "screenshot",
                "type": "image",
                "required": False,
                "source": "optional.png",
                "acquisitionMethod": "local_image_view",
            }
        ]
        result = MODULE.evaluate(
            manifest(materials),
            receipt([verified_prototype()], material_count=2),
        )
        self.assertTrue(result["valid"])
        self.assertEqual("complete", result["status"])

    def test_legacy_handoff_is_not_allowed_to_parse(self):
        result = MODULE.evaluate(None, None)
        self.assertTrue(result["valid"])
        self.assertEqual("legacy-unverified", result["status"])
        self.assertFalse(result["allowedToParse"])

    def test_local_hash_mismatch_is_conflict(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            handoff_path = root / "handoff.md"
            source_path = root / "prd.md"
            handoff_path.write_text("handoff", encoding="utf-8")
            source_path.write_text("actual", encoding="utf-8")
            local_manifest = manifest(
                [
                    {
                        "id": "prd",
                        "type": "markdown",
                        "required": True,
                        "source": "prd.md",
                        "acquisitionMethod": "local_file_raw",
                        "expected": {"sha256": "0" * 64},
                        "expectedCoverage": {"eof": True},
                    }
                ]
            )
            local_receipt = receipt(
                [
                    {
                        "id": "prd",
                        "status": "verified",
                        "evidence": {
                            "method": "local_file_raw",
                            "finalSource": "prd.md",
                            "bytes": source_path.stat().st_size,
                            "coverage": {"eof": True},
                        },
                    }
                ],
                status="conflict",
                allowed=False,
                verified_count=0,
            )
            result = MODULE.evaluate(local_manifest, local_receipt, handoff_path)
            self.assertTrue(result["valid"])
            self.assertEqual("conflict", result["status"])
            self.assertIn("sha256 mismatch", " ".join(result["conflicts"]))

    def test_repo_relative_local_source_resolves_from_git_root(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / ".git").mkdir()
            nested = root / "handoffs" / "wave"
            nested.mkdir(parents=True)
            handoff_path = nested / "handoff.md"
            handoff_path.write_text("handoff", encoding="utf-8")
            source_path = root / "docs" / "prd.md"
            source_path.parent.mkdir()
            source_path.write_text("complete", encoding="utf-8")
            local_manifest = manifest(
                [
                    {
                        "id": "prd",
                        "type": "markdown",
                        "required": True,
                        "source": "docs/prd.md",
                        "acquisitionMethod": "local_file_raw",
                        "expectedCoverage": {"eof": True},
                    }
                ]
            )
            local_receipt = receipt(
                [
                    {
                        "id": "prd",
                        "status": "verified",
                        "evidence": {
                            "method": "local_file_raw",
                            "finalSource": "docs/prd.md",
                            "bytes": source_path.stat().st_size,
                            "coverage": {"eof": True},
                        },
                    }
                ]
            )
            result = MODULE.evaluate(local_manifest, local_receipt, handoff_path)
            self.assertTrue(result["valid"])
            self.assertEqual("complete", result["status"])

    def test_markdown_fences_are_parsed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            handoff_path = root / "handoff.md"
            receipt_path = root / "receipt.md"
            handoff_path.write_text(
                "```handoff-manifest\n" + json.dumps(manifest()) + "\n```\n",
                encoding="utf-8",
            )
            receipt_path.write_text(
                "```handoff-acquisition\n" + json.dumps(receipt([verified_prototype()])) + "\n```\n",
                encoding="utf-8",
            )
            result = MODULE.validate_files(handoff_path, receipt_path)
            self.assertEqual("complete", result["status"])


if __name__ == "__main__":
    unittest.main()
