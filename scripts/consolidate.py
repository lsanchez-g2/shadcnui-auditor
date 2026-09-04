#!/usr/bin/env python3
"""Validate, merge, dedupe and score specialist findings.

Usage: consolidate.py <audit dir> [--strict]

Reads  <audit dir>/findings/*.json and <audit dir>/snapshot/meta.json
Writes <audit dir>/merged.json
Exit 0 on success, 2 on schema violations (details on stderr).
"""
import glob
import json
import os
import re
import sys
from collections import defaultdict

EXPECTED_AGENTS = ['tokens', 'variables', 'modes', 'contrast', 'states', 'components', 'styles', 'governance']
CATEGORIES = {'baseline', 'pairing', 'semantic', 'radius', 'architecture', 'alias', 'orphan', 'scope', 'mode',
              'contrast', 'state', 'variant', 'naming', 'size', 'layout', 'typography', 'anatomy', 'props', 'a11y',
              'style', 'governance'}
DIMENSIONS = {'pairing', 'contrast', 'mode', 'architecture', 'state_variant', 'governance'}
WEIGHTS = {'pairing': 20, 'contrast': 25, 'mode': 20, 'architecture': 20, 'state_variant': 15}
SEVERITIES = ['low', 'medium', 'high', 'critical']
EFFORTS = {'S', 'M', 'L'}
REQUIRED = ['id', 'category', 'dimension', 'severity', 'layer_path', 'element', 'expected_value', 'source',
            'evidence', 'fix', 'effort', 'confidence']


