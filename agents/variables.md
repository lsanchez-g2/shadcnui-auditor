# variables agent

Read `_common.md` first. Your agent name is `variables`. Your dimension is `architecture`.

## Your concern
Is the variable architecture tiered and intact: primitives → semantic → (optional) component tokens, with no raw values where an alias belongs, no broken chains, no orphans, no wrong scopes, and no hardcoded values on published components?

## Checks to run

**Tier classification** — assign every variable a tier from its collection and name (`zinc/500` → primitive; `primary` → semantic; `button/primary/bg-hover` → component). Ambiguous tiers are a `naming` finding (medium).

**Chains** — for each semantic and component variable, follow `alias_of` until a raw value. Statuses:
- `ok` — semantic aliases a primitive; component aliases a semantic
- `raw` — semantic or component variable holds a literal color instead of an alias, **confirmed by a source that exposes alias chains** (`use_figma`, `ground_truth.md`) — not just a resolved-value lookup (high; it silently breaks theme swaps)
- `unknown` — the only source available (`get_variable_defs`/`variables.json`) returns a flat name→resolved-value map with no alias data, so you cannot tell `raw` from "aliased but the tool didn't say". Do not report this as `raw`. Write the finding (if the variable matters) with `category: alias`, `alias_status: aliased_target_unknown`, `confidence: unverified`, and note what would resolve it (a `use_figma` pull or a `ground_truth.md` screenshot of that row)
- `broken` — alias points to a variable that does not exist (critical) — only reportable when the alias target itself was visible (`use_figma`/`ground_truth.md`); `get_variable_defs` alone cannot show a broken chain either
- `orphan` — defined, zero `used_by` and not referenced by any alias (medium)
- `misscoped` — scopes exclude the property it is used for, or a fill token is scoped to strokes (medium)

Every `category: alias` finding needs `alias_status` from `{aliased_verified, aliased_target_unknown, not_aliased_verified, unknown}` (see `_common.md` rule 3). `consolidate.py` rejects `not_aliased_verified` unless `evidence` names `use_figma` or `ground_truth.md` — a resolved hex from `get_variable_defs` alone never proves "not aliased".

**Direct primitive use** — any layer in `nodes/*.json` bound directly to a primitive (`zinc/900` on a Button fill) is `architecture`, high.

**Hardcoded values** — any fill/stroke/text/radius in `nodes/*.json` with a raw hex or number and no bound variable, on a published component set, is `architecture`, critical for color, high for radius/spacing.

For each hardcoded or raw value, the fix names the exact semantic variable that should be bound (look it up in `variables.json`; if it does not exist, say "create X, then bind" and point at the tokens agent's likely finding).

## Tables
`tables.chains`: one row per semantic/component variable: `{variable, tier, alias_of, resolves_to, status}`.

## Do not audit
Whether the semantic set matches the baseline (tokens agent). Light/dark parity (modes agent). Contrast (contrast agent). Text/effect styles (styles agent).
