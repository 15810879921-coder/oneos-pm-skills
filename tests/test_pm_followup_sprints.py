"""Include the installed skill's regression tests in the repository suite."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def load_tests(loader, tests, pattern):
    root = Path(__file__).resolve().parents[1]
    path = root / "skills/YunxiaoPM/tests/test_followup_sprints.py"
    names = ("accept_release", "yunxiao_cli_pm", "yunxiao_cli_runtime")
    saved_modules = {name: sys.modules.pop(name) for name in names if name in sys.modules}
    saved_path = sys.path[:]
    try:
        spec = importlib.util.spec_from_file_location("pm_followup_skill_tests", path)
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(module)
        return loader.loadTestsFromModule(module)
    finally:
        for name in names:
            sys.modules.pop(name, None)
        sys.modules.update(saved_modules)
        sys.path[:] = saved_path
