"""Print a per-file coverage summary and append a markdown block
to GITHUB_STEP_SUMMARY so the CI run surfaces a structured report.
"""
import json
import os
import sys


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
        f"TOTAL  {t['percent_covered_display']}  "
        f"({t['covered_lines']}/{t['num_statements']} lines)"
    ]
    for f in sorted(d['files'], key=lambda x: x['summary']['percent_covered']):
        s = f['summary']
        if s['num_statements'] == 0:
            continue
        lines.append(f"  {s['percent_covered_display']:>6}  {f['filename']}")
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
