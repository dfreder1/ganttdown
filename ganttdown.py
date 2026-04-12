#!/usr/bin/env python3
"""ganttdown — read a TSM file and render a text-based Gantt chart."""

import re
import sys
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Optional

OUTPUT_FILE = "schedule.txt"


@dataclass
class Task:
    number: str
    name: str
    duration: int
    start_date: Optional[date] = None
    dependencies: list = field(default_factory=list)
    computed_start: Optional[date] = None
    computed_end: Optional[date] = None


# ── date helpers ──────────────────────────────────────────────────────────────

def is_workday(d: date) -> bool:
    return d.weekday() < 5


def next_workday(d: date) -> date:
    d += timedelta(days=1)
    while not is_workday(d):
        d += timedelta(days=1)
    return d


def add_workdays(start: date, n: int) -> date:
    cur = start
    for _ in range(n - 1):
        cur = next_workday(cur)
    return cur


def workdays_in_range(start: date, end: date) -> list:
    days, cur = [], start
    while cur <= end:
        if is_workday(cur):
            days.append(cur)
        cur += timedelta(days=1)
    return days


def week_monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


# ── TSM parser ────────────────────────────────────────────────────────────────

def parse_task(line: str, tasks: dict) -> Task:
    line = line.strip()
    m = re.match(r'^@task:\s+(\S+)\s*(.*)', line)
    if not m:
        raise ValueError("line must start with '@task: <number>' then fields")

    num  = m.group(1)
    rest = m.group(2)

    text   = ' ' + rest
    kw_re  = re.compile(r'\s(name|start|dur|dep):\s*')
    hits   = list(kw_re.finditer(text))

    if not hits:
        raise ValueError(f"@task: {num}: no recognised fields found (expected name:/start:/dur:/dep:)")

    flds: dict = {}
    for i, h in enumerate(hits):
        key = h.group(1)
        vs  = h.end()
        ve  = hits[i + 1].start() if i + 1 < len(hits) else len(text)
        flds[key] = text[vs:ve].strip()

    if 'name' not in flds:
        raise ValueError(f"@task: {num}: task name (name:) is required")
    name = flds['name']
    if not name:
        raise ValueError(f"@task: {num}: task name cannot be empty")

    if 'dur' not in flds:
        raise ValueError(f"@task: {num}: duration (dur:) is required")
    try:
        duration = int(flds['dur'])
        if duration < 1:
            raise ValueError()
    except ValueError:
        raise ValueError(f"@task: {num}: dur: must be a positive integer, got '{flds['dur']}'")

    start_date: Optional[date] = None
    if 'start' in flds:
        try:
            start_date = datetime.strptime(flds['start'], '%m/%d/%Y').date()
        except ValueError:
            raise ValueError(f"@task: {num}: invalid date '{flds['start']}' — use MM/DD/YYYY")
        if not is_workday(start_date):
            raise ValueError(f"@task: {num}: start date {flds['start']} falls on a weekend")

    deps: list = []
    if 'dep' in flds:
        for d in (x.strip() for x in flds['dep'].split(',') if x.strip()):
            if d not in tasks:
                raise ValueError(
                    f"@task: {num}: dependency '{d}' not found — define dependencies before dependents")
            deps.append(d)

    if start_date is None and not deps:
        raise ValueError(f"@task: {num}: must provide a start date (start:) or at least one dependency (dep:)")

    if num in tasks:
        raise ValueError(f"@task: {num}: task number already exists")

    return Task(number=num, name=name, duration=duration,
                start_date=start_date, dependencies=deps)


# ── schedule computation ──────────────────────────────────────────────────────

def compute(tasks: dict) -> None:
    done:   set = set()
    active: set = set()

    def resolve(n: str) -> None:
        if n in done:
            return
        if n in active:
            raise ValueError(f"circular dependency detected involving #{n}")
        active.add(n)
        t = tasks[n]
        for dep in t.dependencies:
            resolve(dep)
        if t.dependencies:
            latest = max(tasks[d].computed_end for d in t.dependencies)
            t.computed_start = next_workday(latest)
        else:
            t.computed_start = t.start_date
        t.computed_end = add_workdays(t.computed_start, t.duration)
        active.discard(n)
        done.add(n)

    for n in list(tasks):
        resolve(n)


# ── Gantt renderer ────────────────────────────────────────────────────────────

def _sort_key(num: str) -> list:
    parts = []
    for p in num.split('.'):
        try:
            parts.append((0, int(p), ''))
        except ValueError:
            parts.append((1, 0, p))
    return parts


