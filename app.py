#!/usr/bin/env python3
"""Flask web interface for ganttdown."""

from flask import Flask, render_template, request, Response
from ganttdown import parse_task, compute, render

app = Flask(__name__)


def process_input(text: str) -> tuple[str, str]:
    """Parse TSM input, return (chart, error). One will be empty."""
    tasks: dict = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith('//') or line.startswith('--'):
            continue
        if not line.startswith('@task:'):
            return '', f'Error: line must start with @task: — got: {line!r}'
        try:
            task = parse_task(line, tasks)
            tasks[task.number] = task
            compute(tasks)
        except ValueError as e:
            return '', f'Error: {e}'
    if not tasks:
        return '', 'No tasks found in input.'
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
