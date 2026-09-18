"""Build execution-gate scope metadata from explicit Yunxiao values only."""

from __future__ import annotations

from typing import Any


def _present(value: Any) -> bool:
    return value is not None and str(value).strip() not in {"", "None", "null"}


def build_task_scope(*, task_type: str, task_id: Any, created_at: Any,
                     gate_effective_at: Any, parent_task_id: Any = None,
                     parent_task_type: Any = None,
                     parent_created_at: Any = None) -> dict[str, Any]:
    """Return ready scope or an explicit metadata gap; never infer timestamps."""
    task_id_value = str(task_id) if _present(task_id) else None
    scope = {"task_type": task_type, "created_at": created_at,
             "gate_effective_at": gate_effective_at,
             "parent_task_id": str(parent_task_id) if _present(parent_task_id) else None,
             "parent_task_type": parent_task_type, "parent_created_at": parent_created_at}
    required = ("created_at", "gate_effective_at")
    if task_type in {"development", "test"}:
        required += ("parent_task_id", "parent_task_type", "parent_created_at")
    missing = [key for key in required if not _present(scope.get(key))]
    if missing:
        return {"status": "metadata_missing",
                "missing": (["task_id"] if not task_id_value else []) + missing,
                "task_id": task_id_value, "task_scope": scope}
    return {"status": "ready", "task_id": task_id_value, "task_scope": scope}
