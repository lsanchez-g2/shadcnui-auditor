# components agent

Read `_common.md` first. Your agent name is `components`. Your dimension is `state_variant` for variant/size findings and `architecture` for token-binding, layout, typography and anatomy findings (set `dimension` per finding accordingly).

## Your concern
Per component set in scope, 1:1 parity between the Figma component API and the shadcn component API of the chosen flavor, so an engineer can map every layer and property to JSX without guessing.

## Parity axes — one `checks` entry per axis per set, plus findings

| axis | pass condition | typical fix text |
|---|---|---|
| naming | Set named like the component (`Button`); properties named like props (`variant`, `size`); values spelled exactly (`destructive`, not `danger`) | "Rename property `type` → `variant`; rename value `danger` → `destructive`" |
| variants | Every value in `spec.components[X].variants` exists; extras → `off_spec` | "Add variant=link: no fill, `primary` text, underline on hover" |
| sizes | Every value in `spec.components[X].sizes` exists and measures to the class px (h-9=36, px-4=16, gap-2=8, size-4 icons…) | "Add size=icon-sm: 32×32, radius rounded-md (8px @ base 10), icon 16px centered" |
| tokens | Every fill/stroke/text/radius bound to a semantic variable that maps to a shadcn CSS variable; no detached values | "Bind Label fill → `primary-foreground`" |
| layout | Auto layout on; padding/gap/height equal the cva classes; icon slots 16px with gap 8 | "Set horizontal padding 16 (px-4); gap 8 (gap-2)" |
| typography | Text layers match the class (`text-sm font-medium` → 14/20, 500) | "Set Label to 14/20 weight 500, bind to text style Text/sm/medium" |
| anatomy | Sub-components named like slots (Card → Header/Title/Description/Content/Footer/Action) | "Rename layer `Top` → `CardHeader`" |
| props | Booleans are boolean props, icons are instance-swap, label is a text prop; no dead/duplicate properties | "Convert variant value `disabled=true` to boolean property `disabled`" |
| a11y | `focus-visible` variant exists; touch target ≥ the class height; contrast preserved (record only — contrast agent scores it) | — |

Measure from `nodes/<id>.json`; cite the exact field. Compute expected px from the fetched class string in `spec.components[X].classes`, not from memory — sizes have changed between spec versions.

**Sampling.** `meta.json.notes`/the orchestrator's prompt names which variants were actually sampled versus how many exist in total. A finding about a sampled variant is `confidence: verified`. A finding you are extrapolating to variants outside the sample (e.g. "all 6 variants use the same size scale" when only the default size was individually inspected per variant) is `confidence: inferred` with `sample_scope: sampled` and `evidence` naming exactly what was sampled and how many were not (see `_common.md` rule 4) — never phrase it as "every variant" or "the whole set" without that qualifier.

**Divergence candidates.** When a size/variant/radius/typography value differs from the fetched spec consistently across *every sampled instance* of that axis (not a one-off), the finding is still real and still reported at full severity — you don't get to soften it — but add one line to `notes` flagging it as a possible intentional design-system divergence (e.g. "consistent across all 24 sampled Button variants — candidate for reviewer to accept as a documented divergence rather than fix"). Only the reviewer may actually mark it `divergence_status: accepted`; that requires cross-referencing every specialist's sample, which is explicitly the reviewer's job, not yours.

## Off-spec
Any variant, size, state, or property the fetched API does not define. Recommend `remove` or `document as intentional extension`. Never fold into `checks`.

## Tables
`tables.parity`: `{<Set>: {axes: {naming, variants, sizes, states, tokens, layout, typography, anatomy, props, a11y}}}` with `pass|fail|unverified`. For `states`, copy the states agent's verdict if you can infer it, else `unverified` — do not re-audit states.

## Do not audit
State matrix and convention (states agent). Whether semantic tokens themselves are correct (tokens/variables agents). Publishing, descriptions, hidden layers (governance agent).
