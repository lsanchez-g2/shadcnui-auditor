---
name: shadcn-figma-audit-swarm
description: Multi-agent audit of a Figma design system or component against the live shadcn/ui spec, delivered as a consolidated senior-level HTML report. Use this whenever the user shares a figma.com URL and wants it audited, checked, reviewed, scored, or compared against shadcn/ui — tokens, variables, light/dark modes, contrast, states, variants, component parity, styles, or handoff readiness. Also trigger on phrases like "design system audit", "check parity with shadcn", "is this component ready for handoff", "token audit", "WCAG check on my Figma library", or "Code Connect readiness", even when shadcn is not named but the file clearly follows its conventions.
compatibility: Requires the Figma MCP connector (get_metadata, get_design_context, get_variable_defs, search_design_system, get_screenshot), web fetch for ui.shadcn.com, the Agent tool for subagents, and Python 3 for the bundled scripts.
---

# shadcn/ui Figma Audit Swarm

One orchestrator (you), eight read-only specialists running in parallel, one senior reviewer, and two deterministic scripts. The specialists never touch Figma or the web — they read a snapshot you extracted once. That single decision is what keeps eight agents from producing eight contradictory reports: same inputs, same spec, one shared findings contract.

```
Phase 0  you        route → pick shadcn flavor → fetch docs once → extract Figma once → write snapshot/
Phase 1  8 agents   parallel, each reads snapshot/, writes findings/<agent>.json (shared schema)
Phase 2  script     consolidate.py: validate → merge → dedupe → weighted health score → merged.json
Phase 3  reviewer   reads merged.json, writes review.json (summary, verdict, fix order, conflicts resolved)
Phase 4  script     render_report.py: merged.json + review.json → report.html
```

Rigor rules that apply to every phase, and why:

- **Never audit from memory.** The spec has changed materially (radius scale, Button sizes, Base UI as default). A score against a remembered spec is a wrong score. If a docs page cannot be fetched, stop and say so.
- **Never guess a value you can read.** Every finding carries `evidence` naming the tool output it came from, and `source` naming the docs anchor it was checked against. `consolidate.py` rejects findings missing either.
- **Do not invent, do not remove, do not add.** Anything shadcn does not define goes to `off_spec`, never into the score.
- **Distinguish "missing" from "named differently".** Search the snapshot before flagging absence.
- **Absence is not evidence of absence.** A component-scoped snapshot proves only that this component doesn't reference a token — never that the token doesn't exist in the library. A "missing" claim needs a global source (a full variable pull, `search_design_system`, or `ground_truth.md`); without one, the check is `unverified`, not a finding. See `agents/_common.md`.
- **Verify mode and alias claims from real data, not from a name.** A `dark:`-shaped variable name is not evidence about its Dark cell; a resolved hex from `get_variable_defs` is not evidence a variable is unaliased (that tool exposes no alias chain at all). Both need `ground_truth.md` or a `use_figma` pull to become verified findings; otherwise they're unverified.
- **A sample is not a census.** Claims about variants outside what was actually sampled are `confidence: inferred`, never `verified`, and never phrased as "all N variants".
- **shadcn is a reference baseline, not the file's absolute truth.** A real, consistent, system-wide divergence from shadcn (a size scale, a radius, a weight) is still reported at full severity, but the reviewer — not a specialist — may accept it as a deliberate design-system decision (`review.json.accepted_divergences`) rather than a defect, when the evidence supports it.

## Phase 0 — Orchestrate

### 0.1 Route

Read the URL. Decide and state the mode in your first line:

| Input | Mode |
|---|---|
| No `node-id`, or `node-id` is a page/section holding several component sets | `system` |
| `node-id` is a component set (a `<frame>` whose direct children are `<symbol>` variants), or a page/section that contains exactly one such set | `component` |
| `node-id` is one variant (`<symbol>` named `Prop=Value, …`) | `component`, on its parent set |
| `node-id` is a standalone component (`<symbol>` with a plain name and no set parent — Dialog, Separator often are) | `component`, on the node itself; anatomy and slots are the audit, there is no variant matrix |
| `node-id` is a plain frame, group, or instance with no `<symbol>` children or parent | Stop: "Not a component — nothing to audit." |
| `node-id` is a page/section holding several component sets whose **combined** variant count is small enough to sample in full (roughly ≤ 20 variants total) | `system`, fully sampled — see note below |

