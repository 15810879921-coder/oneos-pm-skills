#!/usr/bin/env python3
"""Compute YunxiaoPMapp stage calendar hours = workdays × 8.

Usage:
  python3 workday_hours.py YYYY-MM-DD YYYY-MM-DD
  python3 workday_hours.py YYYY-MM-DD YYYY-MM-DD --calendar /path/to/cn-workday-calendar.json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path


def parse_day(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def load_calendar(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    years = data.get("years") or {}
    holidays: set[str] = set()
    makeup: set[str] = set()
    for _y, block in years.items():
        holidays.update(block.get("holidays") or [])
        makeup.update(block.get("workdays_on_weekend") or [])
    return {"holidays": holidays, "makeup": makeup, "years": set(years.keys())}


def ensure_years_covered(start: date, end: date, years: set[str]) -> None:
    y = start.year
    while y <= end.year:
        if str(y) not in years:
            raise SystemExit(
                f"缺少 {y} 年日历：请在 assets/cn-workday-calendar.json 补全后再计算。"
                "禁止仅去周末静默估算。"
            )
        y += 1


def is_workday(d: date, holidays: set[str], makeup: set[str]) -> bool:
    key = d.isoformat()
    if key in holidays:
        return False
    if key in makeup:
        return True
    return d.weekday() < 5  # Mon=0 .. Fri=4


def count_workdays(start: date, end: date, holidays: set[str], makeup: set[str]) -> int:
    if end < start:
        raise SystemExit("结束日早于开始日")
    n = 0
    cur = start
    while cur <= end:
        if is_workday(cur, holidays, makeup):
            n += 1
        cur += timedelta(days=1)
    return n


def main() -> None:
    parser = argparse.ArgumentParser(description="阶段日历工时 = 工作日×8")
    parser.add_argument("start", help="计划开始 YYYY-MM-DD")
    parser.add_argument("end", help="计划完成 YYYY-MM-DD")
    parser.add_argument(
        "--calendar",
        default=str(Path(__file__).resolve().parent.parent / "assets" / "cn-workday-calendar.json"),
        help="日历 JSON 路径",
    )
    args = parser.parse_args()
    start = parse_day(args.start)
    end = parse_day(args.end)
    cal = load_calendar(Path(args.calendar))
    ensure_years_covered(start, end, cal["years"])
    days = count_workdays(start, end, cal["holidays"], cal["makeup"])
    hours = days * 8
    out = {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "workdays": days,
        "stage_calendar_hours": hours,
        "label": "阶段日历工时（工作日×8），非人力投入预估",
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
