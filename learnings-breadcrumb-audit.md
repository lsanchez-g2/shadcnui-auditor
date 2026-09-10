# Learnings — Apollo v2 (SA) Breadcrumb Audit & Remediation

Session notes from auditing and remediating the Apollo Breadcrumb component
(Figma file `3401ZFUHoboOwA6GGjAEsq`, page "Breadcrumb" `23:1004` → size-variant
frame `Breadcrumb` `109:947` and item variant set `Breadcrumb / BreadcrumbItem`
`195:1993`, "Apollo v2 (SA) Design System") against the `shadcnui-auditor`
skill, run from a `bx-monorepo` project worktree. Captured here so the next
audit — of this component or any other — doesn't rediscover the same traps.

## 1. "Give me the top 10, brief" is a real, unhandled routing case

The user explicitly asked for brevity up front ("Please be brief I just want
to see the 10 more important changes"), before any audit work started. The
skill as written has exactly one path: Phase 0 (route + fetch spec + extract
snapshot) → Phase 1 (8 parallel specialist agents) → Phase 2 (`consolidate.py`)
→ Phase 3 (reviewer agent) → Phase 4 (`render_report.py`, full HTML report).
There is no lighter-weight mode for "just tell me the highlights."

What actually happened: the full swarm was **not** run. Instead, a condensed
single-pass manual audit was done — one `get_metadata` call to identify the
node, two `get_design_context` calls (component set + size-variant frame) and
one `get_variable_defs` call for evidence, one `WebFetch` of the docs page and
one of the `base-nova` registry JSON for the spec side, then findings were
synthesized directly instead of writing `findings/*.json` and running
`consolidate.py`/`render_report.py`. This produced a reasonable, evidence-based
top-10 list faster and with far fewer tokens, but it skipped every rigor
mechanism the skill actually has: no `evidence_scope`/`confidence`/
`alias_status` fields, no dedup-by-property across independent checks, no
computed health score, no `review.json` reconciliation of conflicts. For a
"just the highlights" request that's a reasonable trade, but it was an
improvised decision, not a documented one.

**Rule for next time:** add a third top-level mode to `SKILL.md`'s Phase 0 —
call it "quick pass" — triggered by an explicit brevity/top-N request. Quick
pass still requires one real fetch of the shadcn spec (never audit from
memory) and one real Figma read per component, but skips the 8-agent fan-out
and the render pipeline, and the final reply must say plainly that it is a
quick pass (fewer checks, no computed score, no persisted `merged.json`) so
the user knows it isn't the full audit contract. Do not silently downgrade
rigor without saying so.

## 2. Real defects fixed on the Breadcrumb (Figma)

- **Focus-state stroke bound to a variable whose own name says it's dead.**
  `Dropdown`/`Link`/`Link Current` Focus variants (`18437:15333`,
  `18437:15336`, `18437:15340`) and the Ellipsis-Focus icon wrapper instance
  (`18437:15339`) all had their stroke color bound to
  `button/legacy-outline-ring (unused — was custom/outline)`. Found the
  correct replacement by searching all local variables for
  `/ring|focus|outline/i` and cross-checking collections — `base/ring` (in
  the `3. Mode` collection, Light/Dark) is the token every other focus
  treatment in the file actually resolves to. Rebound all four nodes'
  `strokes[0].color` from the legacy variable to `base/ring` via
  `figma.variables.setBoundVariableForPaint`. Confirmed visually via
  `get_screenshot`: rings went from muted grey to the correct purple.
- **Ellipsis was 36×36 (`h-9 w-9`), spec is `size-5` (20×20).** All three
  Ellipsis component variants (`109:375` Default, `980:14187` Hover,
  `18437:15338` Focus) were resized 36→20 on both axes. Verified first that
  all three are `HORIZONTAL` auto-layout with `FIXED`/`FIXED` sizing modes
  and a `FIXED`/`FIXED` 16×16 icon child, so the resize couldn't cascade into
  an unwanted reflow of the icon.

Both fixes were applied at the **master component/variant level only** — not
per-instance, and not by walking every placed instance across the file. A
variable-bound property or a component-level `resize()` propagates
automatically to every instance that hasn't detached/overridden that specific
property; chasing individual instances is unnecessary and out of scope unless
an instance is known to have an override.

## 3. Findings surfaced but deliberately NOT applied (architecture-axis, needs sign-off)

Distinguishing "mechanical property fix" from "changes the component's public
contract" mattered here, same lesson as the Avatar audit's `Type`-variant call
(§3 there) but hit for different reasons:

- **"Dropdown" item variant has no shadcn sub-component equivalent** (the
  canonical 7 are List/Item/Link/Page/Separator/Ellipsis — nothing is a
  text+chevron-down dropdown trigger). Left alone; renaming/restructuring it
  would be inventing an API decision, not applying a documented fix.
- **`Size=md/sm` variant axis doesn't exist in shadcn's Breadcrumb API at
  all.** Same reasoning — an axis-level change (or its removal) needs a
  product call, not a unilateral fix.
- **"md" item gap is 10px vs. spec's only documented gap of 6px
  (`gap-1.5`).** A value fix in isolation would be mechanical and safe, but
  it's entangled with the (out-of-scope) `Size` axis question above — left
  as a reported-but-unapplied finding rather than fixed in isolation.
- **Ellipsis modeled as interactive/focusable vs. spec's
  `role="presentation" aria-hidden="true"`, and no sr-only "More" label.**
  Figma has no accessible-name/ARIA concept to encode directly on a node —
  this is a decision about whether Ellipsis is meant to open a dropdown menu
  (in which case it's *correctly* interactive and needs a real accessible
  name added at implementation time) or stay purely decorative. Not a
  Figma-layer fix either way.
- **No nav/list semantic intent conveyed in layer naming**, and **no
  Active/pressed state defined anywhere in the set.** Documentation/handoff
  gaps and a scope decision respectively, not mechanical property fixes.

**Rule reinforced:** before touching anything in response to "apply the
changes," classify each finding as (a) a value/token/size fix on an existing
property — safe to apply directly, or (b) anything that adds, removes, or
changes the meaning of a variant/property axis, or requires ARIA/semantic
decisions Figma can't encode — always surface these separately and get
explicit go-ahead, never bundle them into a blanket "apply the top 10."

## 4. Process: asked before touching anything, not just before pushing

Before making any Figma edit, the ambiguity in "apply the changes" (fix the
Figma file? build/update the component in `packages/apollo-ui`? both?) was
resolved with an explicit clarifying question rather than guessing — editing
a shared, live design system file is a hard-to-reverse action affecting
every downstream consumer, distinct in kind from editing a local code diff.
The user picked "Figma file only." Lesson: when a fix-it instruction doesn't
say *where*, and the candidate destinations differ in blast radius (shared
design file vs. a local package no one else depends on yet), ask before
picking one — don't default to "the one I was just looking at."

## 5. Figma Plugin API / MCP notes

- **Searching all local variables by name regex is an effective way to find
  the "correct" token before a rebind**, when the wrong/legacy binding is
  already suspected: `getLocalVariablesAsync()` filtered by
  `/ring|focus|outline/i` surfaced `base/ring` immediately alongside several
  decoys (`button/outline-bg`, `base/outline-hover`, the legacy variable
  itself) — cross-checking against which collection each candidate lives in
  (`3. Mode` = the live Light/Dark token tier) picked the real one out of the
  list. Don't rebind to the first plausibly-named variable; enumerate
  candidates and check the collection tier.
- **A variable name that says `unused`/`legacy`/`deprecated` in a parenthetical
  is a high-confidence signal on its own**, worth flagging automatically
  regardless of what else an audit finds — the token's own author already
  marked it dead. Worth teaching the `tokens`/`governance` agent prompts to
  treat this as a near-automatic `critical` finding rather than requiring the
  same evidentiary weight as an inferred mismatch.
- **Always check `layoutMode`/`primaryAxisSizingMode`/
  `counterAxisSizingMode`/child `layoutSizingHorizontal`/`layoutSizingVertical`
  before calling `resize()`** on a component that has children — confirmed
  again here (matches the Button audit's hug-height regression gotcha in
  reverse: this time checking first meant the resize was risk-free because
  every relevant node was already `FIXED`/`FIXED`).
- **`get_design_context`'s reconstructed JSX is good enough for *value* claims
  here** (icon sizes, gap tokens, color variable names, state coverage) —
  this component had no nested-instance/property-wiring ambiguity like the
  Avatar Badge case, so the Avatar audit's warning about verifying
  `architecture`-category claims via `use_figma` didn't end up being a trap
  in this session. Still worth the reminder: that JSX becomes unreliable
  specifically for claims about *how* something is built (instance vs.
  inline, linked property, layout mechanism) — not for what value a leaf
  property holds.
- `get_metadata` on a page node (`23:1004`) returned a normal frame/symbol
  tree, no "nothing selected" error — unlike `get_variable_defs`, which does
  need a node with real bound-variable usage under it (confirmed in the
  Avatar audit, not re-hit here since a concrete node was passed directly).

## 6. Repo/workflow boundaries for this engagement

- `shadcnui-auditor` is the repo authorized for this session's
  branch/commit; this file is a docs-only addition
  (`learnings-breadcrumb-audit.md`) — no schema/script/prompt changes were
  made or requested this round.
- `bx-monorepo` (the project worktree the audit was actually run from) was
  not touched by this file, and no Breadcrumb component was built there this
  session — the user chose "Figma file only," so `packages/apollo-ui` still
  has no Breadcrumb implementation.
- Live Figma edits (the two fixes in §2) were applied directly to the Figma
  file, not staged as a PR anywhere — there is no code "diff" for a Figma
  edit; the audit findings + this learnings file are the record of what
  changed and why.
