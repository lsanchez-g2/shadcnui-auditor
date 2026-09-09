# Learnings — Apollo v2 (SA) Avatar Family Audit & Remediation

Session notes from auditing and remediating the Apollo Avatar family (Figma
file `3401ZFUHoboOwA6GGjAEsq`, node `23:988` → `Components` section
`296:5188`: Avatar `17100:29935`, Avatar / Avatar Badge `21122:16180`, Avatar
Group `17100:83077`, Avatar / Form Field `18692:42355`, "Apollo v2 (SA)
Design System") against the `shadcnui-auditor` skill. The headline result:
**3 of the 6 "architecture" fixes the audit reported turned out to be false
positives** once checked against the live file via `use_figma`. Captured
here so the next audit doesn't repeat the mistake that produced them.

## 1. The core finding: `get_design_context` is not a structural source of truth

Every `components`/`variables`-dimension finding in this audit was written
from `snapshot/nodes/<id>.json`, which was built entirely from
`get_design_context`'s reconstructed JSX. That tool exists to hand an
implementer a reasonable starting point for *codegen* — it flattens real
component instances into inline conditional `<div>`s, collapses
`strokeAlign`/box-model nuance into approximate Tailwind classes, and has no
way to reveal a bound component property. Three findings that read as solid
defects in that reconstruction evaporated on direct inspection:

- **"Badge is baked in as an always-on inline layer, never actually
  instances the standalone `Avatar / Avatar Badge` component."** False.
  Every one of the 15 sampled Avatar cells has a real `INSTANCE` child of
  the standalone Avatar Badge component set, and a `Show Badge` BOOLEAN
  component property already exists on Avatar, already correctly linked via
  `componentPropertyReferences: { visible: "Show Badge#21123:0" }` on every
  instance. `get_design_context` reconstructs a linked boolean-controlled
  instance as `showBadge = true` inline JSX — indistinguishable, from the
  reconstruction alone, from a truly hardcoded always-on layer.
- **"Badge/avatar stroke uses `border` (box-model) instead of `ring`
  (box-shadow), so it will diverge from ungrouped usage when laid out with
  siblings."** False. The real stroke is `strokeAlign: "OUTSIDE"` — Figma's
  closest native equivalent to a CSS ring (the fill/content box is
  unaffected; only the rendered paint extends outward). `get_design_context`
  had reconstructed it as a plain Tailwind `border-2 border-background`
  class, which reads as inside/box-model with no way to tell `OUTSIDE` from
  `INSIDE` alignment from the generated code alone.
- **"Avatar Group's overlap is hardcoded per-child negative margins
  (`mr-[-8px]` on the first two, flush on the last), not a systematic
  spacing rule — will not scale if members are added/removed."** False. The
  real `Items` node is a genuine `HORIZONTAL` auto-layout frame with
  `itemSpacing: -8` and every child at `layoutPositioning: "AUTO"` — fully
  systematic, scales correctly with member count. The JSX reconstruction
  had turned that one auto-layout property into per-child inline margin
  utilities, which reads exactly like the manual-margin anti-pattern it
  isn't.

**Rule for the next audit:** any finding in the `architecture` category —
anything claiming "this is implemented as X instead of Y" about *how* a
node is built (instance vs. inline layer, stroke primitive, layout
mechanism, property wiring) — must be verified with a direct read-only
`use_figma` inspection (`componentPropertyReferences`, `strokeAlign`,
`layoutMode`/`itemSpacing`/`layoutPositioning`, `componentPropertyDefinitions`)
before it's written to `findings/*.json`, not inferred from
`get_design_context`'s JSX. Findings about *values* (a wrong px, a wrong
color, a missing token) are comparatively safe from this trap since
`get_design_context` reads those fairly faithfully — it's specifically
claims about implementation *mechanism* that it cannot be trusted for.
Concretely: extend `references/extraction.md`'s normalization step so that,
for any node whose family maps to more than one shadcn sub-component (a
component with a nested/sibling badge, group, or count part), the
orchestrator also runs a live `use_figma` structural probe (linked
properties, stroke align, auto-layout spacing) and stores it in
`nodes/<id>.json` alongside — not instead of — the `get_design_context`
JSON, so the `components`/`variables` agents have both and can cite the
live probe specifically for architecture-category claims.

