#!/usr/bin/env python3
"""txtsched — command-line Gantt chart scheduler (TSM format)"""

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
    return d.weekday() < 5  # Mon=0 … Fri=4


def next_workday(d: date) -> date:
    """First working day strictly after d."""
    d += timedelta(days=1)
    while not is_workday(d):
        d += timedelta(days=1)
    return d


def add_workdays(start: date, n: int) -> date:
    """Date that is n working days from start (start counts as day 1)."""
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
    """Parse one TSM line into a Task.

    Format:
        @task: <num> name: <name> start: <MM/DD/YYYY> dur: <days> dep: <dep1,dep2,...>
    Fields name: and dur: are required; start: and dep: are optional but at
    least one of start: or dep: must be present.
    """
    line = line.strip()
    m = re.match(r'^@task:\s+(\S+)\s*(.*)', line)
    if not m:
        raise ValueError("line must start with '@task: <number>' then fields")

    num  = m.group(1)
    rest = m.group(2)

    # Prepend a space so a keyword at position 0 is also caught
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

    # ── required: name ──
    if 'name' not in flds:
        raise ValueError(f"@task: {num}: task name (name:) is required")
    name = flds['name']
    if not name:
        raise ValueError(f"@task: {num}: task name cannot be empty")

    # ── required: dur ──
    if 'dur' not in flds:
        raise ValueError(f"@task: {num}: duration (dur:) is required")
    try:
        duration = int(flds['dur'])
        if duration < 1:
            raise ValueError()
    except ValueError:
        raise ValueError(f"@task: {num}: dur: must be a positive integer, got '{flds['dur']}'")

    # ── optional: start ──
    start_date: Optional[date] = None
    if 'start' in flds:
        try:
            start_date = datetime.strptime(flds['start'], '%m/%d/%Y').date()
        except ValueError:
            raise ValueError(
                f"@task: {num}: invalid date '{flds['start']}' — use MM/DD/YYYY")
        if not is_workday(start_date):
            raise ValueError(
                f"@task: {num}: start date {flds['start']} falls on a weekend")

    # ── optional: dep ──
    deps: list = []
    if 'dep' in flds:
        for d in (x.strip() for x in flds['dep'].split(',') if x.strip()):
            if d not in tasks:
                raise ValueError(
                    f"@task: {num}: dependency '{d}' not found — enter dependencies first")
            deps.append(d)

    if start_date is None and not deps:
        raise ValueError(
            f"@task: {num}: must provide a start date (start:) or at least one dependency (dep:)")

    if num in tasks:
        raise ValueError(f"@task: {num}: task number already exists")

    return Task(number=num, name=name, duration=duration,
                start_date=start_date, dependencies=deps)


# ── schedule computation ──────────────────────────────────────────────────────

def compute(tasks: dict) -> None:
    """Resolve computed_start / computed_end for every task (topological order)."""
    done:   set = set()
    active: set = set()   # cycle detection

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
            # td takes priority over ts when both are supplied
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
    """'1.2.10' → [(0,1,''), (0,2,''), (0,10,'')] for natural numeric sort."""
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

    # unique weeks ordered by Monday date
    weeks: list = []
    seen:  set  = set()
    for d in wdays:
        mon = week_monday(d)
        if mon not in seen:
            seen.add(mon)
            weeks.append(mon)

    # ── column widths ──
    num_w  = max(max(len(t.number) for t in ordered), 4)
    name_w = 20
    dur_w  = max(5, len('Dur'))
    dep_w  = max(5, len('Dep'), max(
        len(','.join(t.dependencies)) if t.dependencies else 3
        for t in ordered))

    # prefix  =  num  2sp  name  2sp  dur  2sp  dep  2sp
    PFX = num_w + 2 + name_w + 2 + dur_w + 2 + dep_w + 2

    # Each working day occupies 2 chars; a colon follows each week's last day
    DW = 2

    # Build gantt position map accounting for week-separator colons
    pos_map: dict = {}
    col = 0
    for i, d in enumerate(wdays):
        pos_map[d] = col
        col += DW
        if d.weekday() == 4 or i == n_days - 1:   # Friday or last day
            col += 1                                # colon
    gantt_w = col
    total_w = PFX + gantt_w

    lines: list = []

    # ── header: column labels + week-start Monday dates with colon separators ──
    hdr = [' '] * total_w
    # column label section
    col_labels = ('#'.ljust(num_w) + '  '
                  + 'Task Name'.ljust(name_w) + '  '
                  + 'Dur'.ljust(dur_w) + '  '
                  + 'Dep'.ljust(dep_w) + '  ')
    for j, ch in enumerate(col_labels):
        hdr[j] = ch
    # gantt date labels and colons
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

    # ── sub-header: day-of-week letters with week colons ──
    DOW = {0: 'M', 1: 'T', 2: 'W', 3: 'T', 4: 'F'}
    dow_parts = []
    for i, d in enumerate(wdays):
        dow_parts.append(DOW[d.weekday()] + ' ')
        if d.weekday() == 4 or i == n_days - 1:
            dow_parts.append(':')
    lines.append(' ' * PFX + ''.join(dow_parts))

    # ── separator with week colons ──
    sep_parts = []
    for i, d in enumerate(wdays):
        sep_parts.append('--')
        if d.weekday() == 4 or i == n_days - 1:
            sep_parts.append(':')
    lines.append(' ' * PFX + ''.join(sep_parts))

    # ── task rows ──
    prev_group = None
    for t in ordered:
        grp = t.number.split('.')[0]
        if prev_group is not None and grp != prev_group:
            lines.append('')         # blank line between groups
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