def load(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def validate_file(agent_file, data, errors):
    name = os.path.basename(agent_file)
    agent = data.get('agent')
    if agent not in EXPECTED_AGENTS:
        errors.append(f'{name}: agent must be one of {EXPECTED_AGENTS}, got {agent!r}')
    for key in ('checks', 'findings'):
        if not isinstance(data.get(key), list):
            errors.append(f'{name}: "{key}" must be a list')
    ids = set()
    for i, fnd in enumerate(data.get('findings', [])):
        loc = f'{name} findings[{i}]'
        for req in REQUIRED:
            if not str(fnd.get(req, '')).strip():
                errors.append(f'{loc}: missing "{req}"')
        fid = fnd.get('id')
        if fid in ids:
            errors.append(f'{loc}: duplicate id {fid}')
        ids.add(fid)
        if fnd.get('category') not in CATEGORIES:
            errors.append(f'{loc}: bad category {fnd.get("category")!r}')
        if fnd.get('dimension') not in DIMENSIONS:
            errors.append(f'{loc}: bad dimension {fnd.get("dimension")!r}')
        if fnd.get('severity') not in SEVERITIES:
            errors.append(f'{loc}: bad severity {fnd.get("severity")!r}')
        if fnd.get('effort') not in EFFORTS:
            errors.append(f'{loc}: bad effort {fnd.get("effort")!r}')
        if fnd.get('confidence') not in ('verified', 'unverified'):
            errors.append(f'{loc}: bad confidence {fnd.get("confidence")!r}')
        if not str(fnd.get('source', '')).startswith('https://ui.shadcn.com/'):
            errors.append(f'{loc}: source must be a ui.shadcn.com URL')
        for k in ('current_score', 'final_score'):
            v = fnd.get(k)
            if v is not None and not (isinstance(v, int) and 1 <= v <= 10):
                errors.append(f'{loc}: {k} must be int 1-10')
    for i, chk in enumerate(data.get('checks', [])):
        loc = f'{name} checks[{i}]'
        if chk.get('dimension') not in DIMENSIONS:
            errors.append(f'{loc}: bad dimension {chk.get("dimension")!r}')
        if not isinstance(chk.get('passed'), bool):
            errors.append(f'{loc}: "passed" must be boolean')
        fid = chk.get('finding_id')
        if fid and fid not in ids:
            errors.append(f'{loc}: finding_id {fid} not in findings')


def norm(s):
    return re.sub(r'[^a-z0-9]+', ' ', (s or '').lower()).strip()


# Ordered: first match wins. Two agents describing the same property on the same node use different
# words ("focus ring effect color" vs "focus ring — not derived from ring"), so we key on the property,
# not the sentence. Order matters: "focus ring" must beat "fill"; "label" must beat "fill".
PROPERTY_KEYS = [
    # Structural/naming classes first: "icon slot naming" is a naming issue, not an icon-colour issue.
    ('naming', r'\b(naming|casing|property names?|value names?|layer name|slot name|named|rename)\b'),
    ('anatomy', r'\b(anatomy|slot structure|sub-?component|nesting)\b'),
    ('doc-link', r'\b(doc anchor|doc link|documentation link|docs? url|un-?prefixed url|flavor not stated)\b'),
    ('description', r'\b(description|documentation)\b'),
    ('publish', r'\b(publish|unpublished|library status)\b'),
    ('hidden-layers', r'\bhidden layers?\b'),
    ('state-values', r'\b(state (property|value)|aria-|loading|disabled value)\b'),
    ('size-values', r'\bsize (property|value)s?\b'),
    # Visual properties. Colour and dimension of the same primitive are different fixes.
    ('ring', r'\b(ring|focus (ring|effect|border|state)|outline (ring|effect))\b'),
    ('label', r'\b(label|text style|type size|typography|font|leading|weight)\b'),
    ('stroke-width', r'\b(stroke|border)[- ]?(width|weight|thickness)\b|\b\d(\.\d)?px (stroke|border)\b'),
    ('stroke', r'\b(stroke|border)\b'),
    ('radius', r'\b(radius|corner|rounded)\b'),
    ('fill', r'\b(fill|background|bg)\b'),
    ('height', r'\bheight\b'),
    ('width', r'\b(width|box size)\b'),
    ('padding', r'\b(padding|inset|spacing)\b'),
    ('gap', r'\bgap\b'),
    ('icon', r'\bicon\b'),
    ('opacity', r'\bopacity\b'),
    ('effect', r'\b(shadow|effect|blur)\b'),
]


def property_key(element):
    e = (element or '').lower()
    for key, pat in PROPERTY_KEYS:
        if re.search(pat, e):
            return key
    return norm(element)


def dedupe(findings):
    """Merge findings that target the same property on the same node/layer."""
    buckets = defaultdict(list)
    for f in findings:
        key = (f.get('node_id') or norm(f.get('layer_path')), property_key(f.get('element')))
        buckets[key].append(f)
    merged, conflicts = [], []
    for key, group in buckets.items():
        group.sort(key=lambda f: SEVERITIES.index(f['severity']), reverse=True)
        head = dict(group[0])
        head['agents'] = sorted({g['agent'] for g in group})
        head['merged_ids'] = [g['id'] for g in group]
        head['evidence_all'] = [f"[{g['agent']}] {g['evidence']}" for g in group]
        expecteds = {norm(g.get('expected_value')) for g in group}
        if len(expecteds) > 1:
            conflicts.append({'element': head['element'], 'layer_path': head['layer_path'],
                              'finding_ids': head['merged_ids'],
                              'expected_values': [f"[{g['agent']}] {g['expected_value']}" for g in group]})
        merged.append(head)
    return merged, conflicts


def demote_unverified_criticals(findings):
    needs = []
    for f in findings:
        if f['severity'] == 'critical' and f.get('confidence') == 'unverified':
            f['severity'] = 'high'
            f['demoted_from'] = 'critical'
            needs.append(f['id'])
    return needs


def score(checks, mode):
    """Checks flagged off_spec_scope are excluded: a defect on a variant shadcn does not define
    is reported, but must not move a number that claims to measure parity with shadcn."""
    checks = [c for c in checks if not c.get('off_spec_scope')]
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


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    audit = os.path.abspath(sys.argv[1])
    strict = '--strict' in sys.argv
    meta_path = os.path.join(audit, 'snapshot', 'meta.json')
    meta = load(meta_path) if os.path.exists(meta_path) else {}
    mode = meta.get('mode', 'system')

    files = sorted(glob.glob(os.path.join(audit, 'findings', '*.json')))
    if not files:
        print('no findings files', file=sys.stderr)
        sys.exit(2)

    errors, agents, all_findings, all_checks = [], {}, [], []
    tables, compliant, off_spec, unverified, notes = {}, [], [], [], {}
    for path in files:
        try:
            data = load(path)
        except Exception as e:
            errors.append(f'{os.path.basename(path)}: invalid JSON ({e})')
            continue
        validate_file(path, data, errors)
        agent = data.get('agent', os.path.basename(path).replace('.json', ''))
        agents[agent] = {'file': os.path.basename(path), 'checks': len(data.get('checks', [])),
                         'findings': len(data.get('findings', [])), 'unverified': len(data.get('unverified', []))}
        for f in data.get('findings', []):
            f = dict(f)
            f['agent'] = agent
            all_findings.append(f)
        for c in data.get('checks', []):
            c = dict(c)
            c['agent'] = agent
            all_checks.append(c)
        if data.get('tables'):
            tables[agent] = data['tables']
        compliant += [{'agent': agent, 'item': x} for x in data.get('compliant', [])]
        off_spec += [dict(x, agent=agent) for x in data.get('off_spec', [])]
        unverified += [dict(x, agent=agent) for x in data.get('unverified', [])]
        if data.get('notes'):
            notes[agent] = data['notes']

    missing = [a for a in EXPECTED_AGENTS if a not in agents]
    if errors:
        print('\n'.join(errors), file=sys.stderr)
        print(f'\n{len(errors)} schema violation(s). Fix the agent and rerun it.', file=sys.stderr)
        sys.exit(2)
    if missing and strict:
        print(f'missing agents: {missing}', file=sys.stderr)
        sys.exit(2)

    merged, conflicts = dedupe(all_findings)
    needs_verification = demote_unverified_criticals(merged)
    merged.sort(key=lambda f: (-SEVERITIES.index(f['severity']), 'SML'.index(f['effort']), f['id']))
    scores = score(all_checks, mode)
    off_scope_checks = sum(1 for c in all_checks if c.get('off_spec_scope'))
    off_scope_findings = [f['id'] for f in merged if f.get('off_spec_scope')]
    by_sev = {s: sum(1 for f in merged if f['severity'] == s) for s in SEVERITIES}

    out = {
        'meta': meta,
        'scores': scores,
        'counts': {'findings_raw': len(all_findings), 'findings_merged': len(merged), 'checks': len(all_checks),
                   'by_severity': by_sev, 'conflicts': len(conflicts), 'off_spec': len(off_spec),
                   'unverified': len(unverified), 'off_spec_scope_checks_excluded': off_scope_checks,
                   'off_spec_scope_findings': off_scope_findings},
        'findings': merged,
        'conflicts': conflicts,
        'needs_verification': needs_verification,
        'checks': all_checks,
        'tables': tables,
        'compliant': compliant,
        'off_spec': off_spec,
        'unverified': unverified,
        'notes': notes,
        'agents': agents,
        'missing_agents': missing,
    }
    with open(os.path.join(audit, 'merged.json'), 'w', encoding='utf-8') as f:
        json.dump(out, f, indent=2, ensure_ascii=False)

    print(f'agents: {len(agents)}/{len(EXPECTED_AGENTS)}' + (f'  MISSING: {missing}' if missing else ''))
    print(f'checks: {len(all_checks)}   findings: {len(all_findings)} → {len(merged)} after dedupe   conflicts: {len(conflicts)}')
    print(f'severity: {by_sev}')
    if scores['health_score'] is not None:
        print(f'health score: {scores["health_score"]}/100  (weights used: {scores["weight_used"]}/100)')
    print(f'compliance: {scores["compliance_pct"]}%' + (f'  ({off_scope_checks} off-spec-scoped checks excluded)' if off_scope_checks else ''))
    for d, v in scores['by_dimension'].items():
        print(f'  {d:15s} {v["passed"]}/{v["total"]}')
    if needs_verification:
        print(f'needs verification (critical→high): {needs_verification}')
    print(f'wrote {os.path.join(audit, "merged.json")}')


if __name__ == '__main__':
    main()
