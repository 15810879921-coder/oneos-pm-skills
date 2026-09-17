from __future__ import annotations

import argparse
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import accept_release as acceptance  # noqa: E402
import yunxiao_cli_pm as pm  # noqa: E402
import yunxiao_cli_runtime as core  # noqa: E402


def sprint(identifier: str, name: str, start: str, end: str) -> dict:
    return {
        "id": identifier,
        "name": name,
        "startDate": start,
        "endDate": end,
        "status": "DOING",
        "owners": [{"id": "owner-1"}],
    }


class FollowupSprintSpecTests(unittest.TestCase):
    def test_get_sprint_rejects_response_for_different_id(self) -> None:
        with mock.patch.object(
            pm.core, "run_devops", return_value={"id": "other-sprint"},
        ):
            with self.assertRaisesRegex(core.AdapterError, "回读ID与请求不一致"):
                pm.get_sprint("aliyun", "p1", "expected-sprint")

    def test_sprint_timestamp_uses_asia_shanghai_business_date(self) -> None:
        self.assertEqual(
            pm.sprint_day(1789315200000, "start").isoformat(), "2026-09-14"
        )
        self.assertEqual(
            pm.sprint_day("2026-09-13T16:00:00Z", "start").isoformat(),
            "2026-09-14",
        )

    def test_web_patch_targets_preserve_prefix_and_inclusive_cadence(self) -> None:
        source = sprint("s11", "OneOS Web端V1.4.11", "2026-09-14", "2026-09-28")
        self.assertEqual(
            pm.build_followup_sprint_specs(source),
            [
                {"name": "OneOS Web端V1.4.12", "startDate": "2026-09-29", "endDate": "2026-10-13"},
                {"name": "OneOS Web端V1.4.13", "startDate": "2026-10-14", "endDate": "2026-10-28"},
            ],
        )

    def test_non_web_or_non_version_source_is_rejected(self) -> None:
        with self.assertRaisesRegex(core.AdapterError, "仅适用于Web"):
            pm.build_followup_sprint_specs(
                sprint("mini", "OneOS 小程序端V1.4.11", "2026-09-14", "2026-09-28")
            )
        with self.assertRaisesRegex(core.AdapterError, "不是受支持"):
            pm.build_followup_sprint_specs(
                sprint("bi", "BI报表", "2026-09-14", "2026-09-28")
            )

    @mock.patch.object(pm, "list_sprints")
    @mock.patch.object(pm, "get_sprint")
    @mock.patch.object(pm, "verified_project")
    def test_exact_existing_target_is_reused_and_mismatch_is_rejected(
        self, verified_project, get_sprint, list_sprints
    ) -> None:
        source = sprint("s11", "OneOS Web端V1.4.11", "2026-09-14", "2026-09-28")
        target = sprint("s12", "OneOS Web端V1.4.12", "2026-09-29", "2026-10-13")
        verified_project.return_value = ({"id": "p1"}, "01_ONEOS")
        list_sprints.return_value = [source, target]
        get_sprint.side_effect = lambda _exe, _project, identifier: {
            "s11": source,
            "s12": target,
        }[identifier]
        scope = pm.build_followup_scope("aliyun", "p1", "s11", "accept-key")
        self.assertEqual(scope["targets"][0]["result"], "idempotent")
        self.assertEqual(scope["targets"][1]["result"], "create")

        target["endDate"] = "2026-10-14"
        with self.assertRaisesRegex(core.AdapterError, "日期.*漂移"):
            pm.build_followup_scope("aliyun", "p1", "s11", "accept-key")

    def test_apply_uses_frozen_targets_and_never_updates_old_sprints(self) -> None:
        source = {
            "id": "s11", "name": "OneOS Web端V1.4.11", "endpoint": "Web",
            "startDate": "2026-09-14", "endDate": "2026-09-28", "version": "1.4.11",
            "ownerIds": ["owner-1"],
        }
        targets = [
            {"name": "OneOS Web端V1.4.12", "startDate": "2026-09-29", "endDate": "2026-10-13", "existing": None, "result": "create"},
            {"name": "OneOS Web端V1.4.13", "startDate": "2026-10-14", "endDate": "2026-10-28", "existing": None, "result": "create"},
        ]
        scope = {
            "project": {"id": "p1", "name": "01_ONEOS"},
            "source": source,
            "targets": targets,
            "idempotencyKey": "accept-key",
        }
        plan = {"schema": pm.SCHEMA, "command": "preflight-followup-sprints", "createdAt": "now", "liveScope": scope}
        plan["preflightHash"] = pm.canonical_hash(plan, {"preflightHash"})
        created_by_name = {
            "OneOS Web端V1.4.12": sprint("s12", "OneOS Web端V1.4.12", "2026-09-29", "2026-10-13"),
            "OneOS Web端V1.4.13": sprint("s13", "OneOS Web端V1.4.13", "2026-10-14", "2026-10-28"),
        }
        calls: list[list[str]] = []

        def run_devops(_executable: str, arguments: list[str]):
            calls.append(arguments)
            name = arguments[arguments.index("--name") + 1]
            return {"id": created_by_name[name]["id"]}

        with tempfile.TemporaryDirectory() as temp:
            preflight = Path(temp) / "plan.json"
            receipt = Path(temp) / "receipt.json"
            preflight.write_text(json.dumps(plan), encoding="utf-8")
            with (
                mock.patch.object(pm, "build_followup_scope", return_value=scope),
                mock.patch.object(pm.core, "run_devops", side_effect=run_devops),
                mock.patch.object(pm, "get_sprint", side_effect=lambda _e, _p, identifier: {
                    "s12": created_by_name["OneOS Web端V1.4.12"],
                    "s13": created_by_name["OneOS Web端V1.4.13"],
                }[identifier]),
            ):
                result = pm.apply_followup_preflight("aliyun", preflight, receipt)
        self.assertEqual([row["result"] for row in result["targets"]], ["created", "created"])
        self.assertTrue(all(call[0] == "projex-create-sprint" for call in calls))
        self.assertFalse(any("update" in call[0] for call in calls))

    def test_created_target_owner_mismatch_keeps_receipt_incomplete(self) -> None:
        source = {
            "id": "s11", "name": "OneOS Web端V1.4.11", "endpoint": "Web",
            "startDate": "2026-09-14", "endDate": "2026-09-28", "version": "1.4.11",
            "ownerIds": ["owner-1"],
        }
        scope = {
            "project": {"id": "p1", "name": "01_ONEOS"},
            "source": source,
            "targets": [
                {"name": "OneOS Web端V1.4.12", "startDate": "2026-09-29", "endDate": "2026-10-13", "existing": None, "result": "create"},
                {"name": "OneOS Web端V1.4.13", "startDate": "2026-10-14", "endDate": "2026-10-28", "existing": None, "result": "create"},
            ],
            "idempotencyKey": "accept-key",
        }
        plan = {
            "schema": pm.SCHEMA, "command": "preflight-followup-sprints",
            "createdAt": "now", "liveScope": scope,
        }
        plan["preflightHash"] = pm.canonical_hash(plan, {"preflightHash"})
        wrong_owner = sprint(
            "s12", "OneOS Web端V1.4.12", "2026-09-29", "2026-10-13"
        )
        wrong_owner["owners"] = [{"id": "owner-2"}]
        with tempfile.TemporaryDirectory() as temp:
            preflight = Path(temp) / "plan.json"
            receipt = Path(temp) / "receipt.json"
            preflight.write_text(json.dumps(plan), encoding="utf-8")
            with (
                mock.patch.object(pm, "build_followup_scope", return_value=scope),
                mock.patch.object(pm.core, "run_devops", return_value={"id": "s12"}),
                mock.patch.object(pm, "get_sprint", return_value=wrong_owner),
            ):
                with self.assertRaisesRegex(core.AdapterError, "创建后回读不一致"):
                    pm.apply_followup_preflight("aliyun", preflight, receipt)
            saved = json.loads(receipt.read_text(encoding="utf-8"))
        self.assertFalse(saved["complete"])
        self.assertEqual(saved["targets"], [])

    def test_existing_target_status_change_does_not_invalidate_frozen_plan(self) -> None:
        before = {
            "project": {"id": "p1", "name": "01_ONEOS"},
            "source": {"id": "s11", "name": "OneOS Web端V1.4.11"},
            "idempotencyKey": "accept-key",
            "targets": [
                {
                    "name": "OneOS Web端V1.4.12", "startDate": "2026-09-29",
                    "endDate": "2026-10-13", "result": "idempotent",
                    "existing": {
                        "id": "s12", "name": "OneOS Web端V1.4.12", "endpoint": "Web",
                        "startDate": "2026-09-29", "endDate": "2026-10-13",
                        "status": "TODO", "ownerIds": ["owner-1"],
                    },
                },
                {
                    "name": "OneOS Web端V1.4.13", "startDate": "2026-10-14",
                    "endDate": "2026-10-28", "result": "create", "existing": None,
                },
            ],
        }
        live = json.loads(json.dumps(before))
        live["targets"][0]["existing"]["status"] = "DOING"
        pm._validate_followup_apply_scope(before, live)


