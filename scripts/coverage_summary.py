"""Print a per-file coverage summary and append a markdown block
to GITHUB_STEP_SUMMARY so the CI run surfaces a structured report.
Compatible with coverage.py 5.x through 7.x.
"""
import json
import os
import sys


def _percent(item):
    return item.get('percent_covered_display') or f"{item.get('percent_covered', 0):.0f}"


def main():
    path = 'artifacts/coverage.json'
    out_md = 'artifacts/coverage-summary.txt'
    if not os.path.exists(path):
        print('no coverage')
        return
    with open(path) as f:
        d = json.load(f)
    t = d['totals']
    lines = [
        f"TOTAL  {_percent(t)}%  "
        f"({t['covered_lines']}/{t['num_statements']} lines)"
    ]

    def _pct_key(item):
        return item.get('summary', {}).get('percent_covered', 0)

    files = list(d['files'].items())
    for path_key, payload in sorted(files, key=lambda x: _pct_key(x[1])):
        s = payload.get('summary', {})
        if s.get('num_statements', 0) == 0:
            continue
        lines.append(f"  {_percent(s):>5}%  {path_key}")
    text = '\n'.join(lines)
    print(text)
    with open(out_md, 'w') as f:
        f.write(text + '\n')
    summary = os.environ.get('GITHUB_STEP_SUMMARY')
    if summary:
        with open(summary, 'a') as f:
            f.write('\n```\n' + text + '\n```\n')


if __name__ == '__main__':
    sys.exit(main() or 0)
