# Runtime source manifest

This directory is the traceable repository copy of the Codex team-task-router runtime gate used by the OneOS delivery workflow. The Python runtime source is kept under `skills/team-task-router/`; focused tests are under `tests/`.

The runtime gate reads explicit task metadata and reports missing scope metadata instead of inferring timestamps or parent relationships. Yunxiao development receipts consume the shared `task_scope_metadata` helper under `skills/yunxiao-development-delivery/scripts/`.
