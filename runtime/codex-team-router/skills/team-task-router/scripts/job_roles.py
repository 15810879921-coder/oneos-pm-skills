#!/usr/bin/env python3
"""Job-role classification and transcript evidence helpers.

This module deliberately keeps job ownership separate from model routing.  It
never treats user prose, assistant prose, or an arbitrary tool result as proof
that a skill was read.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import shlex
from typing import Any

ROLE_ORDER = ("product", "ux", "development", "qa")
DEFAULT_SKILLS = {
    "product": "oneos-pm-product",
    "ux": "oneos-ux-guide",
    "development": "oneos-dev-delivery",
    "qa": "oneos-qa-verify",
}
ROLE_SKILL_SUFFIX = {
    "product": ("pm-product",),
    "ux": ("ux-guide",),
    "development": ("dev-delivery",),
    "qa": ("qa-verify",),
}
PROJECT_SKILLS = {
    "yuzar": {
        "product": "yuzar-pm-product",
        "development": "yuzar-dev-delivery",
        "qa": "yuzar-qa-verify",
    },
    "quzar": {
        "product": "quzar-pm-product",
        "development": "quzar-dev-delivery",
        "qa": "quzar-qa-verify",
    },
}

_PRODUCT = re.compile(r"(?:需求(?:分析|梳理|整理|确认|评审|范围|清单)?|产品方案|功能范围|功能清单|用户流程|验收条件|\bprd\b)", re.I)
_UX = re.compile(r"(?:(?:页面|界面|原型|视觉|布局|组件|交互|体验|按钮|颜色|样式|\bui\b|\bux\b).{0,12}(?:设计|调整|修改|改|统一|评审|方案|优化|实现)|(?:设计|调整|修改|改|统一|评审|优化|实现).{0,12}(?:页面|界面|原型|视觉|布局|组件|交互|体验|按钮|颜色|样式|\bui\b|\bux\b))", re.I)
_DEV = re.compile(r"(?:修改|审查|修复|调试|排查|启动|构建|编译|安装|升级).{0,12}(?:代码|源码|仓库|服务|开发环境|依赖|构建|编译|接口)|(?:代码|源码|仓库|本机服务|开发环境|依赖|构建|编译).{0,12}(?:修改|审查|修复|调试|排查|启动|失败|报错|问题)|(?:bug|缺陷).{0,10}(?:修复|定位|排查)", re.I)
_QA = re.compile(r"(?:写|执行|跑|补|做|进行|制定|新增|编写)(?:单元测试|集成测试|自动化测试|测试|验证|测试用例|测试计划|测试方案|测试报告|回归测试|回归|复测|验收验证|缺陷验证)|(?:单元测试|集成测试|自动化测试|测试用例|测试计划|测试方案|测试报告|回归测试|回归|复测|验收验证|缺陷验证)|(?:测试|验证).{0,8}(?:执行|结果|计划|方案|报告|通过|失败|回归|修复)", re.I)
_NEGATOR = r"(?:不要|别|先不|暂不|无需|不需要|禁止|不再|不做|不)"
_DEV_OBJECT = r"(?:代码|源码|仓库|服务|开发环境|依赖|构建|编译|接口|文件)"
_DEV_ACTION = r"(?:修改|改动|改|开发|实现|编写|写|动|审查|修复|调试)"
_NEG_DEV = re.compile(_NEGATOR + r"\s*(?:再\s*)?(?:" + _DEV_ACTION + r"\s*)?" + _DEV_OBJECT
                      + r"(?:\s*" + _DEV_ACTION + r")?", re.I)
_NEG_QA = re.compile(_NEGATOR + r"\s*(?:再\s*)?(?:执行|跑|做|进行)?\s*(?:回归测试|自动化测试|测试|验证|回归|复测)", re.I)
_UX_OBJECT = r"(?:页面|界面|原型|视觉|布局|组件|交互|\bui\b|\bux\b)"
_UX_ACTION = r"(?:设计|修改|改动|改|实现)"
_NEG_UX = re.compile(_NEGATOR + r"\s*(?:" + _UX_ACTION + r"\s*)?" + _UX_OBJECT
                     + r"(?:\s*" + _UX_ACTION + r")?", re.I)
_NEG_PRODUCT = re.compile(_NEGATOR + r"\s*(?:分析|梳理|整理|确认|评审|制定|写)?\s*(?:需求|产品方案|功能范围|功能清单|用户流程|验收条件|\bprd\b)", re.I)
_ANALYSIS_ONLY = re.compile(r"(?:只|仅)\s*(?:做|进行)?\s*.{0,10}(?:分析|看看|评审)", re.I)
_DOCUMENT_ONLY = re.compile(r"(?:翻译|读文档|阅读文档|整理(?:excel|表格|录音|文档)|转写录音|查询时间|几点了)", re.I)


def classify_prompt(prompt: str) -> list[str]:
    """Return required roles in business-stage order for the user prompt."""
    if not isinstance(prompt, str) or not prompt.strip():
        return []
    text = prompt.strip()
    product_text = _NEG_PRODUCT.sub(" ", text)
    ux_text = _NEG_UX.sub(" ", text)
    dev_text = _NEG_DEV.sub(" ", text)
    qa_text = _NEG_QA.sub(" ", text)
    # Prompts that define the routing vocabulary often quote every business
    # role.  Those mentions describe configuration data, not four live stages.
    routing_meta = bool(re.search(r"(?:岗位|技能).{0,16}(?:触发|路由|配置|规则)|team-task-router|execution_gate|执行门禁", text, re.I))
    if routing_meta:
        roles = []
        if (_DEV.search(dev_text)
                or re.search(r"(?:修复|增强|修改|实现|调试|审查).{0,40}(?:team-task-router|execution_gate|执行门禁|代码|脚本|运行时|安装器)", dev_text, re.I)):
            roles.append("development")
        if _QA.search(qa_text):
            roles.append("qa")
        return [role for role in ROLE_ORDER if role in roles]
    roles: list[str] = []
    if _PRODUCT.search(product_text):
        roles.append("product")
    ux = bool(_UX.search(ux_text))
    if ux:
        roles.append("ux")
    no_change = bool(_NEG_DEV.search(text) or _NEG_UX.search(text) or _ANALYSIS_ONLY.search(text))
    # Read-only code/environment diagnosis still needs development ownership;
    # the negation limits mutation authority rather than removing the role.
    if _DEV.search(dev_text):
        roles.append("development")
    # A requested UI change normally reaches source implementation.  A design
    # review or explicitly analysis-only request stays in the UX phase.
    if ux and not no_change and re.search(r"(?:改|修改|调整|统一|修复|实现|优化|换成|删除|增加|新增)", text):
        roles.append("development")
    if _QA.search(qa_text):
        roles.append("qa")
    if _DOCUMENT_ONLY.search(text) and not any((_PRODUCT.search(text), _UX.search(text), _DEV.search(text), _QA.search(text))):
        return []
    return [role for role in ROLE_ORDER if role in roles]


def project_family(cwd: str | Path | None) -> str | None:
    value = str(cwd or "").lower()
    if "yuzar" in value:
        return "yuzar"
    if "quzar" in value or "玉衢" in value:
        return "quzar"
    return None


def resolve_skill(home: Path, role: str, cwd: str | Path | None = None, requested: str | None = None) -> tuple[str, Path, str]:
    if role not in ROLE_ORDER:
        raise ValueError("unknown job role: " + str(role))
    family = project_family(cwd)
    candidates: list[tuple[str, str]] = []
    if requested:
        known = {DEFAULT_SKILLS[role], *(mapping[role] for mapping in PROJECT_SKILLS.values() if role in mapping)}
        if requested not in known and not any(requested.endswith("-" + suffix) or requested == suffix
                                               for suffix in ROLE_SKILL_SUFFIX[role]):
            raise ValueError(f"skill {requested} does not match job role {role}")
        candidates.append((requested, "explicit"))
    if family and role in PROJECT_SKILLS.get(family, {}):
        candidates.append((PROJECT_SKILLS[family][role], "project"))
    candidates.append((DEFAULT_SKILLS[role], "default"))
    seen = set()
    roots = []
    if cwd:
        current = Path(cwd).resolve()
        for parent in (current, *current.parents):
            for relative in (Path(".agents/skills"), Path(".cursor/skills")):
                root = parent / relative
                if root.is_dir() and root not in roots:
                    roots.append(root)
            if parent == parent.parent:
                break
    global_agents = home.parent / ".agents" / "skills"
    if global_agents.is_dir() and global_agents not in roots:
        roots.append(global_agents)
    roots.append(home / "skills")
    for name, source in candidates:
        if name in seen:
            continue
        seen.add(name)
        for root in roots:
            path = root / name / "SKILL.md"
            if path.is_file() and not path.is_symlink():
                return name, path.resolve(), source
    raise ValueError(f"no readable skill installed for job role {role}")


def skill_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _text(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _call_command(payload: dict[str, Any]) -> str | None:
    kind = payload.get("type")
    if kind == "function_call":
        raw = payload.get("arguments")
        try:
            args = json.loads(raw) if isinstance(raw, str) else raw
        except ValueError:
            return None
        if isinstance(args, dict):
            value = args.get("cmd", args.get("command"))
            return value if isinstance(value, str) else None
    if kind == "custom_tool_call" and payload.get("name") == "exec":
        value = payload.get("input")
        return value if isinstance(value, str) else None
    return None


def _explicit_read(command: str, skill_path: Path, role: str | None = None) -> bool:
    """Recognize a narrow read invocation; path mentions in other commands fail."""
    target = str(skill_path.resolve())
    if (role and "execution_gate.py" in command and "role-read" in command
            and re.search(r"--role(?:=|\s+)[\"']?" + re.escape(role) + r"(?:[\"'\s]|$)", command)):
        return True
    aliases = [target]
    for candidate in re.findall(r"/(?:[^\s\"'`;,&)\]}]+/)+SKILL\.md", command):
        try:
            candidate_path = Path(candidate)
            same_file = candidate_path.resolve() == skill_path.resolve()
            # A repository can install an identical project-role skill beside
            # the global installation.  Accept that concrete read only when
            # both the skill directory name and current bytes match.
            equivalent_install = (candidate_path.name == "SKILL.md"
                                  and candidate_path.parent.name == skill_path.parent.name
                                  and candidate_path.is_file()
                                  and skill_digest(candidate_path) == skill_digest(skill_path))
            if (same_file or equivalent_install) and candidate not in aliases:
                aliases.append(candidate)
        except OSError:
            continue
    if not any(candidate in command for candidate in aliases):
        return False
    # Direct shell reads and code-mode tools.exec_command wrappers are both in
    # assistant call input.  Other parallel rg/find calls neither help nor
    # invalidate the concrete read call.
    boundary = r"(?:^|[\"']?cmd[\"']?\s*:\s*[\"'`]|[;&]\s*)"
    direct_reader = r"(?:sed\s+-n\s+[\"']?[^\s\"']+[\"']?|head(?:\s+-n\s+\d+)?|tail(?:\s+-n\s+\d+)?)"
    absolute_cat_arg = r"[\"'`]?/[^\s\"'`;,&)\]}]+[\"'`]?"
    for candidate in aliases:
        suffix = (r"[\"'`]?(?:[\s;,&)\]}]|$)")
        if re.search(boundary + r"\s*" + direct_reader + r"\s+[\"'`]?"
                     + re.escape(candidate) + suffix, command):
            return True
        # ``cat`` accepts several files in one invocation.  Every preceding
        # argument must itself be an absolute path, so prose such as
        # ``echo cat ...`` and unrelated report text remain ineligible.
        if re.search(boundary + r"\s*cat(?:\s+" + absolute_cat_arg + r")*\s+[\"'`]?"
                     + re.escape(candidate) + suffix, command):
            return True
    return False


def _content_variants(content: str) -> list[str]:
    variants = [content]
    encoded = content
    for _ in range(3):
        encoded = json.dumps(encoded, ensure_ascii=False)
        variants.extend((encoded, encoded[1:-1]))
    return variants


def _unwrapped_output_strings(value: Any, max_depth: int = 8, max_nodes: int = 256) -> list[str]:
    """Unwrap native text/output/content envelopes with fixed resource bounds."""
    found: list[str] = []
    pending: list[tuple[Any, int]] = [(value, 0)]
    visited = 0
    while pending and visited < max_nodes:
        current, depth = pending.pop()
        visited += 1
        if depth > max_depth:
            continue
        if isinstance(current, str):
            found.append(current)
            stripped = current.strip()
            if depth < max_depth and stripped[:1] in {"{", "["}:
                try:
                    pending.append((json.loads(stripped), depth + 1))
                except (TypeError, ValueError):
                    pass
        elif isinstance(current, list):
            pending.extend((item, depth + 1) for item in reversed(current[:max_nodes - visited]))
        elif isinstance(current, dict):
            for key in ("text", "output", "content"):
                if key in current:
                    pending.append((current[key], depth + 1))
    return found


def _successful_output(output: str, skill_path: Path, skill_name: str) -> bool:
    if not output.strip():
        return False
    lowered = output.lower()
    if any(marker in lowered for marker in ("no such file", "permission denied", "traceback", "script failed", "exit_code\":1", "exit code 1")):
        return False
    # Bind the receipt to the complete current bytes.  JSONL tool results can
    # wrap/escape content more than once, so check a small deterministic set of
    # representations.  A stale read containing only the same frontmatter name
    # must not acquire the new file hash.
    try:
        content = skill_path.read_text()
    except OSError:
        return False
    if any(value and value in output for value in _content_variants(content)):
        return True
    # Native code-mode can serialize a role-read result through several
    # text/output JSON envelopes.  Accept only an exactly unwrapped full body;
    # prefixes, timestamps, and other partial-read signals remain insufficient.
    return any(candidate == content for candidate in _unwrapped_output_strings(output))


def transcript_read_evidence(path: str | Path, skill_path: Path, skill_name: str, role: str | None = None) -> dict[str, Any] | None:
    """Pair an assistant read call with its exact successful tool result."""
    calls: dict[str, tuple[int, dict[str, Any], str]] = {}
    outputs: dict[str, tuple[int, str]] = {}
    p = Path(path)
    if not p.is_file():
        return None
    with p.open(errors="replace") as handle:
        for line_no, line in enumerate(handle, 1):
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if row.get("type") != "response_item" or not isinstance(row.get("payload"), dict):
                continue
            payload = row["payload"]
            call_id = payload.get("call_id")
            if not isinstance(call_id, str):
                continue
            if payload.get("type") in {"function_call", "custom_tool_call"}:
                command = _call_command(payload)
                if command and _explicit_read(command, skill_path, role):
                    calls[call_id] = (line_no, payload, command)
            elif payload.get("type") in {"function_call_output", "custom_tool_call_output"}:
                outputs[call_id] = (line_no, _text(payload.get("output")))
    for call_id, (call_line, payload, _) in calls.items():
        result = outputs.get(call_id)
        if result and result[0] > call_line and _successful_output(result[1], skill_path, skill_name):
            return {"transcript": str(p.resolve()), "call_id": call_id, "call_line": call_line,
                    "output_line": result[0], "tool": payload.get("name"), "skill_sha256": skill_digest(skill_path)}
    return None


def validate_result_evidence(items: Any) -> list[dict[str, Any]]:
    if not isinstance(items, list) or not items:
        raise ValueError("result evidence must be a non-empty list")
    clean = []
    for item in items:
        if not isinstance(item, dict) or set(item) - {"kind", "path", "call_id"}:
            raise ValueError("invalid result evidence item")
        kind, raw_path = item.get("kind"), item.get("path")
        if kind not in {"file", "transcript"} or not isinstance(raw_path, str):
            raise ValueError("evidence kind must be file or transcript with path")
        path = Path(raw_path)
        if not path.is_absolute() or not path.is_file():
            raise ValueError("evidence path must be an existing absolute file: " + raw_path)
        row = {"kind": kind, "path": str(path.resolve())}
        if kind == "transcript":
            call_id = item.get("call_id")
            if not isinstance(call_id, str) or not call_id.strip():
                raise ValueError("transcript evidence requires call_id")
            if call_id not in path.read_text(errors="replace"):
                raise ValueError("transcript call_id not found")
            row["call_id"] = call_id
        clean.append(row)
    return clean