Confirm the node type with `get_metadata` before committing; URLs lie about what they point to, and the metadata XML never says "component set" — it says `<frame>` and you read the children.

**`system, fully sampled`** exists for the case a plain `system` route handles badly: a page holding several *related* sets (Avatar + Avatar Badge + Avatar Group, say) where each set alone is small. Plain `system` mode skips `nodes/` entirely (see `agents/_common.md`, "System mode") because it assumes 100+ sets — but with a handful of sets and ≤ 20 total variants, running `get_design_context` per set is cheap and the per-variant detail is exactly what catches cross-set architecture issues (a badge's `strokeAlign`, a group's `itemSpacing`) that naming/variable-level checks can't see. In this variant: run extraction's full per-set `get_design_context` pass as in `component` mode, for every set on the page, and write `nodes/<id>.json` for each. State in your first line that `nodes/` is populated and therefore authoritative — tell agents explicitly (in the per-agent prompt, not left to the "System mode" default) to prefer `nodes/` over system-level inference wherever a node file exists for the set they're scoring.

### 0.2 Pick the shadcn flavor

The docs ship three primitive flavors with different APIs: `base` (Base UI, current default), `radix`, `aria`. The un-prefixed `/docs/components/<name>` URL redirects to `base`. Ask the user which flavor engineering uses if it is not stated or inferable from the file. Record it in `snapshot/meta.json`. Mixing flavors in one audit produces false findings (e.g. `data-state` vs `data-open`).

### 0.3 Fetch the spec once

Fetch and save raw text to `snapshot/spec/`:

- `https://ui.shadcn.com/docs/theming` → `theming.md`
- For each component set in scope: `https://ui.shadcn.com/docs/components/<flavor>/<name>` → `components/<name>.md` (API table, usage notes)
- And its registry item `https://ui.shadcn.com/r/styles/<style>/<name>.json` (`base-nova` for the base flavor) → `components/<name>.registry.json` — this is where the `cva` class strings live; the docs page collapses them.

Then write `snapshot/spec/spec.json` following `references/shadcn-baseline.md`, which also lists what you should expect to find so you can tell if a fetch returned a stub.

### 0.4 Extract Figma once

Follow `references/extraction.md`. The variable structure (collections, modes, alias chains, scopes) comes from a read-only `use_figma` script, not from `get_variable_defs`; the reference has the script. In system mode, extraction stops at metadata plus variables — no per-variant design context — and the agents know how to score at that level (see `agents/_common.md`, "System mode"). It maps each MCP call to a snapshot section and tells you how to normalize output so specialists find the same shape every time. Save raw tool output alongside the normalized files — specialists cite raw output as evidence.

Result: `snapshot/meta.json`, `variables.json`, `styles.json`, `components.json`, `nodes/<id>.json`, `screenshots/`, and — when the user has supplied Variables-panel screenshots — `ground_truth.md` (see the reference; it is the only way the modes and variables agents get collection, mode, and alias data).

Once a library's `ground_truth.md` exists, copy it into every later audit of the same file. It does not change between components.

### 0.5 Fan out

Create `findings/`. Spawn all eight specialists **in one message** with the Agent tool (`subagent_type: general-purpose`). Each prompt is:

```
Read, in order: <skill>/agents/_common.md, <skill>/agents/<name>.md, <skill>/references/findings-schema.md. Follow them exactly.
Audit workspace (file tools): <abs path to audit dir as Read/Write see it>
Audit workspace (bash):       <same dir as mcp__workspace__bash sees it>
Skill scripts (bash):         <skill>/scripts/ as bash sees it
Mode: <system|component>.  shadcn flavor: <base|radix|aria>.
In scope: <set name(s) + node id(s) + variant count, or "N sets, see components.json" in system mode>.
Component API has states: <yes | no | only on <sub-part> — from spec.json>.
Write your output to <audit dir>/findings/<name>.json and nothing else.
Do not call Figma or fetch the web. If the snapshot lacks data you need, emit the check as "unverified" and say what is missing.
Reply with one line: counts of checks, passes, findings, unverified.
```

