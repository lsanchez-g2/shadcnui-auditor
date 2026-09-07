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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _scoring import DIMENSIONS, WEIGHTS, score as _score  # noqa: E402

EXPECTED_AGENTS = ['tokens', 'variables', 'modes', 'contrast', 'states', 'components', 'styles', 'governance']
CATEGORIES = {'baseline', 'pairing', 'semantic', 'radius', 'architecture', 'alias', 'orphan', 'scope', 'mode',
              'contrast', 'state', 'variant', 'naming', 'size', 'layout', 'typography', 'anatomy', 'props', 'a11y',
              'style', 'governance'}
SEVERITIES = ['low', 'medium', 'high', 'critical']
EFFORTS = {'S', 'M', 'L'}
REQUIRED = ['id', 'category', 'dimension', 'severity', 'layer_path', 'element', 'expected_value', 'source',
            'evidence', 'fix', 'effort', 'confidence']
CONFIDENCES = {'verified', 'inferred', 'unverified'}
EVIDENCE_SCOPES = {'component', 'global', 'not_applicable'}
ALIAS_STATUSES = {'aliased_verified', 'aliased_target_unknown', 'not_aliased_verified', 'unknown'}
MODE_EVIDENCE = {'cell_values', 'name_inference', 'not_applicable'}
SAMPLE_SCOPES = {'exhaustive', 'sampled'}
# Categories where "missing" means "this token/variable may not exist anywhere in the library" —
# a claim a component-scoped snapshot cannot settle on its own. Component-property categories
# (variant/size/state/naming/anatomy/props/a11y) are excluded: a component's own variant-property
# values are fully enumerable from that one component's metadata, so "missing size=xs on Button"
# is not a scope-ambiguous claim the way "missing token X" is.
TOKEN_EXISTENCE_CATEGORIES = {'baseline', 'pairing', 'semantic', 'radius'}
# "current_value"/"element" phrasing that asserts something is missing/absent. A finding using
# this language is a claim about the whole library and needs global evidence — see
# references/findings-schema.md "Absence is not evidence of absence".
ABSENCE_LANGUAGE = re.compile(r'\b(missing|absent|does not exist|doesn\'t exist|not found|no such|nonexistent)\b',
                              re.IGNORECASE)
