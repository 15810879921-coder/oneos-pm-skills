#!/usr/bin/env python3
"""Verify the five installed lifecycle Skills without assuming an installation root."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


SCHEMA = "oneos.lifecycle-suite-state/v1"
SUITE_VERSION = "10.0.0"
REQUIRED = {
    "YunxiaoPM", "yunxiao-development-delivery", "development-brain",
    "YunxiaoQA", "yunxiao-release-operations",
}


def verify(values: list[str]) -> dict:
    paths: dict[str, Path] = {}
    for value in values:
        if "=" not in value:
            raise ValueError("--skill格式必须为名称=SKILL.md绝对路径")
        name, raw_path = value.split("=", 1)
        name = name.strip()
        if name in paths:
            raise ValueError(f"Skill重复：{name}")
        paths[name] = Path(raw_path.strip())
    if set(paths) != REQUIRED:
        raise ValueError("必须精确提供五个生命周期Skill：" + ",".join(sorted(REQUIRED)))
    versions: dict[str, str | None] = {}
    evidence: dict[str, str] = {}
    for name, path in paths.items():
        if not path.is_absolute() or not path.is_file() or path.name.lower() != "skill.md":
            raise ValueError(f"{name}必须指向存在的SKILL.md绝对路径")
        text = path.read_text(encoding="utf-8")
        matches = sorted(set(re.findall(r"(?<![0-9])10\.0\.0(?![0-9])", text)))
        versions[name] = matches[0] if len(matches) == 1 else None
        evidence[name] = str(path.resolve())
    mismatched = sorted(name for name, version in versions.items() if version != SUITE_VERSION)
    return {
        "schemaVersion": SCHEMA,
        "suiteVersion": SUITE_VERSION,
        "verified": not mismatched,
        "skills": versions,
        "evidencePaths": evidence,
        "mismatched": mismatched,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="回读五个云效生命周期Skill的安装版本")
    parser.add_argument("--skill", action="append", required=True, help="名称=SKILL.md绝对路径")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        result = verify(args.skill)
    except (OSError, ValueError) as exc:
        print(json.dumps({"verified": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 2
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["verified"] else 2


if __name__ == "__main__":
    sys.exit(main())
