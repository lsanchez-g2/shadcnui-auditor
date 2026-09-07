# Findings contract

Every specialist writes exactly one file, `findings/<agent>.json`, in this shape. `scripts/consolidate.py` enforces it. The contract is strict because eight agents that each invent their own fields cannot be merged, and a finding without evidence and a source cannot be trusted by the engineer reading the report.

## File shape

```json
{
  "agent": "tokens",
  "mode": "system",
  "flavor": "base",
  "spec_sources": ["https://ui.shadcn.com/docs/theming#theme-tokens"],
  "checks": [
    {"dimension": "pairing", "name": "primary has primary-foreground", "passed": true, "finding_id": null},
    {"dimension": "pairing", "name": "primary-disabled has foreground pair", "passed": false, "finding_id": "tokens-001"}
  ],
  "findings": [ /* Finding objects, below */ ],
  "compliant": ["primary / primary-foreground present in Light and Dark", "…"],
  "off_spec": [
    {"item": "variant=warning on Button", "recommendation": "remove | document as intentional extension", "reason": "not in Button API (base)"}
  ],
  "unverified": [
    {"check": "input token used on Select border", "missing": "Select is not in snapshot/nodes"}
  ],
  "tables": { /* agent-specific, see below */ },
  "notes": "free text, short"
}
```

## Finding object

