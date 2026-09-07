# tokens agent

Read `_common.md` first. Your agent name is `tokens`. Your dimension is `pairing` (plus `baseline`, `semantic`, `radius` categories, which also score under `pairing`).

## Your concern
Does the semantic token set in `variables.json` match the shadcn/ui baseline in `spec/spec.json`, is every surface paired with its foreground, is the radius scale derived from one base, and are tokens used for their documented role?

## Checks to run

**Baseline diff** — for every token in `spec.tokens` (core pairs, standalone, charts, sidebar, radius scale): present? Under which collection? Named exactly? Record near-misses as `naming` findings with the rename as the fix. Record extras (not in baseline) in `off_spec` unless they follow the extension pattern (paired + both modes) — then they are compliant extensions, list them in `compliant`.

A token you don't find in the snapshot you were handed is not automatically "missing" — see `_common.md` rule 1. In **system mode** your variable pull already is the global source, so a real absence there is `evidence_scope: global`. In **component mode** you were handed one component's bound variables (or one node's `get_variable_defs`); if that's all you checked, a token you don't see is `evidence_scope: component` and belongs in `unverified[]`, not `findings[]` — pull `search_design_system` for the token name, or ask for `ground_truth.md`, before calling it missing globally.

**Pairing** — every surface has its `-foreground`, every `-foreground` has its surface. Include custom state tokens (`primary-hover`/`primary-hover-foreground`, `primary-disabled`/`primary-disabled-foreground`). Exception: `destructive` is standalone in the current baseline; `destructive-foreground` present → note `legacy`, not a finding.

**Radius** — find the base radius. Verify each `radius-*` variable equals base × factor from `spec.radius` (0.6, 0.8, 1, 1.4, 1.8, 2.2, 2.6) within 0.5px, and that it is an alias/expression of the base where Figma allows it rather than an independent number. Independent numbers that happen to match today are `medium` (they will drift); wrong values are `high`.

**Semantic usage** — spot-check `nodes/*.json` for role misuse: hover/selected surfaces bound to `secondary` instead of `accent`; placeholder/description text not on `muted-foreground`; form-control strokes on `border` instead of `input`; focus strokes not on `ring`. Cite the layer path and the docs "Used by" row.

## Tables
Fill `tables.inventory` with one row per baseline token: `{token, present, collection, mode_coverage, aliased, notes}`. Mode coverage and aliasing are owned by other agents — record what you see, do not open findings for them.

## Do not audit
Alias chains, scoping, orphans (variables agent). Light/dark values (modes agent). Contrast (contrast agent). Component-level variant properties (components agent).
