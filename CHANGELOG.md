# Changelog

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
