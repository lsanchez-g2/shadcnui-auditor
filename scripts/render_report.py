#!/usr/bin/env python3
"""Render merged.json + review.json into a self-contained report.html.

Usage: render_report.py <audit dir> [--out report.html]
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _scoring import score as _score  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, '..', 'assets', 'report_template.html')


def adjusted_scores(merged, review):
    """The raw score in merged.json is computed before the reviewer runs, so it cannot yet
    exclude findings the reviewer later accepts as intentional design-system divergences
    (see agents/reviewer.md and findings-schema.md "Divergence vs defect"). This recomputes
    the same deterministic formula with those checks additionally excluded — never a second,
    independently-eyeballed number. Returns None when there is nothing to adjust, so the
    report can tell "not applicable" apart from "adjustment made no difference".
    """
    divergences = review.get('accepted_divergences') or []
    excluded_ids = {fid for d in divergences for fid in d.get('finding_ids', [])}
    if not excluded_ids:
        return None
    meta = merged.get('meta', {})
    mode = meta.get('mode', 'system')
    checks = merged.get('checks', [])
    raw = merged.get('scores', {})
    adjusted = _score(checks, mode, exclude_finding_ids=excluded_ids)
    excluded_count = sum(1 for c in checks if c.get('finding_id') in excluded_ids and not c.get('off_spec_scope'))
    return {'scores': adjusted, 'excluded_finding_ids': sorted(excluded_ids), 'checks_excluded': excluded_count,
            'raw_compliance_pct': raw.get('compliance_pct'), 'raw_health_score': raw.get('health_score')}


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

    adjusted = adjusted_scores(merged, review)
    data = json.dumps({'merged': merged, 'review': review, 'adjusted': adjusted}, ensure_ascii=False)
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
    if adjusted:
        raw_pct = adjusted['raw_compliance_pct']
        adj_pct = adjusted['scores']['compliance_pct']
        print(f"accepted divergences: {adjusted['checks_excluded']} checks excluded — "
              f"compliance {raw_pct}% raw / {adj_pct}% adjusted "
              f"(finding ids: {', '.join(adjusted['excluded_finding_ids'])})")
    print(f"header: flavor={flavor}  docs={len(docs)} url(s)")
    for u in docs:
        print(f"  - {u}")
    if not docs:
        print("  WARNING: meta.docs_fetched is empty — the header will not name the spec pages", file=sys.stderr)
    if review.get('verdict', '').startswith('BLOCKED') and not review.get('unblock_cost'):
        print("  WARNING: verdict is BLOCKED but review.json has no unblock_cost", file=sys.stderr)


if __name__ == '__main__':
    main()
