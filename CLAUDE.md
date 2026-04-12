# txtsched / ganttdown

A text-based Gantt chart tool using TSM (Text Schedule Markup) syntax.
Two modes: interactive (`txtsched.py`) and file-based (`ganttdown.py`).

## Language
Python 3, no external libraries.

## Key concepts
- Working days only (Mon-Fri, no weekends)
- Task numbers use dotted hierarchy (1.1, 1.2, 2.1)
- Output is monospaced text to screen and schedule.txt

## TSM syntax
Each task is one line. All fields use `keyword: value` format:

  @task: <num>  name: <name>  start: <MM/DD/YYYY>  dur: <days>  dep: <dep1,dep2>

- `@task:` — line marker and task number (dotted hierarchy)
- `name:` — task name (required)
- `start:` — start date MM/DD/YYYY (required unless dep: is given)
- `dur:` — duration in working days (required)
- `dep:` — comma-separated dependencies (optional)

Example:
@task: 1.0  name: Buy Nails    start: 06/18/2026  dur: 5
@task: 1.1  name: Buy Wood     start: 06/25/2026  dur: 5
@task: 1.2  name: Hammer       dur: 5             dep: 1.1

## File format (ganttdown)
- One @task: line per task
- Blank lines and lines starting with // or -- are ignored
- Dependencies must be defined before the tasks that reference them

## Conventions
- Keep all output monospaced
- Clear error messages on bad input, with line numbers in file mode