| field | type | rule |
|---|---|---|
| `id` | string | `<agent>-NNN`, unique within the file |
| `category` | enum | `baseline` `pairing` `semantic` `radius` `architecture` `alias` `orphan` `scope` `mode` `contrast` `state` `variant` `naming` `size` `layout` `typography` `anatomy` `props` `a11y` `style` `governance` |
| `dimension` | enum | `pairing` `contrast` `mode` `architecture` `state_variant` `governance` — which weighted bucket this belongs to |
| `severity` | enum | `critical` (a11y failure, broken alias, wrong API values), `high` (missing pair, mode gap, missing variant/size), `medium` (naming, orphans, drift), `low` (convention, polish) |
| `node_id` | string or null | Figma node the fix lands on. Null only for collection-level findings — then `layer_path` names the collection/variable. |
| `layer_path` | string | `Set / variant=…, size=… / Layer` or `Collection / variable/name` |
| `element` | string | short, specific: `"size property — missing icon-sm value"` |
| `current_value` | string | what the file has |
| `expected_value` | string | what the spec requires, with the exact token/class/px |
| `source` | string | docs URL with anchor, e.g. `https://ui.shadcn.com/docs/theming#radius-scale` |
| `evidence` | string | which snapshot file/field shows it: `variables.json › collections[Semantic].radius-md = 6; base radius = 10 → expected 8` |
| `current_score` | int 1–10 | justified by `evidence` |
| `fix` | string | exact, actionable: `"Create variable color/semantic/primary-disabled-foreground; Light = alias primary-foreground; Dark = alias primary-foreground; scope: text, fill"` |
| `effort` | enum | `S` (<15 min) `M` (15–60 min) `L` (>1 h) |
| `benefit` | string | what the handoff gains, concretely |
| `final_score` | int 1–10 | projected after fix |
| `confidence` | enum | `verified` (read directly, for the exact instance the finding is about) · `inferred` (extrapolated from a sampled instance to unsampled ones — see `sample_scope`; say what was sampled vs extrapolated in `evidence`) · `unverified` (insufficient evidence either way; say what is missing in `evidence`) |
| `off_spec_scope` | bool, optional | `true` when the defect lives on a variant/property shadcn does not define (e.g. a contrast fail inside `Type=Box`, a raw stroke on `State=Pressed` for a component whose API has no pressed state). Still reported, still fixable, but excluded from the score — a parity number must not move because of something outside the spec. Put the same flag on the matching `checks[]` entry. |
| `evidence_scope` | enum, required whenever the finding asserts something is missing/absent (see below) | `component` (checked only the node(s)/variables this component instance binds — e.g. a bare `get_variable_defs` pull or one `nodes/<id>.json`) · `global` (checked the whole library — system-mode's full variable pull, `search_design_system`, or `ground_truth.md`) · `not_applicable` (the finding is not an absence claim) |
| `alias_status` | enum, required when `category: alias` | `aliased_verified` (alias target resolved and named) · `aliased_target_unknown` (the tool exposed an alias marker but not its target — e.g. `get_variable_defs`' flat name→value map) · `not_aliased_verified` (a source that exposes alias chains, e.g. `use_figma`/`ground_truth.md`, confirmed this is a raw literal) · `unknown` |
| `mode_evidence` | enum, required when `category: mode` | `cell_values` (both modes' actual resolved values were read — `ground_truth.md`, a mode-aware `use_figma` pull, or per-mode screenshots) · `name_inference` (inferred only from the variable's name, e.g. a `dark:` fragment) · `not_applicable` |
| `sample_scope` | enum, optional | `exhaustive` (every instance of the axis was inspected) · `sampled` (a subset stands in for the rest — name the sample size/coverage in `evidence`). Required alongside `confidence: inferred`. |
| `divergence_status` | enum, reviewer-only — never set by a specialist | `none` (default) · `candidate` (a specialist may flag in `notes` that a deviation looks consistent/deliberate, for the reviewer to consider — never in the finding itself) · `accepted` (the reviewer promoted it; see `references/../agents/reviewer.md` and `review.json.accepted_divergences`) |

### Absence is not evidence of absence

A finding that claims a token/value/binding is **missing** is a `baseline`-family claim about the whole library, not about one component. Before writing `MISSING TOKEN` (or any `current_value` containing "missing"/"absent"/"does not exist"/"not found"), work out which of these is actually true, and say which in `evidence_scope`:

1. The token does not exist anywhere in the file (checked a **global** source: system-mode's full variable pull, `search_design_system`, or `ground_truth.md`) → `evidence_scope: global`, this is a real `baseline` finding.
2. The token exists globally but this component doesn't reference it → not a "missing" finding at all; it is either nothing (the component has no need for it) or, if the component *should* use it, a binding/rebind finding (see below) — cite the token's global location.
3. The token exists but the component binds a different, wrong token instead → this is a **binding defect**, not a missing-token defect. Say `"rebind to <existing token>"` in `fix`, never `"create <token>"`.
4. There is not enough information to tell — the only source checked was this component's own scope (a bare `get_variable_defs`/one `nodes/<id>.json`, no system-mode pull, no `search_design_system`, no `ground_truth.md`) → this is **not** a finding. Write it to the file's `unverified[]` array instead (`{"check": "...", "missing": "global variable inventory not pulled"}`), with `evidence_scope: component`. `consolidate.py` rejects a `findings[]` entry that reads as an absence claim but carries `evidence_scope: component` — move it to `unverified` and rerun.

The same principle applies to alias targets (an `alias_status: aliased_target_unknown` must never be reported as `not_aliased_verified`) and to mode values (a `mode_evidence: name_inference` must never be reported as a confirmed mode gap — see the modes agent).

## Rules the script enforces

- `id`, `category`, `dimension`, `severity`, `layer_path`, `element`, `expected_value`, `source`, `evidence`, `fix`, `effort`, `confidence` are required and non-empty.
- `source` must start with `https://ui.shadcn.com/`.
- `checks[].finding_id`, when present, must exist in `findings`.
- A `critical` finding with `confidence` other than `verified` (i.e. `inferred` or `unverified`) is demoted to `high` and listed under "Needs verification" in the report.
- `confidence: inferred` requires `sample_scope` to be present (`exhaustive` or `sampled`) — an extrapolation without a stated sample is a schema violation.
- A finding whose text reads as a claim about *every* instance of an axis ("all 264 variants", "every variant") requires `sample_scope`, regardless of `confidence` — a universal-quantifier claim with no sample declared at all is a schema violation, not just an `inferred`-without-`sample_scope` one. And `sample_scope: sampled` together with `confidence: verified` is itself a violation: extrapolating from a subset to "every" instance is `inferred` by definition.
- A finding whose text reads as a mode-rendering claim ("renders Light in Dark", "will render Light in Dark") requires `mode_evidence`, whether or not `category` is literally `mode` — this mistake has shipped under `category: governance` in a real audit.
- A finding whose `current_value` or `element` matches absence language (`missing`, `absent`, `does not exist`, `not found`, or similar) must carry `evidence_scope: global`. One with `evidence_scope: component` (or missing entirely) is a schema violation — the consolidator's message tells you to move it into that agent's `unverified[]` array instead, per "Absence is not evidence of absence" above.
- A finding with `category: alias` must carry a valid `alias_status`. One asserting `not_aliased_verified` needs `evidence` that names an alias-exposing source (`use_figma`, `ground_truth.md`) — evidence citing only `get_variable_defs`/`variables.json` (which does not expose alias targets) is rejected; use `aliased_target_unknown` instead.
- A finding with `category: mode` must carry a valid `mode_evidence`, and may never be `name_inference` — a mode claim resting only on the variable's name belongs in `unverified[]`, not `findings[]` (see the modes agent's forbidden-wording rule).
- Duplicates across agents are merged by `(node_id-or-layer_path, property class)`, where the property class is derived from the element text (naming, anatomy, description, ring, label, stroke-width, stroke, radius, fill, height, width, padding, gap, icon, opacity, effect). Highest severity wins, all agents recorded, all `evidence` strings kept. Write the `element` so the class is unambiguous: lead with the property ("stroke colour — …", "stroke width — …", "icon slot name — …"), because two agents writing "icon" for a colour and a naming issue will be merged and the reviewer has to split them.
- Checks and findings with `off_spec_scope: true` are excluded from every score and listed separately in the report. Findings the reviewer promotes to `divergence_status: accepted` (see `review.json.accepted_divergences`) are excluded from the **adjusted** score the same way — `report.html` shows both the raw and the adjusted number, never silently swaps one for the other.

### Divergence vs defect

shadcn/ui is the audit's reference baseline, not the file's absolute source of truth. A finding on an axis shadcn *does* define (a value the API has, like Button's `size`) can still be a deliberate, system-wide brand decision rather than a mistake — unlike `off_spec_scope`, which is for axes shadcn doesn't define at all. Specialists never make this call: write the raw finding as usual (it is real, verifiable, and reported), and if the same deviation recurs consistently across every *sampled* instance of that axis, add one line to `notes` (e.g. `"consistent across all 24 sampled Button variants — possible intentional divergence, not drift"`). Only the reviewer may promote a finding to `divergence_status: accepted`, in `review.json.accepted_divergences`, with the sampling evidence that justifies it. See `agents/reviewer.md`.

## Agent-specific `tables`

| agent | key | shape |
|---|---|---|
| tokens | `inventory` | `[{token, present, collection, mode_coverage: "Light+Dark|Light|Dark|none", aliased: true|false|null, notes}]` |
| contrast | `matrix` | `{Light: [{pair, surface_hex, foreground_hex, backdrop_hex|null, ratio, aa, aa_large_ui, aaa, exempt}], Dark: […]}` |
| states | `coverage` | `{<ComponentSet>: {variants: [...], states: [...], cells: {"<variant>|<state>": "present|missing|inconsistent"}, convention: "opacity|token|mixed|unknown"}}` |
| components | `parity` | `{<ComponentSet>: {axes: {naming, variants, sizes, states, tokens, layout, typography, anatomy, props, a11y} → "pass|fail|unverified"}}` |
| variables | `chains` | `[{variable, tier: "primitive|semantic|component", alias_of, resolves_to, status: "ok|raw|broken|orphan|misscoped"}]` |
| modes | `parity` | `[{token, light, dark, identical: bool, deliberate: bool|null}]` |
| styles | `styles` | `[{style, kind: "text|effect|grid|color", maps_to: "text-sm font-medium|…|none", status}]` |
| governance | `readiness` | `{<ComponentSet>: {published, description, hidden_layers: n, naming_consistent, code_connect_ready}}` |

## Checks: how the score is computed

`checks` is the scoring input. One entry per thing you examined, pass or fail. The health score for a dimension is `passed / total` across all agents' checks in that dimension. Log the passes too — a report that only lists failures cannot show a compliance %, and the engineer needs to know what not to touch.

Weights: pairing 20, contrast 25, mode 20, architecture 20, state_variant 15. `governance` is reported, not weighted.

Component mode: the compliance % is simply `passed / total` over every check.
