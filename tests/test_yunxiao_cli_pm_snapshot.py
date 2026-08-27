import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "YunxiaoPM" / "scripts"
sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location(
    "yunxiao_cli_pm", SCRIPTS / "yunxiao_cli_pm.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


SNAPSHOT_CONTENT = """# 产品交棒快照

## 变更范围
- 本次修改车辆故障登记页面、故障等级规则和异常提示。
- 其他车辆档案与发布流程保持不变。

## PRD版本
- 来源：requirements-prd.md
- 版本证据：sha256=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
- 关键章节：故障登记、等级规则、异常处理。

## 原型版本
- 入口：https://example.test/fault/index.html
- manifest：https://example.test/fault/source/manifest.json
- annotation-source：https://example.test/fault/source/annotation-source.json
- 版本证据：sha256=bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb

## 页面与交互索引
- Web / 故障登记 / 默认、提交失败、权限不足状态。

## 验收入口
- PRD 的验收剧本章节及原型故障登记入口。

## 未决风险
- 无。
"""


class ProductSnapshotTests(unittest.TestCase):
    def test_snapshot_is_hashed_and_managed_idempotently(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "snapshot.md"
            path.write_text(SNAPSHOT_CONTENT, encoding="utf-8")
            snapshot = MODULE.load_product_snapshot(str(path))
        first, format_type = MODULE.managed_product_snapshot_description(
            "人工产品说明", "MARKDOWN", snapshot, "ONEOS-545", "ONEOS-600")
        second, second_format = MODULE.managed_product_snapshot_description(
            first, format_type, snapshot, "ONEOS-545", "ONEOS-600")

        self.assertEqual("MARKDOWN", format_type)
        self.assertEqual(format_type, second_format)
        self.assertEqual(first, second)
        self.assertEqual(1, first.count("## 产品交棒快照"))
        self.assertIn(snapshot["snapshotId"], first)
        self.assertIn(f"sha256={snapshot['sha256']}", first)
        self.assertIn("人工产品说明", first)

    def test_richtext_snapshot_preserves_format(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "snapshot.md"
            path.write_text(SNAPSHOT_CONTENT, encoding="utf-8")
            snapshot = MODULE.load_product_snapshot(str(path))
        value, format_type = MODULE.managed_product_snapshot_description(
            "<p>人工说明</p>", "RICHTEXT", snapshot, "ONEOS-545", "ONEOS-600")
        self.assertEqual("RICHTEXT", format_type)
        self.assertIn("<h2>产品交棒快照</h2>", value)
        self.assertIn("<p>人工说明</p>", value)

    def test_missing_section_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "snapshot.md"
            path.write_text(SNAPSHOT_CONTENT.replace("## 验收入口", "## 其他"),
                            encoding="utf-8")
            with self.assertRaises(MODULE.core.AdapterError):
                MODULE.load_product_snapshot(str(path))

    def test_standard_preflight_remains_backward_compatible(self):
        parsed = MODULE.parser().parse_args([
            "preflight-standard", "--space-id", "space", "--project-name", "OneOS",
            "--subject", "示例", "--description-file", "requirement.md",
            "--delivery-file", "delivery.md",
            "--priority", "中", "--label", "故障管理", "--delivery-owner", "交付甲",
            "--stage-owner", "阶段乙", "--sprint-name", "V1.0.0",
            "--start-date", "2026-08-21", "--end-date", "2026-08-22",
            "--idempotency-key", "example",
        ])
        self.assertEqual("preflight-standard", parsed.command)
        self.assertFalse(hasattr(parsed, "product_snapshot_file"))

    def test_product_snapshot_uses_dedicated_preflight(self):
        parsed = MODULE.parser().parse_args([
            "preflight-product-snapshot", "--space-id", "space",
            "--project-name", "OneOS", "--requirement-id", "ONEOS-545",
            "--delivery-id", "ONEOS-600", "--snapshot-file", "snapshot.md",
        ])
        self.assertEqual("preflight-product-snapshot", parsed.command)
        self.assertEqual("snapshot.md", parsed.snapshot_file)

    def test_project_name_can_be_derived_from_explicit_project_id(self):
        parsed = MODULE.parser().parse_args([
            "preflight-product-snapshot", "--space-id", "space-1",
            "--requirement-id", "ONEOS-545", "--delivery-id", "ONEOS-600",
            "--snapshot-file", "snapshot.md",
        ])
        self.assertIsNone(parsed.project_name)
        with mock.patch.object(MODULE, "get_project", return_value={
                "id": "space-1", "name": "01_ONEOS", "logicalStatus": "NORMAL"}):
            project, name = MODULE.verified_project(
                "aliyun", parsed.space_id, parsed.project_name)
        self.assertEqual("space-1", project["id"])
        self.assertEqual("01_ONEOS", name)

    def test_owner_accepts_unique_name_or_user_id(self):
        members = [
            {"name": "交付甲", "userId": "u-1"},
            {"name": "阶段乙", "userId": "u-2"},
        ]

        def fake_run(_executable, argv):
            needle = argv[2]
            return [row for row in members
                    if needle in {row["name"], row["userId"]}]

        with mock.patch.object(MODULE.core, "run_devops", side_effect=fake_run):
            self.assertEqual(
                {"id": "u-1", "name": "交付甲"},
                MODULE.exact_member("aliyun", "交付甲"))
            self.assertEqual(
                {"id": "u-2", "name": "阶段乙"},
                MODULE.exact_member("aliyun", "u-2"))

    def test_fixed_person_cookie_writer_is_disabled(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "live_create_fast.py")],
            capture_output=True, text=True, encoding="utf-8", check=False)
        self.assertEqual(2, result.returncode)
        self.assertIn("LEGACY_ENTRY_DISABLED", result.stdout)


if __name__ == "__main__":
    unittest.main()
