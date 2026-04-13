# ganttdown

A text-based Gantt chart tool. Reads a .gd file containing a <task> block
and renders a monospaced Gantt chart. Also available as a web app.

## Language
Python 3, no external libraries except Flask for the web app.

## Key concepts
- Working days only (Mon-Fri, no weekends)
- Task numbers use dotted hierarchy (1.1, 1.2, 2.1)
- Output is monospaced text to screen and schedule.txt
- schedule.txt is wrapped in triple backticks for Teams pasting

## Syntax
Tasks live inside a <task> ... </task> block. Each task is one positional line:

  <task#>  <name>  <YYYY-MM-DD or dep#>  <duration>

  Field 1 — task number (dotted hierarchy)
  Field 2 — task name (everything between field 1 and field 3)
  Field 3 — start date (YYYY-MM-DD) or dependency task number
  Field 4 — duration in working days

Example:
<task>
1.0  Project Kickoff  2026-04-13  1
1.1  Requirements     2026-04-13  5
1.2  Design           1.1         5
2.1  Development      1.2         10
</task>

Comments start with //. Blank lines are ignored.
Everything outside the <task> block is ignored.

## Files
- ganttdown.py   — CLI tool and core logic (parser, compute, render)
- app.py         — Flask web app, imports from ganttdown.py
- templates/     — Jinja2 HTML templates
- sample.gd      — sample schedule file

## Conventions
- Keep all output monospaced
- Clear error messages on bad input with line numbers
- Dates are ISO 8601 (YYYY-MM-DD) only
