#!/usr/bin/env python3
"""Regression tests for the auditor-defect fixes found during the Apollo Button audit
(apollo-button-audit-report.html, node 37:931, audited 2026-09-04).

Each scenario below is a mistake a real audit run made before these rules existed:
treating a component-scoped absence as proof a token doesn't exist globally, inferring
Light/Dark behavior from a variable's name, treating an unknown alias target as
"not aliased", turning a sampled pattern into a universal claim, and having no way to
mark a verified, deliberate design-system divergence as anything but a plain defect.

No external dependencies — stdlib unittest only, so this runs anywhere Python 3 runs:

    python3 -m unittest discover -s tests -v
    # or directly:
    python3 tests/test_regression.py
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(HERE, '..', 'scripts')
sys.path.insert(0, SCRIPTS)

import consolidate  # noqa: E402
from _scoring import score  # noqa: E402

SRC = 'https://ui.shadcn.com/docs/theming#theme-tokens'


def base_finding(**overrides):
    """A minimally valid Finding object — every REQUIRED field present — so each test
    only has to override the field(s) it's actually exercising."""
    f = dict(
        id='tokens-001', category='pairing', dimension='pairing', severity='medium',
        node_id='1:1', layer_path='Button / variant=default', element='some property',
        current_value='x', expected_value='y', source=SRC, evidence='variables.json › some field',
        fix='do the fix', effort='S', confidence='verified',
    )
    f.update(overrides)
    return f


def validate(findings, checks=None):
    """Run the finding(s) through consolidate.py's validator and return the error list."""
    errors = []
    data = {'agent': 'tokens', 'checks': checks or [], 'findings': findings}
    consolidate.validate_file('fake/tokens.json', data, errors)
    return errors


class AbsenceIsNotEvidenceOfAbsence(unittest.TestCase):
    """Task scenario 1 — component scope ≠ global missing."""

    def test_absence_claim_without_global_scope_is_rejected(self):
        f = base_finding(category='pairing', current_value='none',
                         element='primary-disabled — missing foreground pair')
        errors = validate([f])
        self.assertTrue(any('absence claim' in e for e in errors), errors)
        self.assertTrue(any('evidence_scope' in e for e in errors), errors)

    def test_absence_claim_with_component_scope_is_still_rejected(self):
        f = base_finding(category='pairing', current_value='none',
                         element='primary-disabled — missing foreground pair',
                         evidence_scope='component')
        errors = validate([f])
        self.assertTrue(any('absence claim' in e for e in errors), errors)

    def test_absence_claim_with_global_scope_is_accepted(self):
        f = base_finding(category='pairing', current_value='none',
                         element='primary-disabled — missing foreground pair',
                         evidence_scope='global')
        errors = validate([f])
        self.assertEqual(errors, [])

    def test_component_property_enumeration_is_not_an_absence_claim(self):
        """A component's own variant/size values are fully visible from its own metadata —
        "missing size=xs on Button" is not the same scope-ambiguous claim as a missing
        design token, so it must not require evidence_scope."""
        f = base_finding(category='size', dimension='state_variant',
                         element='size property — missing icon-sm, icon-lg values',
                         current_value='default, sm, lg, icon')
        errors = validate([f])
        self.assertEqual(errors, [])

    def test_bad_evidence_scope_value_is_rejected(self):
        f = base_finding(category='architecture', current_value='present',
                         element='some non-absence property', evidence_scope='everywhere')
        errors = validate([f])
        self.assertTrue(any('bad evidence_scope' in e for e in errors), errors)


class BindingErrorNotMissing(unittest.TestCase):
    """Task scenario 2 — the token exists globally, but the component binds the wrong one.

    This is not an absence claim at all (evidence_scope: not_applicable is fine), so it isn't
    gated by the same rule as scenario 1 — but the fix text and property classification must
    read as a rebind, not a creation, and consolidate.py's dedupe keyed by (node, property
    class) must land it under the specific property (e.g. "label"), not a generic bucket,
    or it merges into an unrelated finding on the same node.
    """

    def test_binding_defect_validates_as_a_rebind_not_a_creation(self):
        f = base_finding(
            category='architecture', dimension='architecture',
            element='label text colour — bound to base/foreground instead of the existing role token',
            current_value='base/foreground (#0a0a0a light / #fafafa dark)',
            expected_value='base/secondary-foreground (#2d1966, exists in both modes)',
            fix='Rebind Secondary label/icon/Kbd text to base/secondary-foreground. Do not create a new token.',
            evidence='ground_truth.md: secondary-foreground row (both modes present); nodes/37-931.json: label bound to base/foreground',
            evidence_scope='not_applicable',
        )
        errors = validate([f])
        self.assertEqual(errors, [])
        self.assertIn('Rebind', f['fix'])
        self.assertNotIn('Create', f['fix'])

    def test_binding_defect_dedupes_under_its_own_property_not_a_generic_bucket(self):
        rebind = base_finding(
            id='components-011', element='label text colour — bound to base/foreground instead of secondary-foreground',
            node_id='37:932', agent='components',
        )
        unrelated = base_finding(
            id='components-099', element='border colour — bound to base/primary instead of base/border', node_id='37:932',
            agent='components',
        )
        merged, conflicts = consolidate.dedupe([rebind, unrelated])
        # Two different properties (label vs stroke/border) on the same node must stay separate.
        self.assertEqual(len(merged), 2)
        self.assertEqual(conflicts, [])


