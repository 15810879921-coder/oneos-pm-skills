from __future__ import annotations

import argparse
from contextlib import closing
import json
import os
import re
import sqlite3
import sys
import time
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = "oneos.codex-task-segment/v1"
TASK_ID_PATTERN = re.compile(r"^[A-Z][A-Z0-9_-]*-\d+$")


class TimeIndexError(RuntimeError):
    pass


def default_codex_root() -> Path:
    configured = os.environ.get("CODEX_HOME")
    return Path(configured) if configured else Path.home() / ".codex"


def default_ledger_path() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        base = Path(local_app_data) / "Codex"
    else:
        base = default_codex_root() / "state"
    return base / "yunxiao-development-delivery" / "codex-task-segments-v1.sqlite3"


def connect_ledger(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS task_segments (
            thread_id TEXT NOT NULL,
            segment_id TEXT NOT NULL,
            development_task_id TEXT NOT NULL,
            started_at_ms INTEGER,
            ended_at_ms INTEGER,
            active_seconds INTEGER,
            disposition TEXT NOT NULL,
            requirement_id TEXT,
            delivery_task_id TEXT,
            bugs_json TEXT NOT NULL,
            repositories_json TEXT NOT NULL,
            branches_json TEXT NOT NULL,
            mrs_json TEXT NOT NULL,
            commits_json TEXT NOT NULL,
            evidence_json TEXT NOT NULL,
            updated_at_ms INTEGER NOT NULL,
            schema_version TEXT NOT NULL,
            PRIMARY KEY (thread_id, segment_id)
        )
        """
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_task_segments_dev "
        "ON task_segments(development_task_id, disposition)"
    )
    connection.commit()
    return connection


def split_values(values: Iterable[str] | None) -> list[str]:
    result: list[str] = []
    for value in values or []:
        for part in value.split(","):
            normalized = part.strip()
            if normalized and normalized not in result:
                result.append(normalized)
    return result


def validate_task_id(value: str) -> str:
    normalized = value.strip().upper()
    if not TASK_ID_PATTERN.fullmatch(normalized):
        raise TimeIndexError(f"开发任务编号格式无效：{value}")
    return normalized


def emit(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


def command_upsert(args: argparse.Namespace) -> int:
    development_task_id = validate_task_id(args.development_task_id)
    if args.active_seconds is not None and args.active_seconds < 0:
        raise TimeIndexError("active-seconds 不能小于0")
    if (
        args.started_at_ms is not None
        and args.ended_at_ms is not None
        and args.ended_at_ms < args.started_at_ms
    ):
        raise TimeIndexError("ended-at-ms 不能早于 started-at-ms")

    payload = {
        "thread_id": args.thread_id.strip(),
        "segment_id": args.segment_id.strip(),
        "development_task_id": development_task_id,
        "started_at_ms": args.started_at_ms,
        "ended_at_ms": args.ended_at_ms,
        "active_seconds": args.active_seconds,
        "disposition": args.disposition,
        "requirement_id": args.requirement_id,
        "delivery_task_id": args.delivery_task_id,
        "bugs_json": json.dumps(split_values(args.bug), ensure_ascii=False),
        "repositories_json": json.dumps(split_values(args.repository), ensure_ascii=False),
        "branches_json": json.dumps(split_values(args.branch), ensure_ascii=False),
        "mrs_json": json.dumps(split_values(args.mr), ensure_ascii=False),
        "commits_json": json.dumps(split_values(args.commit), ensure_ascii=False),
        "evidence_json": json.dumps(split_values(args.evidence), ensure_ascii=False),
        "updated_at_ms": int(time.time() * 1000),
        "schema_version": SCHEMA_VERSION,
    }
    if not payload["thread_id"] or not payload["segment_id"]:
        raise TimeIndexError("thread-id 和 segment-id 不能为空")

    columns = list(payload)
    assignments = ", ".join(
        f"{column}=excluded.{column}"
        for column in columns
        if column not in {"thread_id", "segment_id"}
    )
    placeholders = ", ".join("?" for _ in columns)
    with closing(connect_ledger(Path(args.ledger))) as connection:
        connection.execute(
            f"INSERT INTO task_segments ({', '.join(columns)}) "
            f"VALUES ({placeholders}) "
            f"ON CONFLICT(thread_id, segment_id) DO UPDATE SET {assignments}",
            [payload[column] for column in columns],
        )
        connection.commit()

    emit(
        {
            "schemaVersion": SCHEMA_VERSION,
            "operation": "upsert",
            "developmentTaskId": development_task_id,
            "threadId": payload["thread_id"],
            "segmentId": payload["segment_id"],
            "disposition": payload["disposition"],
            "ledger": str(Path(args.ledger)),
        }
    )
    return 0


def work_time(total_seconds: int) -> tuple[int, str]:
    if total_seconds <= 0:
        return 0, "0.00"
    total_minutes = max(1, (total_seconds + 30) // 60)
    hours = (Decimal(total_minutes) / Decimal(60)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    return total_minutes, format(hours, ".2f")


def decode_json_list(raw: str) -> list[str]:
    value = json.loads(raw)
    return value if isinstance(value, list) else []


def command_resolve(args: argparse.Namespace) -> int:
    development_task_id = validate_task_id(args.development_task_id)
    ledger = Path(args.ledger)
    if not ledger.exists():
        emit(
            {
                "schemaVersion": SCHEMA_VERSION,
                "operation": "resolve",
                "developmentTaskId": development_task_id,
                "status": "no-index",
                "segments": [],
                "totalSeconds": 0,
                "totalMinutes": 0,
                "calculatedHours": "0.00",
                "ledger": str(ledger),
            }
        )
        return 0

    with closing(connect_ledger(ledger)) as connection:
        rows = connection.execute(
            "SELECT * FROM task_segments WHERE development_task_id=? "
            "ORDER BY started_at_ms, thread_id, segment_id",
            (development_task_id,),
        ).fetchall()

    segments: list[dict[str, Any]] = []
    total_seconds = 0
    counts = {"linked": 0, "excluded": 0, "unassigned": 0}
    for row in rows:
        disposition = row["disposition"]
        counts[disposition] = counts.get(disposition, 0) + 1
        active_seconds = row["active_seconds"]
        auditable = (
            disposition == "linked"
            and active_seconds is not None
            and active_seconds >= 0
            and row["started_at_ms"] is not None
            and row["ended_at_ms"] is not None
        )
        if auditable:
            total_seconds += active_seconds
        segments.append(
            {
                "threadId": row["thread_id"],
                "segmentId": row["segment_id"],
                "disposition": disposition,
                "startedAtMs": row["started_at_ms"],
                "endedAtMs": row["ended_at_ms"],
                "activeSeconds": active_seconds,
                "auditable": auditable,
                "bugs": decode_json_list(row["bugs_json"]),
                "repositories": decode_json_list(row["repositories_json"]),
                "branches": decode_json_list(row["branches_json"]),
                "mrs": decode_json_list(row["mrs_json"]),
                "commits": decode_json_list(row["commits_json"]),
                "evidence": decode_json_list(row["evidence_json"]),
            }
        )

    total_minutes, calculated_hours = work_time(total_seconds)
    emit(
        {
            "schemaVersion": SCHEMA_VERSION,
            "operation": "resolve",
            "developmentTaskId": development_task_id,
            "status": "resolved" if segments else "no-index",
            "counts": counts,
            "segments": segments,
            "totalSeconds": total_seconds,
            "totalMinutes": total_minutes,
            "calculatedHours": calculated_hours,
            "ledger": str(ledger),
        }
    )
    return 0


def table_columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}


def table_exists(connection: sqlite3.Connection, table: str) -> bool:
    row = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    return row is not None


def command_probe(args: argparse.Namespace) -> int:
    codex_root = Path(args.codex_root)
    state_db = codex_root / "state_5.sqlite"
    history_db = codex_root / "thread_history_1.sqlite"
    required_state = {
        "id",
        "title",
        "first_user_message",
        "preview",
        "created_at_ms",
        "updated_at_ms",
        "archived",
        "git_branch",
        "git_sha",
        "git_origin_url",
    }
    required_turns = {
        "thread_id",
        "turn_id",
        "status",
        "started_at",
        "completed_at",
        "duration_ms",
    }
    required_items = {"thread_id", "turn_id", "created_at_ms", "item_json"}
    result: dict[str, Any] = {
        "operation": "probe",
        "codexRoot": str(codex_root),
        "stateDb": {"path": str(state_db), "available": False},
        "historyDb": {"path": str(history_db), "available": False},
    }
    if state_db.exists():
        with closing(sqlite3.connect(state_db)) as connection:
            columns = table_columns(connection, "threads") if table_exists(connection, "threads") else set()
            result["stateDb"] = {
                "path": str(state_db),
                "available": required_state.issubset(columns),
                "missingColumns": sorted(required_state - columns),
            }
    if history_db.exists():
        with closing(sqlite3.connect(history_db)) as connection:
            turn_columns = table_columns(connection, "thread_turns") if table_exists(connection, "thread_turns") else set()
            item_columns = table_columns(connection, "thread_items") if table_exists(connection, "thread_items") else set()
            result["historyDb"] = {
                "path": str(history_db),
                "available": required_turns.issubset(turn_columns) and required_items.issubset(item_columns),
                "missingTurnColumns": sorted(required_turns - turn_columns),
                "missingItemColumns": sorted(required_items - item_columns),
            }
    result["available"] = result["stateDb"]["available"] and result["historyDb"]["available"]
    emit(result)
    return 0 if result["available"] else 2


def command_discover(args: argparse.Namespace) -> int:
    if args.completed_at_ms < args.started_at_ms:
        raise TimeIndexError("completed-at-ms 不能早于 started-at-ms")
    anchors = split_values(args.anchor)
    if not anchors:
        raise TimeIndexError("至少需要一个精确 anchor")

    codex_root = Path(args.codex_root)
    state_db = codex_root / "state_5.sqlite"
    history_db = codex_root / "thread_history_1.sqlite"
    if not state_db.exists() or not history_db.exists():
        raise TimeIndexError("Codex轻量元数据数据库不可用；禁止回退全量原始会话扫描")

    patterns = [f"%{anchor}%" for anchor in anchors]
    state_hits: dict[str, dict[str, Any]] = {}
    state_fields = ["title", "first_user_message", "preview", "git_branch", "git_sha", "git_origin_url"]
    clauses = " OR ".join(
        f"COALESCE({field}, '') LIKE ?" for field in state_fields for _ in patterns
    )
    parameters = [pattern for _field in state_fields for pattern in patterns]
    with closing(sqlite3.connect(state_db)) as connection:
        connection.row_factory = sqlite3.Row
        required = {"id", "created_at_ms", "updated_at_ms", "archived", *state_fields}
        columns = table_columns(connection, "threads") if table_exists(connection, "threads") else set()
        if not required.issubset(columns):
            raise TimeIndexError("Codex任务元数据结构不兼容；禁止猜测字段")
        sql = (
            "SELECT id, title, created_at_ms, updated_at_ms, archived, git_branch, git_sha, git_origin_url "
            "FROM threads WHERE created_at_ms <= ? AND updated_at_ms >= ? AND ("
            + clauses
            + ")"
        )
        for row in connection.execute(
            sql, [args.completed_at_ms, args.started_at_ms, *parameters]
        ):
            state_hits[row["id"]] = {
                "threadId": row["id"],
                "title": row["title"],
                "createdAtMs": row["created_at_ms"],
                "updatedAtMs": row["updated_at_ms"],
                "archived": bool(row["archived"]),
                "gitBranch": row["git_branch"],
                "gitSha": row["git_sha"],
                "gitOriginUrl": row["git_origin_url"],
            }

    item_hits: set[tuple[str, str]] = set()
    with closing(sqlite3.connect(history_db)) as connection:
        required = {"thread_id", "turn_id", "created_at_ms", "item_json"}
        columns = table_columns(connection, "thread_items") if table_exists(connection, "thread_items") else set()
        if not required.issubset(columns):
            raise TimeIndexError("Codex回合元数据结构不兼容；禁止猜测字段")
        item_clause = " OR ".join("item_json LIKE ?" for _ in patterns)
        sql = (
            "SELECT DISTINCT thread_id, turn_id FROM thread_items "
            "WHERE created_at_ms BETWEEN ? AND ? AND (" + item_clause + ")"
        )
        for thread_id, turn_id in connection.execute(
            sql, [args.started_at_ms, args.completed_at_ms, *patterns]
        ):
            item_hits.add((thread_id, turn_id))

    thread_ids = set(state_hits) | {thread_id for thread_id, _ in item_hits}
    emit(
        {
            "operation": "discover",
            "scope": {
                "startedAtMs": args.started_at_ms,
                "completedAtMs": args.completed_at_ms,
                "anchors": anchors,
            },
            "metadataHits": [state_hits[key] for key in sorted(state_hits)],
            "turnHits": [
                {"threadId": thread_id, "turnId": turn_id}
                for thread_id, turn_id in sorted(item_hits)
            ],
            "targetedThreadIds": sorted(thread_ids),
            "deepReadCount": len(thread_ids),
            "rawConversationScan": False,
        }
    )
    return 0


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="Codex开发任务分段索引、定向发现与工时汇总"
    )
    subparsers = result.add_subparsers(dest="command", required=True)

    upsert = subparsers.add_parser("upsert-segment")
    upsert.add_argument("--ledger", default=str(default_ledger_path()))
    upsert.add_argument("--development-task-id", required=True)
    upsert.add_argument("--thread-id", required=True)
    upsert.add_argument("--segment-id", required=True)
    upsert.add_argument("--started-at-ms", type=int)
    upsert.add_argument("--ended-at-ms", type=int)
    upsert.add_argument("--active-seconds", type=int)
    upsert.add_argument(
        "--disposition", choices=("linked", "excluded", "unassigned"), required=True
    )
    upsert.add_argument("--requirement-id")
    upsert.add_argument("--delivery-task-id")
    upsert.add_argument("--bug", action="append")
    upsert.add_argument("--repository", action="append")
    upsert.add_argument("--branch", action="append")
    upsert.add_argument("--mr", action="append")
    upsert.add_argument("--commit", action="append")
    upsert.add_argument("--evidence", action="append")
    upsert.set_defaults(handler=command_upsert)

    resolve = subparsers.add_parser("resolve")
    resolve.add_argument("--ledger", default=str(default_ledger_path()))
    resolve.add_argument("--development-task-id", required=True)
    resolve.set_defaults(handler=command_resolve)

    probe = subparsers.add_parser("probe-codex")
    probe.add_argument("--codex-root", default=str(default_codex_root()))
    probe.set_defaults(handler=command_probe)

    discover = subparsers.add_parser("discover")
    discover.add_argument("--codex-root", default=str(default_codex_root()))
    discover.add_argument("--started-at-ms", required=True, type=int)
    discover.add_argument("--completed-at-ms", required=True, type=int)
    discover.add_argument("--anchor", action="append", required=True)
    discover.set_defaults(handler=command_discover)
    return result


def main(argv: list[str] | None = None) -> int:
    try:
        args = parser().parse_args(argv)
        return args.handler(args)
    except TimeIndexError as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