# Sources that expose alias *targets* (vs get_variable_defs/variables.json, which is a flat
# name→resolved-value map with no alias chain — see references/extraction.md).
ALIAS_EXPOSING_SOURCES = re.compile(r'\b(use_figma|ground_truth\.md)\b', re.IGNORECASE)
# A claim about what a token actually renders as in Light/Dark. A real audit filed this exact
# mistake under category="governance" (not "mode"), describing "custom/*" variables it presumed
# had no Dark value from their names alone — so this check runs on every finding's text
# regardless of category or agent, not only ones already labeled category=mode.
MODE_RENDER_CLAIM = re.compile(
    r'\brenders? .{0,20}(light|dark) in (light|dark)\b|\bwill render .{0,20}(light|dark)\b',
    re.IGNORECASE)


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
        confidence = fnd.get('confidence')
        if confidence not in CONFIDENCES:
            errors.append(f'{loc}: bad confidence {confidence!r} (must be one of {sorted(CONFIDENCES)})')
        if confidence == 'inferred' and fnd.get('sample_scope') not in SAMPLE_SCOPES:
            errors.append(f'{loc}: confidence=inferred requires sample_scope in {sorted(SAMPLE_SCOPES)} '
                          f'(what was sampled vs extrapolated)')
        if not str(fnd.get('source', '')).startswith('https://ui.shadcn.com/'):
            errors.append(f'{loc}: source must be a ui.shadcn.com URL')
        for k in ('current_score', 'final_score'):
            v = fnd.get(k)
            if v is not None and not (isinstance(v, int) and 1 <= v <= 10):
                errors.append(f'{loc}: {k} must be int 1-10')

        # Absence is not evidence of absence: a finding phrased as a missing/absent *token* claim
        # needs global evidence_scope, or it must be reported as unverified instead of a finding.
        # Scoped to token-existence categories — see TOKEN_EXISTENCE_CATEGORIES above.
        text = f"{fnd.get('current_value', '')} {fnd.get('element', '')}"
        evidence_scope = fnd.get('evidence_scope')
        if fnd.get('category') in TOKEN_EXISTENCE_CATEGORIES and ABSENCE_LANGUAGE.search(text):
            if evidence_scope != 'global':
                errors.append(
                    f'{loc}: reads as an absence claim ("{text.strip()}") but evidence_scope='
                    f'{evidence_scope!r}, not "global". A component-scoped check that finds no '
                    f'token cannot prove the token does not exist in the library — move this to '
                    f'"unverified" (with evidence_scope: component) instead of "findings", or '
                    f'pull the global variable inventory / search_design_system / ground_truth.md '
                    f'first. See findings-schema.md "Absence is not evidence of absence".')
        elif evidence_scope is not None and evidence_scope not in EVIDENCE_SCOPES:
            errors.append(f'{loc}: bad evidence_scope {evidence_scope!r}')

        # Alias claims: get_variable_defs/variables.json exposes no alias target, so a finding
        # asserting "not aliased" from that source alone is unverifiable — it must say "unknown".
        if fnd.get('category') == 'alias':
            alias_status = fnd.get('alias_status')
            if alias_status not in ALIAS_STATUSES:
                errors.append(f'{loc}: category=alias requires alias_status in {sorted(ALIAS_STATUSES)}, '
                              f'got {alias_status!r}')
            elif alias_status == 'not_aliased_verified' and not ALIAS_EXPOSING_SOURCES.search(fnd.get('evidence', '')):
                errors.append(
                    f'{loc}: alias_status=not_aliased_verified needs evidence citing an '
                    f'alias-exposing source (use_figma / ground_truth.md) — get_variable_defs/'
                    f'variables.json alone cannot prove a variable is unaliased. Use '
                    f'alias_status=aliased_target_unknown instead, or cite the exposing source.')

        # Mode claims: a variable's name (a "dark:" fragment, etc.) is never evidence about its
        # actual Dark cell. This must be resolved from real per-mode values or left unverified.
        # Triggered by category=mode OR by the claim language itself — a real audit filed this
        # exact mistake ("will render Light in Dark") under category=governance, describing
        # custom/* variables it presumed had no Dark value from their names alone.
        mode_text = f"{fnd.get('element', '')} {fnd.get('current_value', '')} {fnd.get('expected_value', '')}"
        if fnd.get('category') == 'mode' or MODE_RENDER_CLAIM.search(mode_text):
            mode_evidence = fnd.get('mode_evidence')
            if mode_evidence not in MODE_EVIDENCE:
                errors.append(f'{loc}: this is a mode-rendering claim (category=mode, or the '
                              f'text reads as one) and requires mode_evidence in {sorted(MODE_EVIDENCE)}, '
                              f'got {mode_evidence!r}')
            elif mode_evidence == 'name_inference':
                errors.append(
                    f'{loc}: mode_evidence=name_inference is not allowed on a finding — a variable '
                    f'name is not evidence about its actual Dark/Light cell value. Move this to '
                    f'"unverified" instead, or resolve it from ground_truth.md / a mode-aware pull.')
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


def demote_unconfirmed_criticals(findings):
    """A critical claim the specialist could not directly verify for this exact instance — whether
    inferred from a sample or outright unverified — is demoted; only a directly-observed critical
    ships as critical. Both cases are listed under "needs verification" so the report is explicit
    about which criticals are pinned down and which still need a look."""
    needs = []
    for f in findings:
        if f['severity'] == 'critical' and f.get('confidence') != 'verified':
            f['severity'] = 'high'
            f['demoted_from'] = 'critical'
            needs.append(f['id'])
    return needs


# Backward-compatible alias for anything importing the old name.
demote_unverified_criticals = demote_unconfirmed_criticals


def score(checks, mode):
    return _score(checks, mode)


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
    needs_verification = demote_unconfirmed_criticals(merged)
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
