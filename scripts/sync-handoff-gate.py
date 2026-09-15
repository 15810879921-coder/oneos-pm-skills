#!/usr/bin/env python3
"""Generate/check self-contained handoff validators without cross-install imports."""
from pathlib import Path
import argparse

ROOT = Path(__file__).resolve().parents[1]
TARGETS = ("yunxiao-development-delivery", "YunxiaoQA", "yunxiao-release-operations")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    source = (ROOT / "skills/YunxiaoPM/scripts/handoff_gate.py").read_bytes()
    reference = (ROOT / "skills/YunxiaoPM/references/handoff-gate.md").read_bytes()
    mismatches = []
    for name in TARGETS:
        path = ROOT / "skills" / name / "scripts/handoff_gate.py"
        if args.check:
            if not path.is_file() or path.read_bytes() != source:
                mismatches.append(name)
        else:
            path.write_bytes(source)
        ref_path = ROOT / "skills" / name / "references/handoff-gate.md"
        if args.check:
            if not ref_path.is_file() or ref_path.read_bytes() != reference:
                mismatches.append(name + ":reference")
        else:
            ref_path.write_bytes(reference)
    if mismatches:
        raise SystemExit("handoff-gate copies drifted: " + ", ".join(mismatches))
    print("handoff-gate copies OK")


if __name__ == "__main__":
    main()
