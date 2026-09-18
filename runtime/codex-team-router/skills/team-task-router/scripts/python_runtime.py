"""Locate the bundled Python runtime required by the execution gate.

This module intentionally uses only Python 3.9-compatible syntax because it is
loaded before the gate imports Python 3.11-only modules such as ``tomllib``.
"""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
from typing import List, Optional


_REEXEC_ENV = "CODEX_EXECUTION_GATE_RUNTIME_REEXEC"


def _is_supported(path: Path) -> bool:
    """Return whether *path* is an executable Python 3.11+ interpreter."""
    if not path.is_file() or not os.access(str(path), os.X_OK):
        return False
    try:
        result = subprocess.run(
            [str(path), "-c", "import sys; print('%d.%d' % sys.version_info[:2])"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=True,
            text=True,
            timeout=2,
        )
        major, minor = (int(part) for part in result.stdout.strip().split(".", 1))
        return (major, minor) >= (3, 11)
    except (OSError, ValueError, subprocess.SubprocessError):
        return False


def candidate_paths() -> List[Path]:
    """Return deterministic local candidates without installing or replacing Python."""
    candidates = []
    explicit = os.environ.get("CODEX_PYTHON")
    if explicit:
        candidates.append(Path(explicit).expanduser())

    cache_root = Path.home() / ".cache" / "codex-runtimes"
    if cache_root.is_dir():
        candidates.extend(sorted(cache_root.glob("**/bin/python3")))
        candidates.extend(sorted(cache_root.glob("**/bin/python3.*")))

    unique = []
    seen = set()
    for path in candidates:
        resolved = path.resolve()
        if resolved not in seen:
            seen.add(resolved)
            unique.append(resolved)
    return unique


def find_supported_python() -> Optional[Path]:
    """Find the first usable local Python 3.11+ runtime."""
    return next((path for path in candidate_paths() if _is_supported(path)), None)


def reexec_if_needed(script: str, argv: List[str]) -> None:
    """Re-enter this script with a supported runtime, preserving argv and status."""
    if sys.version_info >= (3, 11):
        return
    if os.environ.get(_REEXEC_ENV) == "1":
        raise SystemExit(
            "execution_gate.py requires Python 3.11+ and runtime re-entry did not succeed; "
            "unset %s only after fixing the configured runtime" % _REEXEC_ENV
        )

    runtime = find_supported_python()
    if runtime is None:
        raise SystemExit(
            "execution_gate.py requires Python 3.11+ (tomllib); no compatible local runtime "
            "was found. Install or configure Python 3.11+ via CODEX_PYTHON."
        )

    environment = os.environ.copy()
    environment[_REEXEC_ENV] = "1"
    os.execve(str(runtime), [str(runtime), script] + list(argv), environment)