The two paths matter: in this environment file tools and bash mount the same folder at different roots, and an agent given only one will guess the other. Agents: `tokens`, `variables`, `modes`, `contrast`, `states`, `components`, `styles`, `governance`. In `component` mode they still all run — most simply have fewer checks. For a non-interactive component the states and contrast agents log the size × default matrix and stop (that is what the "has states" line is for).

If an agent fails or returns malformed JSON, rerun that one agent. Do not patch its file by hand — you would be auditing from memory.

## Phase 2 — Consolidate

```bash
python3 <skill>/scripts/consolidate.py <audit dir>
```

Validates every findings file against `references/findings-schema.md`, merges, dedupes by `(node_id|layer_path, property)` — where property is derived from the element text (fill, stroke, ring, label, radius, …) because eight agents describe the same defect in eight sentences — keeping the most severe and recording all agents that flagged it, and computes the health score from the `checks` arrays — pairing 20%, contrast 25%, mode parity 20%, architecture 20%, state/variant 15%. Governance checks are reported but unweighted, matching the source prompt. Output: `merged.json` plus a console summary. A non-zero exit means a schema violation; fix the agent, rerun the agent, rerun the script.

The score is computed by code and never by an agent so that two runs on the same file give the same number.

## Phase 3 — Review

Spawn one agent with `agents/reviewer.md`. It reads `merged.json` and writes `review.json`: executive summary, verdict, top-5, fix order, and resolutions where two specialists disagreed. It may lower a score with a stated reason; it may not add a finding. It may also promote specific findings to `accepted_divergences` — real, verified deviations from shadcn that read as deliberate design-system decisions rather than defects (strict criteria in `agents/reviewer.md`; never for a11y/alias/mode defects, only for on-spec value choices like a size scale or radius). Its `gaps` come in two kinds: those a specialist can close from the existing snapshot (rerun that specialist), and those that need Figma data the snapshot lacks (a nested set's URL, a Dark-mode screenshot). The second kind goes into your final reply as "needs data: …" — do not rerun anything for them.

## Phase 4 — Render

```bash
python3 <skill>/scripts/render_report.py <audit dir>
```

Produces `report.html`: self-contained, light/dark aware, severity filters, copy-ready token names, per-fix effort/benefit, an agent run log, and — when the reviewer accepted any divergences — both the raw and the accepted-divergence-adjusted compliance number, plus a dedicated "Accepted divergences" section (never a silent score change). Open it or publish it as an artifact if the session has that tool. Present the file to the user.

## Verification before you report

You are done only when all of these are true:

- `consolidate.py` exited 0 and reported eight agent files.
- `render_report.py` exited 0. Its console line prints the flavor and the docs URLs it embedded — that is the header check; the page renders client-side so `grep` on the HTML body tells you nothing. The `<meta name="audit-flavor">` and `<meta name="audit-docs">` tags in the file head are the static confirmation if you need one. If any divergences were accepted, the same console line also prints the raw vs. adjusted compliance and which finding ids were excluded.
- Every `critical` finding in `merged.json` has `confidence: verified`. A `critical` that is `inferred` or `unverified` is demoted to `high` by the script and listed under "Needs verification" — tell the user.
- No finding in `merged.json` reads as an absence claim (`missing`/`does not exist`/…) with `evidence_scope` other than `global` — `consolidate.py` would already have rejected it, but if you're inspecting output by hand this is the tell that an agent guessed rather than checked.
- Every entry in `merged.conflicts` is covered by some `review.json.resolutions` item (the reviewer may cover several conflicts in one resolution, so do not compare counts), and if the verdict is BLOCKED it carries `unblock_cost`.

Then give the user the verdict line with the score, the unblock cost if blocked, the two or three findings that matter most, and the file. The report carries the rest.

## Files in this skill

- `references/shadcn-baseline.md` — token contract, radius scale, semantic roles, flavor differences, what a healthy fetch contains.
- `references/extraction.md` — MCP call → snapshot section mapping and normalization rules.
- `references/findings-schema.md` — the JSON contract every agent writes; read it before writing any agent prompt tweak.
- `agents/*.md` — one prompt per specialist plus `reviewer.md`.
- `scripts/consolidate.py`, `scripts/render_report.py`, `scripts/contrast.py` (WCAG math with oklch and alpha compositing — the contrast agent shells out to it rather than doing arithmetic in prose).
- `assets/report_template.html` — the report shell.
