from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path


SCRIPT = (
    Path(__file__).parents[1]
    / "skills"
    / "yunxiao-development-delivery"
    / "scripts"
    / "codex_task_time.py"
)
SPEC = importlib.util.spec_from_file_location("codex_task_time", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def invoke(arguments):
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        code = MODULE.main(arguments)
    return code, json.loads(output.getvalue())


class CodexTaskTimeTests(unittest.TestCase):
    def test_upsert_is_idempotent_and_resolve_excludes_unassigned(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = str(Path(directory) / "ledger.sqlite3")
            common = [
                "upsert-segment",
                "--ledger",
                ledger,
                "--development-task-id",
                "ONEOS-696",
                "--thread-id",
                "thread-1",
                "--segment-id",
                "segment-1",
                "--started-at-ms",
                "1000",
                "--ended-at-ms",
                "2000",
                "--disposition",
                "linked",
            ]
            self.assertEqual(0, invoke([*common, "--active-seconds", "120"])[0])
            self.assertEqual(0, invoke([*common, "--active-seconds", "5700"])[0])
            self.assertEqual(
                0,
                invoke(
                    [
                        "upsert-segment",
                        "--ledger",
                        ledger,
                        "--development-task-id",
                        "ONEOS-696",
                        "--thread-id",
                        "thread-1",
                        "--segment-id",
                        "segment-2",
                        "--started-at-ms",
                        "2001",
                        "--ended-at-ms",
                        "3000",
                        "--active-seconds",
                        "600",
                        "--disposition",
                        "unassigned",
                    ]
                )[0],
            )
            code, payload = invoke(
                [
                    "resolve",
                    "--ledger",
                    ledger,
                    "--development-task-id",
                    "ONEOS-696",
                ]
            )
            self.assertEqual(0, code)
            self.assertEqual(5700, payload["totalSeconds"])
            self.assertEqual(95, payload["totalMinutes"])
            self.assertEqual("1.58", payload["calculatedHours"])
            self.assertEqual(1, payload["counts"]["linked"])
            self.assertEqual(1, payload["counts"]["unassigned"])

    def test_discover_is_time_bounded_and_returns_no_conversation_body(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state = sqlite3.connect(root / "state_5.sqlite")
            state.execute(
                "CREATE TABLE threads (id TEXT, title TEXT, first_user_message TEXT, "
                "preview TEXT, created_at_ms INTEGER, updated_at_ms INTEGER, archived INTEGER, "
                "git_branch TEXT, git_sha TEXT, git_origin_url TEXT)"
            )
            state.executemany(
                "INSERT INTO threads VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    ("hit", "ONEOS-696", "", "", 1000, 2000, 0, "", "", ""),
                    ("outside", "ONEOS-696", "", "", 1, 2, 1, "", "", ""),
                ],
            )
            state.commit()
            state.close()

            history = sqlite3.connect(root / "thread_history_1.sqlite")
            history.execute(
                "CREATE TABLE thread_items (thread_id TEXT, turn_id TEXT, created_at_ms INTEGER, item_json TEXT)"
            )
            history.execute(
                "INSERT INTO thread_items VALUES (?, ?, ?, ?)",
                ("hit", "turn-1", 1500, '{"text":"处理 ONEOS-696"}'),
            )
            history.commit()
            history.close()

            code, payload = invoke(
                [
                    "discover",
                    "--codex-root",
                    str(root),
                    "--started-at-ms",
                    "900",
                    "--completed-at-ms",
                    "2100",
                    "--anchor",
                    "ONEOS-696",
                ]
            )
            self.assertEqual(0, code)
            self.assertEqual(["hit"], payload["targetedThreadIds"])
            self.assertFalse(payload["rawConversationScan"])
            self.assertNotIn("处理 ONEOS-696", json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    unittest.main()