## 2. Real defects fixed on the Avatar family (Figma)

- **Missing `AvatarGroupCount` component.** shadcn's Avatar family defines
  a sibling `data-slot=avatar-group-count` component (the "+N" overflow
  chip); it did not exist anywhere in this file (confirmed via a fan-out
  search of all 83 component pages, not just the audited scope). Built it
  as a new component, reusing — not creating or rebinding — the exact same
  `accent` fill and `primary` text variable bindings the file's own
  `Avatar` `Type=Fallback, Size=default` component already uses, so the fix
  needed zero new token decisions and stayed inside the "no color-token
  changes" constraint the user set for this remediation pass.
- **Avatar Badge's `Size` vocabulary didn't share Avatar's.** Avatar's
  `Size` variant is `xl|lg|default|sm|xs`; Avatar Badge's was the unrelated
  raw-numeric `2|2.5|3` (its own literal pixel sizes). Renamed the three
  variant child components' names (`Type=Default, Size=2` →
  `Type=Default, Size=sm`, etc.) so the property now reads
  `default|lg|sm` — a shared vocabulary subset, not a full 5-value match,
  since the badge only ever needs 3 discrete sizes. Renaming only relabels
  the child component; existing instances keep pointing at the same node
  IDs, so nothing else in the file was affected.
