"""Shared, deterministic scoring — used by consolidate.py (the raw, review-blind
score) and render_report.py (the reviewer-informed adjusted score). One
implementation so the two numbers can never drift apart by accident.
"""
DIMENSIONS = {'pairing', 'contrast', 'mode', 'architecture', 'state_variant', 'governance'}
WEIGHTS = {'pairing': 20, 'contrast': 25, 'mode': 20, 'architecture': 20, 'state_variant': 15}


def score(checks, mode, exclude_finding_ids=frozenset()):
    """Checks flagged off_spec_scope are excluded: a defect on a variant shadcn does not define
    is reported, but must not move a number that claims to measure parity with shadcn.

    `exclude_finding_ids` additionally excludes checks whose finding_id is in the set — used to
    compute the accepted-divergence-adjusted score in render_report.py. Passing nothing
    reproduces the raw, review-blind score consolidate.py writes to merged.json.
    """
    checks = [c for c in checks
              if not c.get('off_spec_scope') and c.get('finding_id') not in exclude_finding_ids]
    per_dim = {}
    for d in DIMENSIONS:
        rows = [c for c in checks if c['dimension'] == d]
        total = len(rows)
        passed = sum(1 for c in rows if c['passed'])
        per_dim[d] = {'passed': passed, 'total': total, 'rate': (passed / total) if total else None}
    weighted, weight_used = 0.0, 0
    for d, w in WEIGHTS.items():
        r = per_dim[d]['rate']
        if r is not None:
            weighted += w * r
            weight_used += w
    health = round(100 * weighted / weight_used) if weight_used else None
    all_scored = [c for c in checks]
    compliance = round(100 * sum(1 for c in all_scored if c['passed']) / len(all_scored)) if all_scored else None
    return {'health_score': health if mode == 'system' else None,
            'compliance_pct': compliance,
            'weights': WEIGHTS, 'weight_used': weight_used, 'by_dimension': per_dim}