# ── interactive loop ──────────────────────────────────────────────────────────

BANNER = """\
txtsched — Text-based Gantt Chart Scheduler
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Format : @task: <num> name: <name> start: <MM/DD/YYYY> dur: <days> dep: <dep1,dep2,...>
Commands: done · list · help
"""

HELP = """\
TSM Format
─────────────────────────────────────────────────────────────
  @task: <num>   task identifier   e.g.  1   1.1   2.3   (dotted)
  name:         task name         (required)
  start:        start date        MM/DD/YYYY  (required unless dep: given)
  dur:          duration          working days Mon–Fri  (required)
  dep:          dependencies      comma-separated task numbers  (optional)

Rules
  • Weekends are skipped in both duration and column display.
  • A dependent task starts the next working day after ALL deps finish.
  • When both start: and dep: are given, dep: takes priority (start
    computed from deps; start: is ignored).
  • Task numbers sharing the same prefix (e.g. 1.x) are grouped with
    a blank line separating each top-level group.

Examples
  @task: 1    name: Project Kickoff  start: 03/02/2026  dur: 1
  @task: 1.1  name: Requirements     start: 03/02/2026  dur: 5
  @task: 1.2  name: Design           dur: 5             dep: 1.1
  @task: 2.1  name: Development      dur: 10            dep: 1.2
  @task: 2.2  name: Testing          dur: 5             dep: 2.1
─────────────────────────────────────────────────────────────
"""


def _save_and_echo(tasks: dict) -> None:
    chart = render(tasks)
    with open(OUTPUT_FILE, 'w') as f:
        f.write('```\n' + chart + '```\n')


def main() -> None:
    tasks: dict = {}
    print(BANNER)

    while True:
        try:
            raw = input("task> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not raw:
            continue

        low = raw.lower()

        if low == 'done':
            break

        if low == 'help':
            print(HELP)
            continue

        if low == 'list':
            if not tasks:
                print("  (no tasks yet)\n")
            else:
                for n, t in sorted(tasks.items(),
                                   key=lambda x: _sort_key(x[0])):
                    dep_s = ','.join(t.dependencies) or 'n/a'
                    print(f"  @task: {n:<10s}  {t.name[:20]:<20s}  "
                          f"{t.duration}d  dep:{dep_s}  "
                          f"{t.computed_start:%m/%d/%Y} → "
                          f"{t.computed_end:%m/%d/%Y}")
                print()
            continue

        if not raw.startswith('@task:'):
            print("  Error: tasks must start with '@task'  (type 'help' for format)\n")
            continue

        try:
            task = parse_task(raw, tasks)
            tasks[task.number] = task
            compute(tasks)
            _save_and_echo(tasks)

            print(f"  + @task: {task.number}  {task.name}")
            print(f"    {task.computed_start:%m/%d/%Y} → {task.computed_end:%m/%d/%Y}"
                  f"  ({task.duration} working day{'s' if task.duration != 1 else ''})\n")

        except ValueError as e:
            print(f"  Error: {e}\n")

    # ── final output ──
    if tasks:
        compute(tasks)
        _save_and_echo(tasks)
        chart = render(tasks)
        sep = '═' * min(72, 40 + len(tasks) * 2)
        print(f"\n{sep}")
        print("FINAL SCHEDULE")
        print(sep)
        print(chart)
        print(f"Saved to: {OUTPUT_FILE}")
    else:
        print("No tasks scheduled.")


if __name__ == '__main__':
    main()