def render(tasks: dict) -> str:
    if not tasks:
        return "(no tasks)\n"

    ordered = sorted(tasks.values(), key=lambda t: _sort_key(t.number))

    chart_start = min(t.computed_start for t in ordered)
    chart_end   = max(t.computed_end   for t in ordered)
    wdays       = workdays_in_range(chart_start, chart_end)
    n_days      = len(wdays)

    weeks: list = []
    seen:  set  = set()
    for d in wdays:
        mon = week_monday(d)
        if mon not in seen:
            seen.add(mon)
            weeks.append(mon)

    num_w  = max(max(len(t.number) for t in ordered), 4)
    name_w = 20
    dur_w  = max(5, len('Dur'))
    dep_w  = max(5, len('Dep'), max(
        len(','.join(t.dependencies)) if t.dependencies else 3
        for t in ordered))

    PFX = num_w + 2 + name_w + 2 + dur_w + 2 + dep_w + 2
    DW  = 2

    pos_map: dict = {}
    col = 0
    for i, d in enumerate(wdays):
        pos_map[d] = col
        col += DW
        if d.weekday() == 4 or i == n_days - 1:
            col += 1
    gantt_w = col
    total_w = PFX + gantt_w

    lines: list = []

    hdr = [' '] * total_w
    col_labels = ('#'.ljust(num_w) + '  '
                  + 'Task Name'.ljust(name_w) + '  '
                  + 'Dur'.ljust(dur_w) + '  '
                  + 'Dep'.ljust(dep_w) + '  ')
    for j, ch in enumerate(col_labels):
        hdr[j] = ch
    for mon in weeks:
        first = next((d for d in wdays if week_monday(d) == mon), None)
        if first is None:
            continue
        pos   = PFX + pos_map[first]
        label = mon.strftime('%m/%d/%Y')
        for j, ch in enumerate(label):
            if pos + j < total_w:
                hdr[pos + j] = ch
        week_days = [d for d in wdays if week_monday(d) == mon]
        colon_pos = PFX + pos_map[week_days[-1]] + DW
        if colon_pos < total_w:
            hdr[colon_pos] = ':'
    lines.append(''.join(hdr))

    DOW = {0: 'M', 1: 'T', 2: 'W', 3: 'T', 4: 'F'}
    dow_parts = []
    for i, d in enumerate(wdays):
        dow_parts.append(DOW[d.weekday()] + ' ')
        if d.weekday() == 4 or i == n_days - 1:
            dow_parts.append(':')
    lines.append(' ' * PFX + ''.join(dow_parts))

    sep_parts = []
    for i, d in enumerate(wdays):
        sep_parts.append('--')
        if d.weekday() == 4 or i == n_days - 1:
            sep_parts.append(':')
    lines.append(' ' * PFX + ''.join(sep_parts))

    prev_group = None
    for t in ordered:
        grp = t.number.split('.')[0]
        if prev_group is not None and grp != prev_group:
            lines.append('')
        prev_group = grp

        dep_str = ','.join(t.dependencies) if t.dependencies else 'n/a'
        bar_parts = []
        for i, d in enumerate(wdays):
            bar_parts.append('# ' if t.computed_start <= d <= t.computed_end else '  ')
            if d.weekday() == 4 or i == n_days - 1:
                bar_parts.append(':')
        bar = ''.join(bar_parts)

        row = (t.number.ljust(num_w)          + '  '
               + t.name[:name_w].ljust(name_w) + '  '
               + str(t.duration).ljust(dur_w)  + '  '
               + dep_str.ljust(dep_w)          + '  '
               + bar)
        lines.append(row)

    return '\n'.join(lines) + '\n'


# ── file parser ───────────────────────────────────────────────────────────────

def load_file(path: str) -> dict:
    """Read a ganttdown file and return a dict of parsed Tasks."""
    try:
        with open(path) as f:
            raw_lines = f.readlines()
    except FileNotFoundError:
        print(f"Error: file not found: {path}", file=sys.stderr)
        sys.exit(1)
    except OSError as e:
        print(f"Error reading {path}: {e}", file=sys.stderr)
        sys.exit(1)

    tasks: dict = {}
    errors: list = []

    for lineno, raw in enumerate(raw_lines, 1):
        line = raw.strip()
        if not line or line.startswith('//') or line.startswith('--'):
            continue   # blank lines and comment lines are ignored
        if not line.startswith('@task:'):
            errors.append(f"  line {lineno}: skipped (does not start with '@task'): {line!r}")
            continue
        try:
            task = parse_task(line, tasks)
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

USAGE = "usage: ganttdown.py <schedule-file>"


def main() -> None:
    if len(sys.argv) != 2:
        print(USAGE)
        sys.exit(1)

    path = sys.argv[1]
    tasks = load_file(path)

    if not tasks:
        print("No tasks found in file.")
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
