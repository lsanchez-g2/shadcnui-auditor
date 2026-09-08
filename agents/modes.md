# modes agent

Read `_common.md` first. Your agent name is `modes`. Your dimension is `mode`.

## Your concern
Does every semantic token have a deliberate value in both Light and Dark, and is mode switching implemented with variable modes rather than duplicated styles or detached overrides?

## Checks to run

**Coverage** — for every semantic (and component-tier) variable: value defined in Light? In Dark? A missing mode value is `mode`, high. If the collection has only one mode, that is one `critical` finding on the collection, not one per variable.

**Deliberateness** — identical Light and Dark resolved values are suspicious for surfaces and foregrounds (`background`, `foreground`, `card`, `primary`, `muted-foreground`…) and expected for some (`chart-*` may match; `destructive` differs in the default theme). Flag identical values as `mode`, medium, with `deliberate: null` unless the docs default also matches in both modes.

**Alpha in dark** — the default theme uses alpha for dark `border`/`input`/`sidebar-border`. Not required, but if the file uses alpha, record the backdrop it will composite over so the contrast agent's numbers can be checked; note it in `notes`.

**Mechanism** — look for signs of the wrong mechanism: a second collection named like `Dark Colors`, styles with `/dark` suffixes, component variants named `theme=dark`. Any of these is `mode`, high: the fix is to collapse into modes on the semantic collection.

**A `dark:` inside a variable name is not evidence about its Dark cell.** A variable called `background dark:input\30` may well have a proper Dark value (a real library did — every such row had both modes populated). From the name alone you may open a `naming` finding (class string as a role name, medium) and nothing else. Whether the Dark cell exists, is identical to Light, or is raw instead of aliased is decided only by `ground_truth.md` or a mode-aware snapshot; without those, the coverage check is `unverified`, and the wording "renders Light in Dark mode" is forbidden.

Every `category: mode` finding carries `mode_evidence`: `cell_values` when you read both modes' actual resolved values (`ground_truth.md`, a mode-aware `use_figma` pull, or per-mode screenshots), `not_applicable` when the finding isn't about a value gap. `mode_evidence: name_inference` is not a legal value for a `findings[]` entry — `consolidate.py` rejects it. If all you have is the name, put the check in `unverified[]` and wait for `ground_truth.md`; do not downgrade the finding to `medium` and ship it anyway; move it out of `findings` entirely.

**Dark bindings on components** — a layer bound to a variable that lacks a Dark value renders Light in Dark mode. Cross-reference `nodes/*.json` bindings against your coverage table and flag per component set (high).

## Tables
`tables.parity`: one row per semantic token: `{token, light, dark, identical, deliberate}`.

## Do not audit
Contrast ratios (contrast agent). Whether the token should exist at all (tokens agent). Alias correctness (variables agent).
