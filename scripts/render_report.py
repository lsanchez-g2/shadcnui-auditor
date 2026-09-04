#!/usr/bin/env python3
"""Render merged.json + review.json into a self-contained report.html.

Usage: render_report.py <audit dir> [--out report.html]
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, '..', 'assets', 'report_template.html')


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    audit = os.path.abspath(sys.argv[1])
    out = os.path.join(audit, 'report.html')
    if '--out' in sys.argv:
        out = sys.argv[sys.argv.index('--out') + 1]

    merged_path = os.path.join(audit, 'merged.json')
    if not os.path.exists(merged_path):
        print('merged.json missing — run consolidate.py first', file=sys.stderr)
        sys.exit(2)
    with open(merged_path, encoding='utf-8') as f:
        merged = json.load(f)
    review = {}
    review_path = os.path.join(audit, 'review.json')
    if os.path.exists(review_path):
        with open(review_path, encoding='utf-8') as f:
            review = json.load(f)
    else:
        print('warning: review.json missing — report will have no verdict/fix order', file=sys.stderr)

    meta = merged.get('meta', {})
    name = meta.get('file_name') or 'Figma'
    title = f"{name} Audit"

    data = json.dumps({'merged': merged, 'review': review}, ensure_ascii=False)
    # Keep the JSON safe inside a <script> block.
    data = data.replace('</', '<\\/')

    with open(TEMPLATE, encoding='utf-8') as f:
        html = f.read()
    def attr(s):
        return str(s).replace('&', '&amp;').replace('"', '&quot;').replace('<', '&lt;')

    flavor = meta.get('flavor', 'unknown')
    docs = meta.get('docs_fetched', [])
    html = (html.replace('__TITLE__', title.replace('<', '&lt;'))
                .replace('__FLAVOR__', attr(flavor))
                .replace('__DOCS__', attr(' '.join(docs)))
                .replace('__VERDICT__', attr(review.get('verdict', 'n/a')))
                .replace('__DATA__', data))
    with open(out, 'w', encoding='utf-8') as f:
        f.write(html)

    c = merged.get('counts', {})
    print(f"wrote {out}  ({os.path.getsize(out)//1024} KB) — {c.get('findings_merged')} findings, "
          f"{c.get('checks')} checks, verdict: {review.get('verdict', 'n/a')}")
    print(f"header: flavor={flavor}  docs={len(docs)} url(s)")
    for u in docs:
        print(f"  - {u}")
    if not docs:
        print("  WARNING: meta.docs_fetched is empty — the header will not name the spec pages", file=sys.stderr)
    if review.get('verdict', '').startswith('BLOCKED') and not review.get('unblock_cost'):
        print("  WARNING: verdict is BLOCKED but review.json has no unblock_cost", file=sys.stderr)


if __name__ == '__main__':
    main()