class AcceptanceFollowupTests(unittest.TestCase):
    def test_bug_only_release_scope_is_resolved_but_empty_scope_is_rejected(self) -> None:
        bug = {
            "id": "bug", "serialNumber": "ONEOS-3", "categoryId": "Bug",
            "status": {"id": "done", "displayName": "已完成"},
        }
        with mock.patch.object(acceptance, "associated_full", return_value=[bug]):
            self.assertEqual(
                acceptance.resolve_acceptance_scope("aliyun", "release"),
                ([], [], [bug]),
            )
        with mock.patch.object(acceptance, "associated_full", return_value=[]):
            with self.assertRaisesRegex(RuntimeError, "未正式关联"):
                acceptance.resolve_acceptance_scope("aliyun", "release")

    def test_only_full_batch_pass_triggers_followup(self) -> None:
        self.assertTrue(acceptance.should_auto_followup("pass", [], "s11"))
        self.assertFalse(acceptance.should_auto_followup("fail", [], "s11"))
        self.assertFalse(acceptance.should_auto_followup("pass", [{"componentId": "c1"}], "s11"))
        self.assertFalse(acceptance.should_auto_followup("pass", [], None))

    def test_source_is_inferred_from_batch_and_explicit_mismatch_is_rejected(self) -> None:
        deliveries = [{"serialNumber": "ONEOS-1", "sprint": {"id": "s11"}}]
        self.assertEqual(
            acceptance.acceptance_source_sprint_id(deliveries, [], None), "s11"
        )
        with self.assertRaisesRegex(RuntimeError, "实际迭代不一致"):
            acceptance.acceptance_source_sprint_id(deliveries, [], "s12")
        with self.assertRaisesRegex(RuntimeError, "跨多个来源迭代"):
            acceptance.acceptance_source_sprint_id(
                deliveries + [{"serialNumber": "ONEOS-2", "sprint": {"id": "s12"}}],
                [], None,
            )

    def test_workflow_status_uses_official_id_shape(self) -> None:
        item = {
            "id": "w1", "serialNumber": "ONEOS-1", "space": {"id": "p1"},
            "workitemType": {"id": "type-1"}, "status": {"id": "602481", "displayName": "发布完成"},
        }
        with mock.patch.object(
            acceptance.core,
            "run_devops",
            return_value={"statuses": [{"displayName": "已完成", "id": "100014", "name": "已完成"}]},
        ):
            self.assertEqual(
                acceptance.list_next_statuses("aliyun", item), [("已完成", "100014")]
            )

    def test_existing_plan_must_match_frozen_source_and_key(self) -> None:
        args = argparse.Namespace(
            source_sprint_id="s11", dry_run=False,
            followup_preflight=None, followup_receipt=None,
        )
        plan = {
            "schema": pm.SCHEMA,
            "command": "preflight-followup-sprints",
            "createdAt": "now",
            "liveScope": {
                "project": {"id": "p1"}, "source": {"id": "s11"},
                "idempotencyKey": "accept-key", "targets": [],
            },
        }
        plan["preflightHash"] = pm.canonical_hash(plan, {"preflightHash"})
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "plan.json"
            path.write_text(json.dumps(plan), encoding="utf-8")
            args.followup_preflight = path
            _, returned, _ = acceptance.followup_plan("aliyun", args, "accept-key", "p1")
            self.assertEqual(returned, path)
            with self.assertRaisesRegex(RuntimeError, "批次不一致"):
                acceptance.followup_plan("aliyun", args, "different-key", "p1")

    def test_followup_failure_is_separate_resumable_result(self) -> None:
        with mock.patch.object(pm, "apply_followup_preflight", side_effect=core.AdapterError("network failed")):
            result = acceptance.apply_followup_result(
                "aliyun", Path("frozen.json"), Path("receipt.json")
            )
        self.assertEqual(result["ok"], False)
        self.assertEqual(result["resumable"], True)
        self.assertIn("network failed", result["error"])

    def test_closed_batch_rerun_requires_acceptance_key_on_standalone_bug(self) -> None:
        done = {"status": {"id": "done", "displayName": "已完成"}}
        release = {**done, "id": "release", "serialNumber": "TASK-900", "categoryId": "Task",
                   "description": "accept-key"}
        requirement = {**done, "id": "req", "serialNumber": "ONEOS-1", "categoryId": "Req",
                       "description": "accept-key"}
        delivery = {**done, "id": "delivery", "serialNumber": "ONEOS-2", "categoryId": "Task",
                    "subject": "【交付】功能", "description": "accept-key"}
        bug = {**done, "id": "bug", "serialNumber": "ONEOS-3", "categoryId": "Bug",
               "description": "oneos.bug-retest/v1"}
        with self.assertRaisesRegex(RuntimeError, "独立Bug缺少"):
            acceptance.validate_resume_evidence(
                release, [requirement], [delivery], [bug], "accept-key"
            )

    def test_full_pass_writes_completed_bug_evidence_then_closes_before_followup(self) -> None:
        def item(identifier: str, serial_number: str, category: str, state: str,
                 *, subject: str = "", sprint_id: str | None = None,
                 description: str = "") -> dict:
            value = {
                "id": identifier, "serialNumber": serial_number, "categoryId": category,
                "subject": subject, "description": description,
                "status": {"id": state, "displayName": state},
                "space": {"id": "p1"}, "workitemType": {"id": "type-1", "name": "任务"},
            }
            if sprint_id:
                value["sprint"] = {"id": sprint_id, "name": "OneOS Web端V1.4.11"}
            return value

        release = item("release", "TASK-900", "Task", "发布完成")
        requirement = item("req", "ONEOS-1", "Req", "发布完成")
        delivery = item(
            "delivery", "ONEOS-2", "Task", "处理中",
            subject="【交付】功能", sprint_id="s11",
        )
        bug = item(
            "bug", "ONEOS-3", "Bug", "已完成", sprint_id="s11",
            description="oneos.bug-retest/v1",
        )
        store = {row["id"]: row for row in (release, requirement, delivery, bug)}
        events: list[str] = []

        def write_document(_session: str, identifier: str, content: str) -> None:
            store[identifier]["description"] = content
            events.append(f"evidence:{identifier}")

        def close_item(_session: str, value: dict) -> None:
            store[value["id"]]["status"] = {"id": "done", "displayName": "已完成"}
            events.append(f"close:{value['id']}")

        followup_value = {
            "liveScope": {
                "source": {"id": "s11", "name": "OneOS Web端V1.4.11"},
                "targets": [
                    {"name": "OneOS Web端V1.4.12"},
                    {"name": "OneOS Web端V1.4.13"},
                ],
            },
            "preflightHash": "hash-1",
        }

        def apply_followup(*_args) -> dict:
            events.append("followup")
            return {"ok": True, "resumable": False}

        argv = [
            "accept_release.py", "pass", "--release-id", "release",
            "--release-sn", "TASK-900", "--acceptor", "PM", "--evidence", "E-1",
        ]
        output = io.StringIO()
        with (
            mock.patch.object(sys, "argv", argv),
            mock.patch.object(acceptance, "load_session", return_value="aliyun"),
            mock.patch.object(acceptance, "get_item", side_effect=lambda _s, identifier: store[identifier]),
            mock.patch.object(acceptance, "resolve_acceptance_scope",
                              return_value=([requirement], [delivery], [bug])),
            mock.patch.object(acceptance.pm, "item_project_id", return_value="p1"),
            mock.patch.object(acceptance, "is_web_version_sprint", return_value=True),
            mock.patch.object(acceptance, "followup_plan",
                              return_value=(followup_value, Path("plan.json"), Path("receipt.json"))),
            mock.patch.object(acceptance, "associated_full", return_value=[]),
            mock.patch.object(acceptance, "set_document", side_effect=write_document),
            mock.patch.object(acceptance, "transit_to_acceptance_done", side_effect=close_item),
            mock.patch.object(acceptance, "apply_followup_result", side_effect=apply_followup),
            redirect_stdout(output),
        ):
            acceptance.main()

        result = json.loads(output.getvalue())
        self.assertTrue(result["acceptanceOk"])
        self.assertIn(acceptance.ACCEPT_START, bug["description"])
        self.assertIn(result["idempotencyKey"], bug["description"])
        self.assertEqual(bug["status"]["displayName"], "已完成")
        self.assertEqual(
            [event for event in events if event.startswith("close:")],
            ["close:delivery", "close:req", "close:release"],
        )
        self.assertGreater(events.index("followup"), events.index("close:release"))

    def test_missing_source_is_reported_unresolved_not_non_web(self) -> None:
        release = {
            "id": "release", "serialNumber": "TASK-900", "categoryId": "Task",
            "status": {"id": "published", "displayName": "发布完成"},
        }
        requirement = {
            "id": "req", "serialNumber": "ONEOS-1", "categoryId": "Req",
            "status": {"id": "published", "displayName": "发布完成"},
        }
        delivery = {
            "id": "delivery", "serialNumber": "ONEOS-2", "categoryId": "Task",
            "subject": "【交付】功能",
            "status": {"id": "doing", "displayName": "处理中"},
        }
        argv = [
            "accept_release.py", "pass", "--release-id", "release",
            "--release-sn", "TASK-900", "--acceptor", "PM", "--evidence", "E-1",
            "--dry-run",
        ]
        output = io.StringIO()
        with (
            mock.patch.object(sys, "argv", argv),
            mock.patch.object(acceptance, "load_session", return_value="aliyun"),
            mock.patch.object(acceptance, "get_item", return_value=release),
            mock.patch.object(acceptance, "resolve_acceptance_scope",
                              return_value=([requirement], [delivery], [])),
            mock.patch.object(acceptance.pm, "item_project_id", return_value="p1"),
            redirect_stdout(output),
        ):
            acceptance.main()
        followup = json.loads(output.getvalue())["followupSprints"]
        self.assertEqual(followup["reason"], "missing_source")
        self.assertTrue(followup["unresolved"])
        self.assertNotIn("skippedNonWeb", followup)


if __name__ == "__main__":
    unittest.main()
