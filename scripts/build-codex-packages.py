#!/usr/bin/env python3
"""Reproducible Codex-only packages, with source-byte and manifest verification.

Portable counterpart of build-dual-client-packages.ps1 for hosts without pwsh.
Never changes Cursor artifacts. Run lifecycle tests separately before publishing.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ("YunxiaoPM", "yunxiao-development-delivery", "development-brain", "YunxiaoQA", "yunxiao-release-operations")


def source_files(name):
    root = ROOT / "skills" / name
    return {str(path.relative_to(root.parent)).replace("\\", "/"): path
            for path in sorted(root.rglob("*")) if path.is_file()
            and "__pycache__" not in path.parts and path.suffix not in {".pyc", ".pyo"}
            and path.name != ".DS_Store"}


def check_sources():
    versions, updater_hashes = set(), set()
    for name in SKILLS:
        skill = ROOT / "skills" / name
        text = (skill / "SKILL.md").read_text(encoding="utf-8")
        version = re.search(r"(?:Suite version:|套件版本：|版本：)\s*`([^`]+)`", text)
        if not version:
            raise ValueError(f"{name}: missing suite version")
        versions.add(version.group(1))
        if f"scripts/ensure-daily-skill-update.mjs --current-skill {name}" not in text:
            raise ValueError(f"{name}: missing daily updater command")
        updater_hashes.add(hashlib.sha256((skill / "scripts/ensure-daily-skill-update.mjs").read_bytes()).hexdigest())
    if len(versions) != 1 or len(updater_hashes) != 1:
        raise ValueError("lifecycle versions or daily updaters differ")
    for rel in ("README.md", "docs/index.html"):
        for i, line in enumerate((ROOT / rel).read_text(encoding="utf-8").splitlines(), 1):
            if re.search(r"npx\s+skills\s+(add|update)\b", line) and any(s in line for s in SKILLS) \
                    and "--list" not in line and not re.search(r"(?:^|\s)(?:-g|--global)(?:\s|$)", line):
                raise ValueError(f"{rel}:{i}: lifecycle install command lacks global scope")
    return next(iter(versions))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    version = check_sources()
    output = ROOT / "packages/codex"
    manifest_path = output / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    for name in SKILLS:
        archive = output / f"{name}.zip"
        files = source_files(name)
        if not args.check:
            with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as z:
                for member, source in files.items():
                    info = zipfile.ZipInfo(member, date_time=(2020, 1, 1, 0, 0, 0))
                    info.compress_type = zipfile.ZIP_DEFLATED
                    info.external_attr = (0o100755 if source.stat().st_mode & 0o111 else 0o100644) << 16
                    z.writestr(info, source.read_bytes())
            manifest = [m for m in manifest if m["skill"] != name]
            manifest.append({"client": "codex", "skill": name, "archive": archive.name,
                             "sha256": hashlib.sha256(archive.read_bytes()).hexdigest()})
        matching = [m for m in manifest if m["skill"] == name]
        if len(matching) != 1 or matching[0].get("client") != "codex" \
                or matching[0].get("archive") != archive.name \
                or matching[0]["sha256"] != hashlib.sha256(archive.read_bytes()).hexdigest():
            raise ValueError(f"{name}: package manifest mismatch")
        with zipfile.ZipFile(archive) as z:
            if len(z.namelist()) != len(files) or set(z.namelist()) != set(files):
                raise ValueError(f"{name}: archive inventory mismatch")
            for member, source in files.items():
                if z.read(member) != source.read_bytes():
                    raise ValueError(f"{name}: archive/source drift: {member}")
    if not args.check:
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Codex {version}: {len(SKILLS)} packages and all source bytes verified; Cursor untouched")


if __name__ == "__main__":
    main()
