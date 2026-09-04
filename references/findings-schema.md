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
| `confidence` | enum | `verified` (read from snapshot) or `unverified` (inferred; say why in `evidence`) |
| `off_spec_scope` | bool, optional | `true` when the defect lives on a variant/property shadcn does not define (e.g. a contrast fail inside `Type=Box`, a raw stroke on `State=Pressed` for a component whose API has no pressed state). Still reported, still fixable, but excluded from the score — a parity number must not move because of something outside the spec. Put the same flag on the matching `checks[]` entry. |

## Rules the script enforces

- `id`, `category`, `dimension`, `severity`, `layer_path`, `element`, `expected_value`, `source`, `evidence`, `fix`, `effort`, `confidence` are required and non-empty.
- `source` must start with `https://ui.shadcn.com/`.
- `checks[].finding_id`, when present, must exist in `findings`.
- A `critical` finding with `confidence: unverified` is demoted to `high` and listed under "Needs verification" in the report.
- Duplicates across agents are merged by `(node_id-or-layer_path, property class)`, where the property class is derived from the element text (naming, anatomy, description, ring, label, stroke-width, stroke, radius, fill, height, width, padding, gap, icon, opacity, effect). Highest severity wins, all agents recorded, all `evidence` strings kept. Write the `element` so the class is unambiguous: lead with the property ("stroke colour — …", "stroke width — …", "icon slot name — …"), because two agents writing "icon" for a colour and a naming issue will be merged and the reviewer has to split them.
- Checks and findings with `off_spec_scope: true` are excluded from every score and listed separately in the report.

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
