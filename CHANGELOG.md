# Changelog

## 0.4.0 — 2026-09-07

Evidence and confidence discipline, from the Apollo Button audit remediation (`apollo-button-audit-report.html`, node 37:931). Every item below is a mistake that audit made — some already had prose warnings against them (0.2.0), but nothing enforced them, so they still happened. All five are now schema-validated by `consolidate.py`, not just written guidance.

- **Absence is not evidence of absence.** New `evidence_scope` field (`component`/`global`/`not_applicable`). A finding phrased as a missing/absent *token* claim (tokens/variables categories only — a component's own variant/size values are excluded, they're fully enumerable from that component's own metadata) must carry `evidence_scope: global`, or `consolidate.py` rejects it — the check belongs in `unverified[]`, not `findings[]`, until a global source (a full variable pull, `search_design_system`, or `ground_truth.md`) settles it.
- **Mode claims need real cell values.** New `mode_evidence` field (`cell_values`/`name_inference`/`not_applicable`), required on every `category: mode` finding. `name_inference` is rejected outright — the 0.2.0 prose rule ("forbidden wording") is now a hard schema gate.
- **Alias claims need an alias-exposing source.** New `alias_status` field (`aliased_verified`/`aliased_target_unknown`/`not_aliased_verified`/`unknown`), required on every `category: alias` finding. `not_aliased_verified` is rejected unless `evidence` cites `use_figma` or `ground_truth.md` — `get_variable_defs`/`variables.json` alone is a flat resolved-value map with no alias chain and cannot support that claim.
- **A sample is not a census.** `confidence` is now three-state (`verified`/`inferred`/`unverified`, was two-state); `inferred` requires a new `sample_scope` (`exhaustive`/`sampled`) field naming what was actually inspected. A `critical` finding that is `inferred` (not just `unverified`) is demoted to `high`, same as before.
- **shadcn is a reference baseline, not the file's absolute truth.** New reviewer-only `divergence_status`/`review.json.accepted_divergences`: a real, verified, system-wide deviation from an axis shadcn *does* define (unlike `off_spec_scope`, for axes it doesn't define at all) can be accepted as a deliberate design-system decision rather than a defect, under strict criteria (agents/reviewer.md). `render_report.py` computes and shows both the raw and the accepted-divergence-adjusted compliance number — never a silent score change — via a new shared `scripts/_scoring.py` module (`consolidate.py`'s raw score and `render_report.py`'s adjusted score now share one implementation). `report_template.html` gains an "Accepted divergences" section.
- Added `tests/test_regression.py` (stdlib `unittest`, no dependencies): 21 tests, one per failure mode above plus the binding-error-vs-creation distinction, wired into `scripts/selftest.sh`.

## 0.3.0 — 2026-09-04

Report redesign and repository packaging.

- New report template: sticky section rail with gliding indicator, animated score ring and KPI counters, severity distribution, per-dimension progress bars, fix-order timeline, spring-expanding findings with copy-to-clipboard fixes, sortable tables with sticky headers, colour-pair swatches in the contrast matrix, light/dark with three-state theme handling, print stylesheet, `prefers-reduced-motion`.
- Typeface: Geist / Geist Mono (the faces shadcn's own docs use).
- Fixed: nav labels all reading "Overview"; animations frozen in hosted iframes (now timer-driven with final-value fallback); responsive rule declared before its base rule so the rail overlaid content below 960 px.
- Added `scripts/make_fixture.py` and `scripts/selftest.sh`; `.gitignore` excludes audit workspaces.

## 0.2.0 — 2026-09-04

Lessons from seven real audits (six components + one system-level run).

- `use_figma` read-only script documented as the primary source for collections, modes, alias chains, scopes, and component property definitions; screenshots → `ground_truth.md` as fallback.
- `get_metadata` without node-id truncates the page list — verification step added.
- Whole-set `get_design_context` avoided above ~20 variants; axis-based sampling recipe.
- Shared spec cache; registry JSON (`/r/styles/<style>/<name>.json`) as the source of `cva` class strings; handling for docs pages with no API table.
- System-mode rules per agent (no per-layer checks emitted without `nodes/`).
- `off_spec_scope` flag excludes findings on off-spec variants from the score.
- Dedupe by node + property class (stroke colour vs width, naming vs icon, governance sub-classes).
- Reviewer adds `unblock_cost` when BLOCKED; gaps split into rerun vs needs-data.
- Modes agent forbidden from inferring Dark-cell state from a variable's name.
- Baseline reference updated to base-nova values; decorative-border contrast exemption documented.

## 0.1.0 — 2026-09-04

Initial skill: orchestrator, eight specialists, reviewer, consolidator with weighted scoring, WCAG contrast script, HTML renderer.
