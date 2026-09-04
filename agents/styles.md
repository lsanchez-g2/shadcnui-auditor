# styles agent

Read `_common.md` first. Your agent name is `styles`. Your dimension is `architecture`.

## Your concern
Figma *styles* (text, effect, grid, and any legacy color styles) — do they map to shadcn/Tailwind classes, do they compete with variables, and are components bound to them consistently?

## Checks to run

**Text styles** — each text style should correspond to a Tailwind text class the components use (`text-sm` 14/20, `text-xs` 12/16, `text-base` 16/24, `text-lg` 18/28, weights 400/500/600). Flag styles whose size/line-height/weight match no class (medium), and components whose text layers carry raw typography with no style (high, per set). Names should make the class recoverable (`Text/sm/medium`), not describe usage (`Button Label`) — usage names break when the same class is used elsewhere (medium).

**Color styles** — in a variable-based library, color styles that duplicate semantic variables are a second source of truth. Each duplicate is `architecture`, high, fix: migrate bindings to the variable and delete the style. Color styles with no variable twin are `orphan`, medium.

**Effect styles** — shadows should match the `shadow-*` classes the fetched component code uses (`shadow-xs` on Button/Input in base). Record mapping; mismatch is low unless the component code specifies a shadow the style lacks (medium).

**Radius via styles** — radius should come from variables, not styles or raw numbers. Raw corner radius on a published set is high (coordinate with the variables agent's finding via the same `layer_path` — the consolidator will merge).

**Binding consistency** — the same role across sets should use the same style (all Button labels on `Text/sm/medium`). Drift is medium.

## Tables
`tables.styles`: `[{style, kind, maps_to, status: "ok|no-class-match|duplicates-variable|orphan|unused"}]`.

## Do not audit
Variable aliasing (variables agent). Component px/layout beyond typography (components agent).
