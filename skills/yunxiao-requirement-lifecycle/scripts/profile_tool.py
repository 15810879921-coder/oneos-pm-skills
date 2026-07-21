#!/usr/bin/env python3
"""Validate a project-scoped Yunxiao lifecycle profile and render an execution plan."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REQUIRED_LABELS = {"分析", "设计", "开发", "测试"}
REQUIRED_RULE_IDS = {f"R{index:02d}" for index in range(1, 13)}
REQUIRED_TASK_RULE_IDS = {f"TK{index:02d}" for index in range(1, 9)}
REQUIRED_CONTROL_IDS = {
    *REQUIRED_RULE_IDS,
    *REQUIRED_TASK_RULE_IDS,
    *(f"TC{index:02d}" for index in range(1, 4)),
    *(f"DF{index:02d}" for index in range(1, 4)),
    *(f"CI{index:02d}" for index in range(1, 4)),
    "L01",
    "L02",
}
VALID_MODES = {
    "manual",
    "native_rule",
    "integration_bridge",
    "disabled_legacy",
    "not_supported",
}
VALID_RELEASE_EVIDENCE_MODES = {
    "native_release_change",
    "pipeline_callback",
    "manual_release_confirmation",
}
SENSITIVE_FRAGMENTS = (
    "password",
    "passwd",
    "secret",
    "token",
    "cookie",
    "credential",
    "private_key",
    "otp",
    "密码",
    "密钥",
)


def load_profile(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("配置根节点必须是 JSON 对象")
    return data


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
            lower = str(key).lower()
            if any(fragment in lower for fragment in SENSITIVE_FRAGMENTS):
                found.append(current)
            found.extend(walk_sensitive_keys(nested, current))
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            found.extend(walk_sensitive_keys(nested, f"{prefix}[{index}]"))
    return found


def validate_control_list(
    controls: Any, label: str, errors: list[str]
) -> None:
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
        for key in ("evidence", "owner", "fallback"):
            require_text(control, key, item_label, errors)
        if mode in {"disabled_legacy", "not_supported"} and control.get("enabled") is not False:
            errors.append(f"{item_label} 的 {mode} 模式要求 enabled=false")
        if control_id in {"L01", "L02"} and mode not in {
            "disabled_legacy",
            "native_rule",
            "manual",
        }:
            errors.append(f"{item_label} 必须明确为停用旧规则、获批原生规则或人工处置")
    missing = sorted(REQUIRED_CONTROL_IDS - seen)
    if missing:
        errors.append(f"{label} 缺少控制项：" + "、".join(missing))


def validate_rule_instances(
    rules: Any, lifecycle: list[str], label: str, errors: list[str]
) -> None:
    if not isinstance(rules, list):
        errors.append(f"{label} 必须是数组")
        return
    seen: set[str] = set()
    orders: set[int] = set()
    expected = {
        f"R{index + 1:02d}": (lifecycle[index], lifecycle[index + 1])
        for index in range(12)
    }
    for index, rule in enumerate(rules):
        item_label = f"{label}[{index}]"
        if not isinstance(rule, dict):
            errors.append(f"{item_label} 必须是对象")
            continue
        rule_id = rule.get("id")
        if not is_text(rule_id):
            errors.append(f"{item_label}.id 不能为空")
            continue
        if rule_id in seen:
            errors.append(f"{label} 规则实例重复：{rule_id}")
        seen.add(rule_id)
        if rule_id not in REQUIRED_RULE_IDS:
            errors.append(f"{label} 未知规则实例：{rule_id}")
        mode = rule.get("mode")
        if mode not in {"manual", "native_rule", "integration_bridge", "not_supported"}:
            errors.append(f"{item_label}.mode 不合法")
        for key in ("actual_rule_name", "trigger", "source_status", "target_status", "action", "evidence"):
            require_text(rule, key, item_label, errors)
        conditions = rule.get("conditions")
        if not isinstance(conditions, list) or not conditions or not all(is_text(v) for v in conditions):
            errors.append(f"{item_label}.conditions 必须是非空文本数组")
        order = rule.get("order")
        if not isinstance(order, int) or order < 1:
            errors.append(f"{item_label}.order 必须是正整数")
        elif order in orders:
            errors.append(f"{label} 规则顺序重复：{order}")
        else:
            orders.add(order)
        if not isinstance(rule.get("enabled"), bool):
            errors.append(f"{item_label}.enabled 必须是布尔值")
        if rule.get("has_current_state_condition") is not True:
            errors.append(f"{item_label}.has_current_state_condition 必须为 true")
        if rule_id in expected:
            expected_source, expected_target = expected[rule_id]
            if rule.get("source_status") != expected_source:
                errors.append(f"{item_label}.source_status 应为 {expected_source}")
            if rule.get("target_status") != expected_target:
                errors.append(f"{item_label}.target_status 应为 {expected_target}")
    missing = sorted(REQUIRED_RULE_IDS - seen)
    if missing:
        errors.append(f"{label} 缺少规则实例：" + "、".join(missing))


def validate_task_rule_instances(rules: Any, label: str, errors: list[str]) -> None:
    if not isinstance(rules, list):
        errors.append(f"{label} 必须是数组")
        return
    seen: set[str] = set()
    orders: set[int] = set()
    for index, rule in enumerate(rules):
        item_label = f"{label}[{index}]"
        if not isinstance(rule, dict):
            errors.append(f"{item_label} 必须是对象")
            continue
        rule_id = rule.get("id")
        if not is_text(rule_id):
            errors.append(f"{item_label}.id 不能为空")
            continue
        if rule_id in seen:
            errors.append(f"{label} 规则实例重复：{rule_id}")
        seen.add(rule_id)
        if rule_id not in REQUIRED_TASK_RULE_IDS:
            errors.append(f"{label} 未知任务规则实例：{rule_id}")
        if rule.get("mode") not in {"manual", "native_rule", "integration_bridge", "not_supported"}:
            errors.append(f"{item_label}.mode 不合法")
        for key in ("actual_rule_name", "trigger", "scope", "source_state", "evidence"):
            require_text(rule, key, item_label, errors)
        for key in ("conditions", "actions"):
            values = rule.get(key)
            if not isinstance(values, list) or not values or not all(is_text(value) for value in values):
                errors.append(f"{item_label}.{key} 必须是非空文本数组")
        order = rule.get("order")
        if not isinstance(order, int) or order < 1:
            errors.append(f"{item_label}.order 必须是正整数")
        elif order in orders:
            errors.append(f"{label} 规则顺序重复：{order}")
        else:
            orders.add(order)
        if not isinstance(rule.get("enabled"), bool):
            errors.append(f"{item_label}.enabled 必须是布尔值")
    missing = sorted(REQUIRED_TASK_RULE_IDS - seen)
    if missing:
        errors.append(f"{label} 缺少任务规则实例：" + "、".join(missing))


def validate_project(
    project: Any, index: int, lifecycle: list[str], errors: list[str]
) -> None:
    label = f"projects[{index}]"
    if not isinstance(project, dict):
        errors.append(f"{label} 必须是对象")
        return
    for key in ("name", "work_item_type", "release_status", "final_status"):
        require_text(project, key, label, errors)
    if project.get("release_status") != lifecycle[11]:
        errors.append(f"{label}.release_status 必须与 lifecycle[11] 一致")
    if project.get("final_status") != lifecycle[12]:
        errors.append(f"{label}.final_status 必须与 lifecycle[12] 一致")

    labels = project.get("labels_observed")
    if not isinstance(labels, list) or not REQUIRED_LABELS.issubset(set(labels)):
        errors.append(f"{label}.labels_observed 必须包含：分析、设计、开发、测试")

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

    pipeline = project.get("test_pipeline")
    if not isinstance(pipeline, dict):
        errors.append(f"{label}.test_pipeline 必须是对象")
    else:
        for key in ("name", "environment", "evidence"):
            require_text(pipeline, key, f"{label}.test_pipeline", errors)
        for key in (
            "is_clone_for_callback_poc",
            "original_pipeline_unchanged",
            "docker_success_callback_enabled",
        ):
            if not isinstance(pipeline.get(key), bool):
                errors.append(f"{label}.test_pipeline.{key} 必须是布尔值")
        security = pipeline.get("callback_security")
        if not isinstance(security, dict):
            errors.append(f"{label}.test_pipeline.callback_security 必须是对象")
        else:
            security_keys = (
                "signed",
                "timestamp_checked",
                "replay_protected",
                "idempotent_by_execution_id",
                "failure_retry_tested",
            )
            for key in security_keys:
                if not isinstance(security.get(key), bool):
                    errors.append(f"{label}.test_pipeline.callback_security.{key} 必须是布尔值")
            if pipeline.get("docker_success_callback_enabled") is True:
                if pipeline.get("is_clone_for_callback_poc") is not True:
                    errors.append(f"{label} 启用回调时必须使用test流水线副本")
                if pipeline.get("original_pipeline_unchanged") is not True:
                    errors.append(f"{label} 启用回调时必须保持原流水线不变")
                if any(security.get(key) is not True for key in security_keys):
                    errors.append(f"{label} 启用回调时必须完成全部安全与重试验证")

    release = project.get("release_evidence")
    if not isinstance(release, dict):
        errors.append(f"{label}.release_evidence 必须是对象")
    else:
        if release.get("mode") not in VALID_RELEASE_EVIDENCE_MODES:
            errors.append(f"{label}.release_evidence.mode 不合法")
        for key in ("target_environment", "evidence"):
            require_text(release, key, f"{label}.release_evidence", errors)
        if release.get("test_success_is_production_release") is not False:
            errors.append(f"{label}.release_evidence.test_success_is_production_release 必须为 false")

    test_plan = project.get("test_plan")
    if not isinstance(test_plan, dict):
        errors.append(f"{label}.test_plan 必须是对象")
    else:
        for key in ("name", "evidence"):
            require_text(test_plan, key, f"{label}.test_plan", errors)
        if not isinstance(test_plan.get("requirement_formally_related"), bool):
            errors.append(f"{label}.test_plan.requirement_formally_related 必须是布尔值")
        states = test_plan.get("case_states_observed")
        if not isinstance(states, list) or not states or not all(is_text(v) for v in states):
            errors.append(f"{label}.test_plan.case_states_observed 必须是非空文本数组")

    defect = project.get("defect_workflow")
    if not isinstance(defect, dict):
        errors.append(f"{label}.defect_workflow 必须是对象")
    else:
        for key in ("fixed_status", "closed_status", "reopen_status", "evidence"):
            require_text(defect, key, f"{label}.defect_workflow", errors)
        if defect.get("fixed_is_terminal") is not False:
            errors.append(f"{label}.defect_workflow.fixed_is_terminal 必须为 false")
        if defect.get("tester_retest_required") is not True:
            errors.append(f"{label}.defect_workflow.tester_retest_required 必须为 true")

    validate_rule_instances(project.get("rule_instances"), lifecycle, f"{label}.rule_instances", errors)
    validate_task_rule_instances(
        project.get("task_rule_instances"), f"{label}.task_rule_instances", errors
    )
    validate_control_list(project.get("control_coverage"), f"{label}.control_coverage", errors)
    if not isinstance(project.get("adjunct_automations"), list):
        errors.append(f"{label}.adjunct_automations 必须是数组，可为空")


def validate(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if data.get("schema_version") != 3:
        errors.append("schema_version 必须为 3；旧版台账不包含阶段任务闭环")
    for key in ("organization", "work_item_type"):
        require_text(data, key, "profile", errors)

    lifecycle = data.get("lifecycle")
    if not isinstance(lifecycle, list) or len(lifecycle) != 13 or not all(is_text(v) for v in lifecycle):
        errors.append("lifecycle 必须包含 13 个非空有序状态")
        lifecycle = [str(index) for index in range(13)]
    elif len(set(lifecycle)) != len(lifecycle):
        errors.append("lifecycle 状态名称不能重复")

    labels = data.get("requirement_labels")
    if not isinstance(labels, list) or not REQUIRED_LABELS.issubset(set(labels)):
        errors.append("requirement_labels 必须包含：分析、设计、开发、测试")

    policy = data.get("automation_policy")
    if not isinstance(policy, dict):
        errors.append("automation_policy 必须是对象")
    else:
        for key in ("require_current_state_condition", "inspect_rule_order_and_cascades"):
            if policy.get(key) is not True:
                errors.append(f"automation_policy.{key} 必须为 true")
        for key in ("allow_automatic_final_close_without_acceptance", "zero_related_items_are_complete"):
            if policy.get(key) is not False:
                errors.append(f"automation_policy.{key} 必须为 false")
        events = policy.get("development_start_event_candidates")
        if not isinstance(events, list) or not events or not all(is_text(v) for v in events):
            errors.append("automation_policy.development_start_event_candidates 不能为空")
        if policy.get("require_code_assets_linked_to_requirement_and_development_task") is not True:
            errors.append(
                "automation_policy.require_code_assets_linked_to_requirement_and_development_task 必须为 true"
            )
        idempotency = policy.get("stage_task_creation_idempotency_key_components")
        if not isinstance(idempotency, list) or not idempotency or not all(is_text(v) for v in idempotency):
            errors.append("automation_policy.stage_task_creation_idempotency_key_components 不能为空")

    test_policy = data.get("test_closure_policy")
    if not isinstance(test_policy, dict):
        errors.append("test_closure_policy 必须是对象")
    else:
        if test_policy.get("defect_fixed_is_terminal") is not False:
            errors.append("test_closure_policy.defect_fixed_is_terminal 必须为 false")
        if test_policy.get("require_tester_retest") is not True:
            errors.append("test_closure_policy.require_tester_retest 必须为 true")
        for key in ("accepted_case_states", "rejected_case_states"):
            values = test_policy.get(key)
            if not isinstance(values, list) or not values or not all(is_text(v) for v in values):
                errors.append(f"test_closure_policy.{key} 不能为空")

    projects = data.get("projects")
    if not isinstance(projects, list) or not projects:
        errors.append("projects 至少包含一个项目")
    else:
        names: set[str] = set()
        for index, project in enumerate(projects):
            validate_project(project, index, lifecycle, errors)
            if isinstance(project, dict) and is_text(project.get("name")):
                name = project["name"]
                if name in names:
                    errors.append(f"项目名称重复：{name}")
                names.add(name)

    sensitive = walk_sensitive_keys(data)
    if sensitive:
        errors.append("配置中禁止出现敏感字段：" + "、".join(sensitive))
    if "请填写" in json.dumps(data, ensure_ascii=False):
        errors.append("仍存在“请填写”占位符")
    return errors


def render(data: dict[str, Any]) -> str:
    lines = [
        "# 云效需求生命周期自动化执行计划",
        "",
        f"- 组织：{data['organization']}",
        f"- 工作项类型：{data['work_item_type']}",
        f"- 项目数：{len(data['projects'])}",
        "- 完整性口径：每项目12个需求规则实例、8个任务规则实例、31个闭环控制项。",
        "- 安全边界：不修改现有生产流水线；不记录任何凭据或密钥。",
        "",
    ]
    for project in data["projects"]:
        lines.extend([
            f"## 项目：{project['name']}",
            "",
            f"- 发布状态：{project['release_status']}",
            f"- 最终状态：{project['final_status']}",
            f"- test流水线：{project['test_pipeline']['name']}",
            f"- 发布证据方式：{project['release_evidence']['mode']}",
            "",
            "### 仓库覆盖",
            "",
            "| 仓库 | 角色 | 集成分支 | Codeup已集成 | 纳入全部MR门禁 | 证据 |",
            "|---|---|---|---|---|---|",
        ])
        for repo in project["repositories"]:
            lines.append(
                f"| {repo['name']} | {repo['role']} | {repo['integration_branch']} | "
                f"{'是' if repo['codeup_integrated'] else '否'} | "
                f"{'是' if repo['required_for_mr_gate'] else '否'} | {repo['evidence']} |"
            )
        lines.extend([
            "",
            "### R01–R12实际规则实例",
            "",
            "| ID | 实现 | 实际规则/门禁 | 触发 | 流转 | 条件 | 顺序 | 启用 | 证据 |",
            "|---|---|---|---|---|---|---:|---|---|",
        ])
        for rule in sorted(project["rule_instances"], key=lambda item: item["order"]):
            conditions = "；".join(rule["conditions"])
            lines.append(
                f"| {rule['id']} | {rule['mode']} | {rule['actual_rule_name']} | {rule['trigger']} | "
                f"{rule['source_status']} → {rule['target_status']} | {conditions} | {rule['order']} | "
                f"{'是' if rule['enabled'] else '否'} | {rule['evidence']} |"
            )
        lines.extend([
            "",
            "### TK01–TK08任务规则实例",
            "",
            "| ID | 实现 | 实际规则/门禁 | 触发 | 作用域 | 源状态 | 条件 | 动作 | 顺序 | 启用 | 证据 |",
            "|---|---|---|---|---|---|---|---|---:|---|---|",
        ])
        for rule in sorted(project["task_rule_instances"], key=lambda item: item["order"]):
            conditions = "；".join(rule["conditions"])
            actions = "；".join(rule["actions"])
            lines.append(
                f"| {rule['id']} | {rule['mode']} | {rule['actual_rule_name']} | {rule['trigger']} | "
                f"{rule['scope']} | {rule['source_state']} | {conditions} | {actions} | {rule['order']} | "
                f"{'是' if rule['enabled'] else '否'} | {rule['evidence']} |"
            )
        lines.extend([
            "",
            "### 31项完整性台账",
            "",
            "| 控制ID | 实现方式 | 启用 | 观察证据 | 负责人 | 回退方案 |",
            "|---|---|---|---|---|---|",
        ])
        for control in sorted(project["control_coverage"], key=lambda item: item["id"]):
            lines.append(
                f"| {control['id']} | {control['mode']} | {'是' if control['enabled'] else '否'} | "
                f"{control['evidence']} | {control['owner']} | {control['fallback']} |"
            )
        adjunct = project["adjunct_automations"]
        lines.extend([
            "",
            "### 范围外通用自动化盘点",
            "",
            "- " + ("；".join(map(str, adjunct)) if adjunct else "未纳入；如需通知、自动指派、SLA、字段同步等，应单独授权和设计。"),
            "",
        ])
    lines.extend([
        "## 执行检查",
        "",
        "- [ ] 两个或多个项目的规则实例、控制台账和证据已分别填写。",
        "- [ ] 已逐条读取真实触发配置、规则顺序、启用状态和执行账号。",
        "- [ ] 已检查后继规则、重复规则和跨阶段连锁流转。",
        "- [ ] 已验证失败用例、缺陷已修复、复测通过/失败时双方状态一致。",
        "- [ ] 已逐仓库确认真实dev/develop分支、正式关联和全部MR门禁。",
        "- [ ] 已区分test部署、生产发布、发布变更和业务验收。",
        "- [ ] 已执行正向、负向、异步、多仓库、失败重试和旧规则连锁测试。",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate_parser = subparsers.add_parser("validate", help="验证项目配置")
    validate_parser.add_argument("profile", type=Path)
    render_parser = subparsers.add_parser("render", help="生成 Markdown 执行计划")
    render_parser.add_argument("profile", type=Path)
    render_parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    try:
        data = load_profile(args.profile)
        errors = validate(data)
    except (OSError, json.JSONDecodeError, ValueError) as error:
        print(f"配置读取失败：{error}", file=sys.stderr)
        return 2
    if errors:
        for error in errors:
            print(f"[错误] {error}", file=sys.stderr)
        return 1
    if args.command == "validate":
        print(
            f"[通过] 配置有效：{len(data['projects'])} 个项目；"
            "每项目12个需求规则实例、8个任务规则实例、31个闭环控制项。"
        )
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render(data), encoding="utf-8")
    print(f"[完成] 已生成执行计划：{args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