- **Avatar's `Type` variant (Image/Fallback/Icon) has no equivalent shadcn
  prop** — the real API is a composable `Root` whose content mode comes
  from which child (`<AvatarImage>`/`<AvatarFallback>`) is rendered, with
  Base UI's `AvatarPrimitive` auto-swapping to fallback on image-load
  failure; `Icon` isn't a distinct shadcn concept at all (it's just
  arbitrary children inside `AvatarFallback`). Given the user's explicit
  choice (see §3), this was **documented, not restructured**: added a
  component description (matching the existing convention already used on
  this file's `Button` component) explaining the `Type=Image|Fallback|Icon`
  → JSX composition mapping per value, clarifying `Show Badge` maps to a
  sibling `<AvatarBadge>` rather than a child, and flagging that `xl`/`xs`
  sizes have no shadcn `size` prop equivalent.

## 3. Scope decisions the user made explicitly

- **Excluded every fix that would modify a color token**, as a deliberate
  scoping choice for this remediation pass (not because those findings were
  wrong): `tokens-001` (missing `after:border-border` ring),
  `tokens-002`/`tokens-003` (missing `muted-foreground`/`accent-foreground`
  pairs), `contrast-001` (badge border vs. accent surface, 1.14:1),
  `components-003` (Fallback/Icon backdrop bound to `accent` instead of
  `muted`), `components-008` (badge has no plain `primary`/`primary-
  foreground` default cell). These remain open findings in the report —
  they were scoped out of *this* session, not resolved.
- **For the one fix carrying real breakage risk** (`components-001`, the
  `Type` variant), explicitly asked the user "document only" vs. "restructure
  the variant axis" before touching anything, because restructuring would
  have affected every existing Avatar instance in this file (and any other
  file referencing it) that has a `Type` value set. User chose "document
  only." Lesson for future audits: **flag any fix whose action would change
  a component's variant *axis* (add/remove/rename a property, not just a
  property's value) as a separate confirm-before-acting step**, distinct
  from the general "apply the fixes" go-ahead — the blast radius of an axis
  change (breaks every existing instance's variant selection) is
  categorically different from a value rename or a new additive component,
  even though both showed up as "architecture" findings at the same
  severity.

## 4. Figma Plugin API / MCP gotchas hit in this session

- **`get_variable_defs` needs a concrete node, not the root canvas.**
  Calling it on the page/canvas node (`23:988`) returned `"You currently
  have nothing selected. You need to select a layer first"` — it needs a
  node with actual bound-variable usage under it (a component set worked:
  `17100:29935`). The tool's own description doesn't warn about this; only
  hit it live.
- **`get_design_context` on a component instance triggers an interactive
  Code Connect prompt** ("Some Figma design components are not connected to
  your codebase... Would you like to connect...") that must be answered
  before the call returns real content. For an audit (not a codegen task),
  answer "no" by re-calling with `disableCodeConnect: true` rather than
  going interactive — there's nothing to map and it just adds a wasted
  round trip otherwise.
- **Collection/mode/alias structure is a separate `use_figma` read from
  `get_variable_defs`.** The latter is flat (`name → resolved value for the
  current mode only`); getting the real collection list (`3. Mode`:
  Light/Dark, `2. Theme`: Default-but-encodes-mode-in-the-name, `1.
  TailwindCSS`: Default, etc.) and each variable's per-mode alias chain
  needs the read-only `figma.variables.getLocalVariableCollectionsAsync()` +
  `getVariableByIdAsync()` script from `references/extraction.md`. This
  file's own "2. Theme" tier encodes Light/Dark in the variable *name*
  suffix (`colors/border-light` / `colors/border-dark`) rather than in a
  Figma mode column — worth a general callout in `extraction.md` that a
  file can implement "modes" via either mechanism, and the alias-chain
  script has to resolve through whichever one is actually in use, not
  assume mode columns exist at every tier.
- **A page/section holding a *small*, fully-sample-able number of
  component sets is not automatically "system mode" in the sense
  `agents/_common.md` describes.** This audit was routed as `system` mode
  per the routing table (a page/section holding several component sets),
  but with only 4 sets and ≤20 variants each, every set was fully sampled
  via `get_design_context` — i.e., `nodes/<id>.json` existed for
  everything, unlike the "no `nodes/`, score only what's visible at the
  collection level" system-mode default. Every specialist agent prompt had
  to explicitly override `_common.md`'s system-mode restriction ("nodes/
  IS populated for all 4 — use it, this is deeper than typical system
  mode"), or the agents would have silently under-scored by skipping
  checks they actually had data for. Worth a third routing tier in
  `SKILL.md`'s table: a page/section with multiple sets but a small total
  variant count across all of them should route to a "system mode, fully
  sampled" variant that tells agents to treat `nodes/` as authoritative
  wherever present, rather than leaving the orchestrator to hand-write that
  override into every one of the 8 agent prompts.
- **Component descriptions render through Figma's own rich-text escaping.**
  Setting `component.description` to a string containing `<`, `>`, `'`
  comes back HTML-entity-escaped (`&lt;`, `&gt;`, `&#39;`) when read back —
  expected Figma behavior (the field supports link/rich-text markup
  internally), not a write bug. Don't re-escape or "fix" this on a
  subsequent read; the stored/rendered value is correct.
- **Renaming a variant child component is instant and non-breaking for
  instances.** Confirmed directly (not just inferred): renaming
  `Type=Default, Size=2` → `Type=Default, Size=sm` immediately updated
  `componentSet.componentPropertyDefinitions.Size.variantOptions` to the
  new label with no instance side effects, since instances reference the
  variant child by node ID, not by name. Safe, low-risk fix category —
  distinct from the axis-level risk in §3.

## 5. Repo/workflow boundaries for this engagement

- `shadcnui-auditor` is the repo authorized for this session's
  branch/commit; changes here are docs-only (`learnings-avatar-audit.md`),
  no schema/script/prompt changes were made or requested this round (unlike
  the Button audit's PR #1).
- `bx-monorepo` (where the audit itself was run, from a project worktree)
  was not touched by this file — the learnings capture happens in the
  skill's own repo, matching the Button-audit precedent.
- Live Figma edits for this audit (`AvatarGroupCount` creation, Avatar
  Badge size renames, Avatar description) were applied directly to the
  Figma file, not staged as a PR anywhere — there is no "diff" for a Figma
  edit the way there is for code; the audit report + this learnings file
  are the record of what changed and why.
