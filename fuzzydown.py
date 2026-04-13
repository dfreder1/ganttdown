#!/usr/bin/env python3
"""fuzzydown — positional TSM parser with <task> block syntax."""

import re
import sys
from datetime import date, datetime

from ganttdown import (Task, compute, render,
                       is_workday, next_workday, add_workdays)

OUTPUT_FILE = "schedule.txt"

# Patterns for positional field detection
RE_TASK_NUM = re.compile(r'^\d+(\.\d+)*$')
RE_DATE     = re.compile(r'^\d{4}-\d{2}-\d{2}$')
RE_DURATION = re.compile(r'^\d+$')


# ── positional parser ─────────────────────────────────────────────────────────

def parse_line(line: str, tasks: dict) -> Task:
    """Parse one positional fuzzydown line.

    Fixed order:  <task#>  <name...>  <2026-MM-DD or dep#>  <duration>

    Examples:
      3.1  Build foundation  2026-03-25  5
      3.2  Cure foundation   3.1         7
    """
    tokens = line.split()
    if len(tokens) < 4:
        raise ValueError(
            f"too few fields — expected: <task#> <name...> <date|dep> <duration>")

    # Position 1: task number
    num = tokens[0]
    if not RE_TASK_NUM.match(num):
        raise ValueError(f"'{num}' is not a valid task number (e.g. 1  1.1  2.3)")

    if num in tasks:
        raise ValueError(f"{num}: task number already exists")

    # Position 4 (last token): duration
    dur_token = tokens[-1]
    if not RE_DURATION.match(dur_token):
        raise ValueError(
            f"{num}: last field must be duration in days, got '{dur_token}'")
    duration = int(dur_token)
    if duration < 1:
        raise ValueError(f"{num}: duration must be at least 1")

    # Position 3 (second to last): date or dependency
    anchor_token = tokens[-2]
    start_date = None
    deps = []

    if RE_DATE.match(anchor_token):
        try:
            start_date = datetime.strptime(anchor_token, '%Y-%m-%d').date()
        except ValueError:
            raise ValueError(
                f"{num}: invalid date '{anchor_token}' — use YYYY-MM-DD")
        if not is_workday(start_date):
            raise ValueError(
                f"{num}: start date {anchor_token} falls on a weekend")
    elif RE_TASK_NUM.match(anchor_token):
        if anchor_token not in tasks:
            raise ValueError(
                f"{num}: dependency '{anchor_token}' not found "
                f"— define dependencies before dependents")
        deps = [anchor_token]
    else:
        raise ValueError(
            f"{num}: expected a date (YYYY-MM-DD) or task number, "
            f"got '{anchor_token}'")

    # Position 2: everything between task number and anchor — the name
    name = ' '.join(tokens[1:-2]).strip()
    if not name:
        raise ValueError(f"{num}: task name cannot be empty")

    return Task(number=num, name=name, duration=duration,
                start_date=start_date, dependencies=deps)


# ── file loader ───────────────────────────────────────────────────────────────

def load_file(path: str) -> dict:
    """Read a fuzzydown file, extract the <task> block, parse all lines."""
    try:
        with open(path) as f:
            content = f.read()
    except FileNotFoundError:
        print(f"Error: file not found: {path}", file=sys.stderr)
        sys.exit(1)
    except OSError as e:
        print(f"Error reading {path}: {e}", file=sys.stderr)
        sys.exit(1)

    # Extract <task> block
    m = re.search(r'<task>(.*?)</task>', content, re.DOTALL | re.IGNORECASE)
    if not m:
        print("Error: no <task> ... </task> block found in file.", file=sys.stderr)
        sys.exit(1)

    block = m.group(1)
    tasks: dict = {}
    errors: list = []

    for lineno, raw in enumerate(block.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith('//'):
            continue
        try:
            task = parse_line(line, tasks)
            tasks[task.number] = task
        except ValueError as e:
            errors.append(f"  line {lineno}: {e}")

    if errors:
        print("Parse errors:", file=sys.stderr)
        for e in errors:
            print(e, file=sys.stderr)
        sys.exit(1)

    return tasks


# ── entry point ───────────────────────────────────────────────────────────────

USAGE = "usage: fuzzydown.py <schedule-file>"


def main() -> None:
    if len(sys.argv) != 2:
        print(USAGE)
        sys.exit(1)

    path = sys.argv[1]
    tasks = load_file(path)

    if not tasks:
        print("No tasks found in <task> block.")
        sys.exit(0)

    try:
        compute(tasks)
    except ValueError as e:
        print(f"Schedule error: {e}", file=sys.stderr)
        sys.exit(1)

    chart = render(tasks)

    sep = '═' * 72
    print(sep)
    print("GANTT CHART")
    print(sep)
    print(chart)

    with open(OUTPUT_FILE, 'w') as f:
        f.write('```\n' + chart + '```\n')
    print(f"Saved to: {OUTPUT_FILE}")


if __name__ == '__main__':
    main()
