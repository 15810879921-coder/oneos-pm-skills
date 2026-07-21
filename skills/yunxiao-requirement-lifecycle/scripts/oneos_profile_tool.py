#!/usr/bin/env python3
"""Validate and render a OneOS delivery-model Yunxiao project profile."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


TARGET_LIFECYCLE = [
    "待处理", "已确认", "分析中", "分析完成", "设计中", "设计完成",
    "待开发", "开发中", "开发完成", "待测试", "测试中", "测试完成",
    "发布中", "发布完成", "发布失败", "已关闭",
]
REQUIRED_TASK_LABELS = {"交付", "开发", "测试", "发版"}
REQUIRED_CONTROL_IDS = {
    *(f"Y{index:02d}" for index in range(1, 17)),
    "Y20", "Y21", "Y22",
    *(f"Y{index:02d}" for index in range(30, 36)),
    "Y40",
    "A01", "A02", "A02B", *(f"A{index:02d}" for index in range(3, 11)),
    *(f"TC{index:02d}" for index in range(1, 4)),
    *(f"DF{index:02d}" for index in range(1, 4)),
    *(f"CI{index:02d}" for index in range(1, 4)),
    "L01", "L02",
}
VALID_MODES = {
    "manual", "native_rule", "integration_bridge", "disabled_legacy", "not_supported"
}
VALID_PHASES = {"P0", "P1", "P2", "P3"}
VALID_TASK_WORKFLOW_MODES = {"A", "B"}
VALID_TASK_IDENTITY_MODES = {"work_item_type", "task_label", "title_prefix_process_control"}
VALID_LEGACY_DISPOSITIONS = {"keep_until_ready", "disable", "replace", "already_disabled"}
SENSITIVE_FRAGMENTS = (
    "password", "passwd", "secret", "token", "cookie", "credential",
    "private_key", "otp", "密码", "密钥",
)


def is_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def require_text(container: dict[str, Any], key: str, label: str, errors: list[str]) -> None:
    if not is_text(container.get(key)):
        errors.append(f"{label}.{key} 不能为空")


def walk_sensitive_keys(value: Any, prefix: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, nested in value.items():
            current = f"{prefix}.{key}" if prefix else str(key)
            if any(fragment in str(key).lower() for fragment in SENSITIVE_FRAGMENTS):
                found.append(current)
            found.extend(walk_sensitive_keys(nested, current))
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            found.extend(walk_sensitive_keys(nested, f"{prefix}[{index}]"))
    return found


def validate_controls(controls: Any, label: str, errors: list[str]) -> None:
    if not isinstance(controls, list):
        errors.append(f"{label} 必须是数组")
        return
    seen: set[str] = set()
    for index, control in enumerate(controls):
        item_label = f"{label}[{index}]"
        if not isinstance(control, dict):
            errors.append(f"{item_label} 必须是对象")
            continue
        control_id = control.get("id")
        if not is_text(control_id):
            errors.append(f"{item_label}.id 不能为空")
            continue
        if control_id in seen:
            errors.append(f"{label} 控制项重复：{control_id}")
        seen.add(control_id)
        if control_id not in REQUIRED_CONTROL_IDS:
            errors.append(f"{label} 未知控制项：{control_id}")
        mode = control.get("mode")
        if mode not in VALID_MODES:
            errors.append(f"{item_label}.mode 不合法")
        if not isinstance(control.get("enabled"), bool):
            errors.append(f"{item_label}.enabled 必须是布尔值")
        if mode in {"disabled_legacy", "not_supported"} and control.get("enabled") is not False:
            errors.append(f"{item_label} 的 {mode} 模式要求 enabled=false")
        if control_id in {"L01", "L02"}:
            if mode != "disabled_legacy" or control.get("enabled") is not False:
                errors.append(f"{item_label} 必须停用，防止发布完成绕过验收")
        for key in ("owner", "fallback", "evidence"):
            require_text(control, key, item_label, errors)
    missing = sorted(REQUIRED_CONTROL_IDS - seen)
    if missing:
        errors.append(f"{label} 缺少控制项：" + "、".join(missing))


def validate_project(project: Any, index: int, errors: list[str]) -> None:
    label = f"projects[{index}]"
    if not isinstance(project, dict):
        errors.append(f"{label} 必须是对象")
        return
    require_text(project, "name", label, errors)
    if project.get("migration_phase") not in VALID_PHASES:
        errors.append(f"{label}.migration_phase 必须是 P0/P1/P2/P3")
    statuses = project.get("requirement_statuses_observed")
    if not isinstance(statuses, list) or not statuses or not all(is_text(v) for v in statuses):
        errors.append(f"{label}.requirement_statuses_observed 必须是非空文本数组")
    if project.get("task_workflow_mode") not in VALID_TASK_WORKFLOW_MODES:
        errors.append(f"{label}.task_workflow_mode 必须是 A 或 B")
    if project.get("task_identity_mode") not in VALID_TASK_IDENTITY_MODES:
        errors.append(f"{label}.task_identity_mode 不合法")
    if not isinstance(project.get("native_rule_can_filter_related_task_identity"), bool):
        errors.append(f"{label}.native_rule_can_filter_related_task_identity 必须是布尔值")
    for key in (
        "main_task_prefix", "development_task_prefix", "test_task_prefix", "release_task_prefix"
    ):
        require_text(project, key, label, errors)

    repositories = project.get("repositories")
    if not isinstance(repositories, list) or not repositories:
        errors.append(f"{label}.repositories 至少包含一个仓库")
    else:
        for repo_index, repo in enumerate(repositories):
            repo_label = f"{label}.repositories[{repo_index}]"
            if not isinstance(repo, dict):
                errors.append(f"{repo_label} 必须是对象")
                continue
            for key in ("name", "role", "integration_branch", "evidence"):
                require_text(repo, key, repo_label, errors)
            if repo.get("integration_branch") not in {"dev", "develop"}:
                errors.append(f"{repo_label}.integration_branch 只能是实际存在的 dev/develop")
            for key in ("codeup_integrated", "required_for_mr_gate"):
                if not isinstance(repo.get(key), bool):
                    errors.append(f"{repo_label}.{key} 必须是布尔值")

    test_plan = project.get("test_plan")
    if not isinstance(test_plan, dict):
        errors.append(f"{label}.test_plan 必须是对象")
    else:
        require_text(test_plan, "name", f"{label}.test_plan", errors)
        require_text(test_plan, "evidence", f"{label}.test_plan", errors)
        for key, required in (
            ("iteration_formally_related", True),
            ("cases_partitioned_by_requirement", True),
            ("fixed_defect_is_terminal", False),
            ("tester_retest_required", True),
        ):
            if test_plan.get(key) is not required:
                errors.append(f"{label}.test_plan.{key} 必须为 {str(required).lower()}")

    release = project.get("release")
    if not isinstance(release, dict):
        errors.append(f"{label}.release 必须是对象")
    else:
        require_text(release, "evidence", f"{label}.release", errors)
        for key in (
            "release_task_formally_related_to_iteration",
            "production_evidence_separate_from_test",
            "acceptance_required_after_release",
            "production_pipeline_unchanged",
        ):
            if release.get(key) is not True:
                errors.append(f"{label}.release.{key} 必须为 true")

    legacy_rules = project.get("legacy_rules")
    if not isinstance(legacy_rules, list):
        errors.append(f"{label}.legacy_rules 必须是数组")
    else:
        for legacy_index, rule in enumerate(legacy_rules):
            item_label = f"{label}.legacy_rules[{legacy_index}]"
            if not isinstance(rule, dict):
                errors.append(f"{item_label} 必须是对象")
                continue
            for key in ("name", "reason", "evidence"):
                require_text(rule, key, item_label, errors)
            if rule.get("disposition") not in VALID_LEGACY_DISPOSITIONS:
                errors.append(f"{item_label}.disposition 不合法")
            if not isinstance(rule.get("enabled"), bool):
                errors.append(f"{item_label}.enabled 必须是布尔值")

    validate_controls(project.get("controls"), f"{label}.controls", errors)


def validate(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if data.get("schema_version") != 1:
        errors.append("schema_version 必须为 1")
    if data.get("flow_model") != "oneos_delivery":
        errors.append("flow_model 必须为 oneos_delivery")
    for key in ("organization", "work_item_type"):
        require_text(data, key, "profile", errors)
    if data.get("target_lifecycle") != TARGET_LIFECYCLE:
        errors.append("target_lifecycle 必须与OneOS终态16状态顺序一致")
    labels = data.get("task_labels")
    if not isinstance(labels, list) or not REQUIRED_TASK_LABELS.issubset(set(labels)):
        errors.append("task_labels 必须包含：交付、开发、测试、发版")
    policies = data.get("policies")
    if not isinstance(policies, dict):
        errors.append("policies 必须是对象")
    else:
        true_keys = (
            "require_formal_relations", "require_current_state_condition",
            "require_nonzero_development_tasks",
            "require_signed_timestamped_replay_protected_callbacks",
        )
        false_keys = ("allow_automatic_final_close_without_acceptance", "test_success_is_production_release")
        for key in true_keys:
            if policies.get(key) is not True:
                errors.append(f"policies.{key} 必须为 true")
        for key in false_keys:
            if policies.get(key) is not False:
                errors.append(f"policies.{key} 必须为 false")
        parts = policies.get("bridge_idempotency_key_components")
        if not isinstance(parts, list) or not parts or not all(is_text(v) for v in parts):
            errors.append("policies.bridge_idempotency_key_components 不能为空")
    projects = data.get("projects")
    if not isinstance(projects, list) or not projects:
        errors.append("projects 至少包含一个项目")
    else:
        for index, project in enumerate(projects):
            validate_project(project, index, errors)
    sensitive = walk_sensitive_keys(data)
    if sensitive:
        errors.append("配置中禁止出现敏感字段：" + "、".join(sensitive))
    if "请填写" in json.dumps(data, ensure_ascii=False):
        errors.append("仍存在“请填写”占位符")
    return errors


def render(data: dict[str, Any]) -> str:
    lines = [
        "# OneOS云效终态交付模型执行计划", "",
        f"- 组织：{data['organization']}",
        f"- 工作项类型：{data['work_item_type']}",
        f"- 项目数：{len(data['projects'])}",
        "- 完整性口径：每项目48项Y/A/测试/缺陷/集成/旧规则控制。",
        "- 安全边界：不修改生产流水线；发布完成后保留产品验收门禁。", "",
    ]
    for project in data["projects"]:
        missing_statuses = [s for s in TARGET_LIFECYCLE if s not in project["requirement_statuses_observed"]]
        lines.extend([
            f"## 项目：{project['name']}", "",
            f"- 迁移阶段：{project['migration_phase']}",
            f"- 任务工作流方案：{project['task_workflow_mode']}",
            f"- 任务身份方式：{project['task_identity_mode']}",
            f"- 原生规则可过滤关联任务身份：{'是' if project['native_rule_can_filter_related_task_identity'] else '否'}",
            f"- 缺少目标状态：{'、'.join(missing_statuses) if missing_statuses else '无'}", "",
            "### 旧规则处置", "",
            "| 规则 | 处置 | 启用 | 原因 | 证据 |", "|---|---|---|---|---|",
        ])
        for rule in project["legacy_rules"]:
            lines.append(
                f"| {rule['name']} | {rule['disposition']} | {'是' if rule['enabled'] else '否'} | "
                f"{rule['reason']} | {rule['evidence']} |"
            )
        lines.extend([
            "", "### 48项控制台账", "",
            "| ID | 方式 | 启用 | 负责人 | 回退方案 | 证据 |", "|---|---|---|---|---|---|",
        ])
        for control in sorted(project["controls"], key=lambda item: item["id"]):
            lines.append(
                f"| {control['id']} | {control['mode']} | {'是' if control['enabled'] else '否'} | "
                f"{control['owner']} | {control['fallback']} | {control['evidence']} |"
            )
        lines.extend([
            "", "### 迁移门禁", "",
            "- [ ] 目标状态与流转边已补齐。",
            "- [ ] 主任务可可靠识别或已明确交桥接。",
            "- [ ] 多仓库需求与开发任务均正式关联分支/MR。",
            "- [ ] Testhub按需求分包且缺陷复测闭环。",
            "- [ ] test、生产发布和产品验收证据分离。",
            "- [ ] L01、L02已停用，旧规则已有备份和回滚。", "",
        ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("profile", type=Path)
    render_parser = subparsers.add_parser("render")
    render_parser.add_argument("profile", type=Path)
    render_parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        with args.profile.open("r", encoding="utf-8-sig") as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            raise ValueError("配置根节点必须是JSON对象")
        errors = validate(data)
    except (OSError, json.JSONDecodeError, ValueError) as error:
        print(f"配置读取失败：{error}", file=sys.stderr)
        return 2
    if errors:
        for error in errors:
            print(f"[错误] {error}", file=sys.stderr)
        return 1
    if args.command == "validate":
        print(f"[通过] OneOS配置有效：{len(data['projects'])}个项目，每项目48项控制。")
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render(data), encoding="utf-8")
    print(f"[完成] 已生成执行计划：{args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
