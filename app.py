#!/usr/bin/env python3
"""Flask web interface for ganttdown."""

import re
from flask import Flask, render_template, request, Response
from ganttdown import parse_line, compute, render

app = Flask(__name__)


def process_input(text: str) -> tuple[str, str]:
    """Extract <task> block from input, parse and render. Returns (chart, error)."""
    m = re.search(r'<task>(.*?)</task>', text, re.DOTALL | re.IGNORECASE)
    if not m:
        return '', 'No <task> ... </task> block found in input.'

    tasks: dict = {}
    errors: list = []

    for lineno, raw in enumerate(m.group(1).splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith('//'):
            continue
        try:
            task = parse_line(line, tasks)
            tasks[task.number] = task
            compute(tasks)
        except ValueError as e:
            errors.append(f"line {lineno}: {e}")

    if errors:
        return '', '\n'.join(errors)

    if not tasks:
        return '', 'No tasks found in <task> block.'

    return render(tasks), ''


@app.route('/', methods=['GET', 'POST'])
def index():
    chart = ''
    error = ''
    tsm_input = ''
    if request.method == 'POST':
        tsm_input = request.form.get('tsm', '')
        chart, error = process_input(tsm_input)
    return render_template('index.html', chart=chart, error=error, tsm_input=tsm_input)


@app.route('/download', methods=['POST'])
def download():
    tsm_input = request.form.get('tsm', '')
    chart, error = process_input(tsm_input)
    if error:
        return error, 400
    return Response(
        '```\n' + chart + '```\n',
        mimetype='text/plain',
        headers={'Content-Disposition': 'attachment; filename=schedule.txt'}
    )


if __name__ == '__main__':
    app.run(debug=True)