class ModeVerification(unittest.TestCase):
    """Task scenario 3 — mode verification from actual cell values, not names."""

    def test_mode_finding_missing_mode_evidence_is_rejected(self):
        f = base_finding(category='mode', dimension='mode', current_value='dark:destructive',
                         element='naming suggests a dark-mode role')
        errors = validate([f])
        self.assertTrue(any('mode_evidence' in e for e in errors), errors)

    def test_mode_finding_with_name_inference_is_rejected(self):
        f = base_finding(category='mode', dimension='mode', current_value='dark:destructive',
                         element='naming suggests a dark-mode role', mode_evidence='name_inference')
        errors = validate([f])
        self.assertTrue(any('name_inference is not allowed' in e for e in errors), errors)

    def test_render_claim_under_a_different_category_is_still_caught(self):
        """The real Apollo Button audit's governance-006 finding used this exact "will render
        Light in Dark" framing, but filed it as category=governance, not category=mode — a
        category-only gate would have missed it. The check must trigger on the claim itself."""
        f = base_finding(
            category='governance', dimension='governance',
            element='layers bound to custom/* variables whose Dark treatment is written into '
                    'the variable name instead of a Dark mode value — will render Light in Dark',
            current_value='Bound variables: custom/background dark:input\\30 ...',
            evidence='Inferred: a name that spells out the dark class is the pattern used when a '
                     'variable has no Dark mode; mode data itself is not in the snapshot.',
        )
        errors = validate([f])
        self.assertTrue(any('mode-rendering claim' in e for e in errors), errors)

    def test_mode_finding_with_cell_values_is_accepted(self):
        f = base_finding(category='mode', dimension='mode', current_value='violet/200 / violet/200',
                         element='accent-hover identical in Light and Dark',
                         evidence='ground_truth.md: accent-hover row', mode_evidence='cell_values')
        errors = validate([f])
        self.assertEqual(errors, [])


class AliasUncertainty(unittest.TestCase):
    """Task scenario 4 — alias target unknown ≠ not aliased."""

    def test_alias_finding_missing_alias_status_is_rejected(self):
        f = base_finding(category='alias', current_value='#F5F5F5 (resolved)',
                         element='alias target unknown')
        errors = validate([f])
        self.assertTrue(any('alias_status' in e for e in errors), errors)

    def test_not_aliased_from_flat_resolved_value_is_rejected(self):
        f = base_finding(category='alias', current_value='#F5F5F5 (resolved)',
                         element='secondary-hover appears unaliased', alias_status='not_aliased_verified',
                         evidence='variables.json › secondary-hover resolved value')
        errors = validate([f])
        self.assertTrue(any('not_aliased_verified needs evidence' in e for e in errors), errors)

    def test_aliased_target_unknown_is_accepted_without_a_special_source(self):
        f = base_finding(category='alias', current_value='#F5F5F5 (resolved)',
                         element='alias target unknown — get_variable_defs exposes only the resolved hex',
                         alias_status='aliased_target_unknown', confidence='unverified')
        errors = validate([f])
        self.assertEqual(errors, [])

    def test_not_aliased_verified_with_alias_exposing_source_is_accepted(self):
        f = base_finding(category='alias', current_value='#F5F5F5 (raw, confirmed)',
                         element='secondary-hover confirmed unaliased', alias_status='not_aliased_verified',
                         evidence='ground_truth.md: secondary-hover row shows a raw literal, no alias chip')
        errors = validate([f])
        self.assertEqual(errors, [])


