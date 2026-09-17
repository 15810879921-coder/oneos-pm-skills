#!/usr/bin/env python3
"""Validate the Yunxiao lifecycle Skill index and render its Markdown view."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs/yunxiao-lifecycle-skill-index.json"
OUTPUT = ROOT / "docs/yunxiao-lifecycle-skill-index.md"
README = ROOT / "README.md"
SCHEMA = "oneos.yunxiao-lifecycle-skill-index/v1"
SKILL_ORDER = (
    "YunxiaoPM",
    "yunxiao-development-delivery",
    "development-brain",
    "YunxiaoQA",
    "yunxiao-release-operations",
)
VERSION_PATTERN = re.compile(r"(?:Suite version:|套件版本：|版本：)\s*`([^`]+)`")


def load_index() -> dict:
    return json.loads(SOURCE.read_text(encoding="utf-8"))


def suite_versions() -> set[str]:
    versions: set[str] = set()
    for name in SKILL_ORDER:
        text = (ROOT / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
        match = VERSION_PATTERN.search(text)
        if not match:
            raise ValueError(f"{name}: SKILL.md 缺少套件版本")
        versions.add(match.group(1))
    return versions


def _check_path(relative: str | None, owner: str, field: str) -> None:
    if relative is None:
        return
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"{owner}.{field}: 只允许仓库内相对路径: {relative}")
    if not (ROOT / path).is_file():
        raise ValueError(f"{owner}.{field}: 文件不存在: {relative}")


def validate_index(index: dict) -> None:
    if index.get("schemaVersion") != SCHEMA:
        raise ValueError(f"schemaVersion 必须为 {SCHEMA}")

    skills = index.get("skills")
    if not isinstance(skills, list):
        raise ValueError("skills 必须为数组")
    names = tuple(item.get("name") for item in skills)
    if names != SKILL_ORDER:
        raise ValueError(f"Skill 顺序或范围错误: {names}")
    if [item.get("order") for item in skills] != list(range(1, len(SKILL_ORDER) + 1)):
        raise ValueError("Skill order 必须从 1 连续递增")

    versions = suite_versions()
    if len(versions) != 1 or index.get("suiteVersion") not in versions:
        raise ValueError(
            f"索引版本 {index.get('suiteVersion')} 与 Skill 套件版本 {sorted(versions)} 不一致"
        )

    known = set(names)
    for item in skills:
        owner = item["name"]
        for field in ("displayName", "lifecycleStage", "responsibility", "writeBoundary"):
            if not isinstance(item.get(field), str) or not item[field].strip():
                raise ValueError(f"{owner}.{field}: 不能为空")
        _check_path(item.get("entrypoint"), owner, "entrypoint")
        _check_path(item.get("commandReference"), owner, "commandReference")
        for field in ("keyReferences", "keyScripts"):
            values = item.get(field)
            if not isinstance(values, list) or not values:
                raise ValueError(f"{owner}.{field}: 必须是非空数组")
            if len(values) != len(set(values)):
                raise ValueError(f"{owner}.{field}: 存在重复路径")
            for relative in values:
                _check_path(relative, owner, field)
        for field in ("handoffFrom", "handoffTo"):
            values = item.get(field)
            if not isinstance(values, list) or any(value not in known for value in values):
                raise ValueError(f"{owner}.{field}: 包含未知 Skill")

    routes = index.get("routes")
    if not isinstance(routes, list) or {route.get("skill") for route in routes} != known:
        raise ValueError("routes 必须覆盖且只覆盖五个生命周期 Skill")
    for route in routes:
        if not route.get("intent") or not route.get("examples"):
            raise ValueError(f"{route.get('skill')}: 路由意图和示例不能为空")

    readme_text = README.read_text(encoding="utf-8")
    if "docs/yunxiao-lifecycle-skill-index.md" not in readme_text:
        raise ValueError("README.md 缺少云效生命周期 Skill 索引入口")


def _link(relative: str | None, label: str | None = None) -> str:
    if relative is None:
        return "隐式触发，无独立口令页"
    return f"[{label or Path(relative).name}](../{relative})"


def render_markdown(index: dict) -> str:
    lines = [
        "# 云效生命周期 Skill 索引",
        "",
        "> 本文件由 `scripts/build-yunxiao-skill-index.py` 从 "
        "`docs/yunxiao-lifecycle-skill-index.json` 生成，请勿手工修改。",
        "",
        f"- 套件版本：`{index['suiteVersion']}`",
        f"- 范围：{index['scope']}",
        "- 权威入口：各 Skill 的 `SKILL.md`；本索引只负责定位，不替代运行时规则。",
        "",
        "## 生命周期目录",
        "",
        "| 顺序 | Skill | 阶段 | 职责 | 口令/规则入口 | 写入边界 |",
        "|---:|---|---|---|---|---|",
    ]
    for item in index["skills"]:
        skill_link = _link(item["entrypoint"], item["name"])
        command_link = _link(item["commandReference"], "口令")
        lines.append(
            f"| {item['order']} | {skill_link}<br>{item['displayName']} | "
            f"{item['lifecycleStage']} | {item['responsibility']} | {command_link} | "
            f"{item['writeBoundary']} |"
        )

    lines.extend([
        "",
        "## 自然语言路由",
        "",
        "| 意图 | 负责 Skill | 示例 |",
        "|---|---|---|",
    ])
    for route in index["routes"]:
        lines.append(
            f"| {route['intent']} | `{route['skill']}` | "
            f"{'、'.join(f'`{example}`' for example in route['examples'])} |"
        )

    lines.extend([
        "",
        "## 交接关系",
        "",
    ])
    for item in index["skills"]:
        incoming = "、".join(f"`{name}`" for name in item["handoffFrom"]) or "无固定上游"
        outgoing = "、".join(f"`{name}`" for name in item["handoffTo"]) or "无固定下游"
        lines.append(f"- `{item['name']}`：上游 {incoming}；下游 {outgoing}。")

    lines.extend([
        "",
        "## 关键文件",
        "",
    ])
    for item in index["skills"]:
        refs = "、".join(_link(path) for path in item["keyReferences"])
        scripts = "、".join(_link(path) for path in item["keyScripts"])
        lines.append(f"- `{item['name']}`：规则 {refs}；执行/校验 {scripts}。")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="仅校验索引和已生成 Markdown")
    args = parser.parse_args()

    index = load_index()
    validate_index(index)
    rendered = render_markdown(index)
    if args.check:
        if not OUTPUT.is_file() or OUTPUT.read_text(encoding="utf-8") != rendered:
            raise ValueError(f"生成文件已漂移，请运行: python {Path(__file__).name}")
    else:
        OUTPUT.write_text(rendered, encoding="utf-8", newline="\n")
    print(f"Yunxiao lifecycle index {index['suiteVersion']}: {len(index['skills'])} skills verified")


if __name__ == "__main__":
    main()