class SampledVariants(unittest.TestCase):
    """Task scenario 5 — a sample is not a census."""

    def test_inferred_confidence_without_sample_scope_is_rejected(self):
        f = base_finding(confidence='inferred', element='all Link sizes follow the default pattern')
        errors = validate([f])
        self.assertTrue(any('sample_scope' in e for e in errors), errors)

    def test_inferred_confidence_with_sample_scope_is_accepted(self):
        f = base_finding(confidence='inferred', sample_scope='sampled',
                         element='Link non-default sizes pattern-inferred from the default size',
                         evidence='nodes/60-244.json › only size=default individually sampled; xs/sm/lg extrapolated')
        errors = validate([f])
        self.assertEqual(errors, [])

    def test_critical_that_is_inferred_is_demoted_like_unverified(self):
        """A critical claim that is merely inferred from a sample must not ship as critical —
        only a directly-observed instance earns that severity."""
        f = base_finding(severity='critical', confidence='inferred', sample_scope='sampled',
                         element='contrast fails on every sampled Destructive+Kbd composition')
        needs = consolidate.demote_unconfirmed_criticals([f])
        self.assertEqual(f['severity'], 'high')
        self.assertEqual(f['demoted_from'], 'critical')
        self.assertIn(f['id'], needs)

    def test_critical_that_is_verified_is_not_demoted(self):
        f = base_finding(severity='critical', confidence='verified')
        needs = consolidate.demote_unconfirmed_criticals([f])
        self.assertEqual(f['severity'], 'critical')
        self.assertNotIn(f['id'], needs)

    def test_universal_variant_claim_without_sample_scope_is_rejected(self):
        """The real Apollo Button audit's states-009 finding said "on all 264 variants" while
        only 24 were ever individually inspected, and shipped with confidence=verified because
        nothing forced the universal-quantifier language to declare its sample."""
        f = base_finding(element='State values Focus/Pressed used on every one of the 264 Button variants',
                         current_value='Focus, Pressed (Title Case) on all 264 variants')
        errors = validate([f])
        self.assertTrue(any('every instance of an axis' in e for e in errors), errors)

    def test_universal_variant_claim_sampled_but_verified_is_rejected(self):
        f = base_finding(element='every variant uses the same size scale', sample_scope='sampled',
                         confidence='verified')
        errors = validate([f])
        self.assertTrue(any('contradicts confidence=verified' in e for e in errors), errors)

    def test_universal_variant_claim_declared_exhaustive_is_accepted(self):
        f = base_finding(element='every variant in the 6-variant set uses the same focus ring',
                         sample_scope='exhaustive', confidence='verified')
        errors = validate([f])
        self.assertEqual(errors, [])

    def test_universal_variant_claim_declared_sampled_and_inferred_is_accepted(self):
        f = base_finding(element='every one of the 24 sampled variants uses Title Case state names',
                         current_value='all 264 variants presumed to follow the same pattern',
                         sample_scope='sampled', confidence='inferred')
        errors = validate([f])
        self.assertEqual(errors, [])


class IntentionalDivergence(unittest.TestCase):
    """Task scenario 6 — a documented/accepted divergence from shadcn is not a failure."""

    def test_score_excludes_accepted_divergence_checks(self):
        checks = [
            {'dimension': 'architecture', 'passed': True, 'finding_id': None},
            {'dimension': 'architecture', 'passed': False, 'finding_id': 'components-019'},
            {'dimension': 'architecture', 'passed': False, 'finding_id': 'components-999'},
        ]
        raw = score(checks, mode='component')
        adjusted = score(checks, mode='component', exclude_finding_ids={'components-019'})
        # Raw: 1/3 passed. Adjusted: components-019's failing check is excluded → 1/2 passed.
        self.assertEqual(raw['compliance_pct'], round(100 * 1 / 3))
        self.assertEqual(adjusted['compliance_pct'], round(100 * 1 / 2))
        self.assertGreater(adjusted['compliance_pct'], raw['compliance_pct'])
        # The check the reviewer did NOT accept still counts against the adjusted score.
        self.assertEqual(adjusted['by_dimension']['architecture']['total'], 2)

    def test_off_spec_scope_and_accepted_divergence_compose(self):
        """Both exclusion mechanisms can apply at once without double-counting or interfering."""
        checks = [
            {'dimension': 'contrast', 'passed': True, 'finding_id': None},
            {'dimension': 'contrast', 'passed': False, 'finding_id': 'contrast-001'},
            {'dimension': 'contrast', 'passed': False, 'finding_id': 'contrast-002', 'off_spec_scope': True},
        ]
        adjusted = score(checks, mode='component', exclude_finding_ids={'contrast-001'})
        # off_spec_scope always excluded; contrast-001 additionally excluded → only the passing
        # check remains.
        self.assertEqual(adjusted['by_dimension']['contrast']['total'], 1)
        self.assertEqual(adjusted['compliance_pct'], 100)

    def test_render_report_adjusted_scores_reads_review_accepted_divergences(self):
        sys.path.insert(0, SCRIPTS)
        import render_report  # noqa: E402 (imported lazily: has heavier deps at module scope)
        merged = {
            'meta': {'mode': 'component'},
            'scores': {'compliance_pct': 50, 'health_score': None},
            'checks': [
                {'dimension': 'architecture', 'passed': True, 'finding_id': None},
                {'dimension': 'architecture', 'passed': False, 'finding_id': 'components-019'},
            ],
        }
        review_with = {'accepted_divergences': [{'finding_ids': ['components-019'], 'rationale': 'r', 'evidence': 'e'}]}
        review_without = {}
        adj = render_report.adjusted_scores(merged, review_with)
        self.assertIsNotNone(adj)
        self.assertEqual(adj['excluded_finding_ids'], ['components-019'])
        self.assertEqual(adj['scores']['compliance_pct'], 100)
        self.assertIsNone(render_report.adjusted_scores(merged, review_without))


if __name__ == '__main__':
    unittest.main()
