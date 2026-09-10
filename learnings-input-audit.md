# Learnings — Apollo v2 (SA) Input Audit & Remediation

Session notes from auditing and remediating the Apollo Input component
(Figma file `3401ZFUHoboOwA6GGjAEsq`, node `65:533`, "Apollo v2 [SA] -
Design System") against the `shadcnui-auditor` skill, flavor `radix`.
Captured here so the next audit — of this component or any other — doesn't
rediscover the same traps. Unlike the Button session, no skill code was
changed in this pass; §1 below is a set of *recommended* schema/agent
changes for the next iteration, not landed work.

## 1. Recommended auditor discipline improvements (not yet landed)

- **`get_design_context`'s box-shadow serialization silently drops a local
  effect opacity that is independent of the bound color variable.** The
  `states` agent reported the Focus-state ring at "alpha 1 (100%)" because
  `get_design_context` rendered it as
  `shadow-[0px_0px_0px_3px_var(--base\/ring,#5a35c0)]` — a plain hex, no
  alpha suffix. Reading the actual Effect Style live
  (`figma.getLocalEffectStylesAsync()`) during remediation showed the true
  stored `color.a` was **0.65**, not 1 — the shared `focus/default` style
  carries its own local alpha that the bound `base/ring` variable (itself
  fully opaque) does not override or expose through the Tailwind
  arbitrary-value string. The finding was still correct in *direction*
  (too opaque vs. spec's 50%) but wrong in *magnitude* (65%→50% is a much
  smaller gap than 100%→50%). Recommendation: whenever a finding's
  `evidence` is sourced only from `get_design_context`'s CSS/class output
  for an **effect** color, cross-check it with a read-only
  `figma.getLocalEffectStylesAsync()` / `node.effects` probe before
  asserting an alpha value, the same way `extraction.md` already requires
  `use_figma` (not `get_variable_defs`) for variable *structure*. Add this
  as an explicit extraction step for any component whose states rely on
  `DROP_SHADOW`/`INNER_SHADOW` effects (focus rings, invalid rings).
- **A single native `<input>`/`<textarea>` element's `type`/native
  attribute modeled as a top-level Figma Variant is a recurring
  architecture smell, not a one-off.** shadcn's Input has no variant prop
  at all — `type="password"`/`type="file"` are native HTML attributes
  sharing one class string. Figma modeled `Variant=Default|Password|File`
  as three sibling values, each duplicating the full 6-value State axis
  (18 variants for what is conceptually 6 states × a boolean-ish prop).
  Recommend the `components` agent explicitly check, for any shadcn
  component whose docs page shows **no API Reference table and delegates
  entirely to native element props** (Input, Textarea): does a Figma
  "Variant" axis correspond to a real component prop, or to a native HTML
  attribute that should not multiply the state matrix?
- **A 2-stop gradient fill with identical color stops is an authoring smell
  that hides an unbound raw literal.** It renders pixel-identical to the
  bound solid fill every sibling state uses, so it's invisible on a
  screenshot diff — only caught by checking `fills[0].type` structurally.
  Recommend the `tokens`/`architecture` checks explicitly flag
  `GRADIENT_LINEAR`/`GRADIENT_RADIAL` fills with ≤2 stops of identical
  color as "should be a solid fill, currently unbound" rather than relying
  on a human noticing the visual is indistinguishable from a bound
  sibling.
- **A variable name can encode both Light and Dark resolved values plus
  opacity math directly in its name** (`custom/input\50 dark:input\80` =
  input token at 50% opacity in Light, 80% in Dark), instead of being a
  real two-mode alias in the Light/Dark collection. This is functionally
  correct but breaks the "modes live in a mode-carrying collection"
  convention the rest of the file follows, and is easy to miss because the
  variable *works* — it just isn't structured like its siblings.
  Recommend a dedicated `variables` agent check: any variable outside the
  file's designated Light/Dark collection whose name contains both a
  numeric percentage and the literal word `dark:` is a naming/architecture
  finding, independent of whether its resolved values are correct.
- **"Filled" as a distinct State value has no shadcn equivalent for
  text-input-like components** — content presence never changes Input's
  class list (only `disabled`/`aria-invalid`/`type` do). Confirmed the
  Figma "Filled" state differed from "Default" only by text color on the
  plain Input variant, and **not at all** on the File variant (same
  literal "Choose file" label in both states) — a second, independent
  signal that "Filled" is an invented state rather than a deliberate
  extension. Recommend `states` agent treat "Filled" (or similarly-named
  states with no code-side trigger) as off-spec by default for any
  text-entry component, and flag if it doesn't even visually differ from
  Default.

## 2. Real defects fixed on the Input (Figma)

- Invalid-state fill (Default/Password/File) was an unbound 2-stop
  gradient with identical `#FAFAFA` stops — replaced with a solid fill
  bound to `button/outline-bg`, matching every other state in the set.
- Height was a uniform 44px (`height/h-11`) across all 18 variants vs.
  shadcn's 32px (`h-8`) — rebound to the existing `height/h-8` variable
  (already present in the file's TailwindCSS collection, no new variable
  needed) on all 18 nodes in one pass; verified via screenshot that no
  text clipped and no auto-layout reflow broke after the resize.
- File variant had a fabricated "No file chosen" text layer with no code
  equivalent (native `<input type="file">`'s status text is
  browser-native OS chrome, not stylable, not in the DOM as a separate
  element) — removed the text node from all 6 File-state variants.
- Resting/filled border (`base/input`, `#A3A3A3` on `#FAFAFA` = 2.42:1)
  failed WCAG 1.4.11 (needs ≥3:1, and per `shadcn-baseline.md` an Input's
  own border is control-identifying, not exempt like a decorative
  Card/Separator border). Fixed with a new **Input-scoped** variable
  (`input/border`, Light rebased to `neutral/500` `#737373` → 4.54:1,
  Dark left unchanged since it already passed ~4.97:1) rather than
  rebinding the shared `base/input` token, because `base/input` is also
  consumed by Textarea and Select per the file's own theming docs — see
  §3 blast-radius note below.
- Disabled fill was bound to `custom/input\50 dark:input\80` (see §1) —
  created a proper two-mode `input/bg-disabled` variable with the same
  resolved values (Light 50%, Dark 80% opacity of `base/input`) and
  rebound the 3 Disabled-state fills to it. Left the old variable in place
  (did not delete) since its usage outside this component set was not
  verified.
- Focus ring was at 65% opacity (see §1) vs. spec's `ring-ring/50` (50%) —
  fixed via a new `input/ring-focus` variable, detaching the 3 Focus nodes
  from the shared `focus/default` effect style rather than editing that
  style directly (see §3).
- Invalid ring was at 75% opacity (`button/destructive-ring`) vs. spec's
  `ring-destructive/20` (light) / `/40` (dark) — fixed via a new
  `input/ring-invalid` variable (20%/40%), detaching the 3 Invalid nodes
  from the shared `focus/destructive` effect style.

## 3. Blast-radius discipline for live edits on a shared design-system file

This was the central operating principle for this session and is worth
generalizing into the skill's fix/remediation guidance (there currently is
none — Phase 0–4 of `SKILL.md` cover audit only, not applying fixes).

- **Before rebinding or editing any shared Variable or Effect Style, check
  how many nodes/pages reference it.** Used
  `page.findAllWithCriteria({types:[...]})` filtered by
  `effectStyleId === targetStyleId` to discover that `focus/default` had 3
  users (all on Input) but `focus/destructive` had 5, including instances
  outside the Input page — confirming the shared style genuinely is shared
  and should not be edited in place for a component-scoped fix.
- **A shared color/effect token used by more than one shadcn component
  (per the file's own "Used by" documentation, e.g. `base/input` → Input,
  Textarea, Select) should not be rebound to fix one component's
  contrast** — create a new component-scoped variable instead, even though
  this is less "clean" than fixing the token once. This mirrors the
  Button session's independent discovery that editing a shared Effect
  Style's `color.a` did not propagate reliably to attached instances —
  different platform behavior, same practical conclusion: prefer detaching
  + localizing over editing shared state, when blast radius beyond the
  audited component cannot be fully verified in the time available.
- **Presented this exact trade-off to the user explicitly** (as an
  `AskUserQuestion`, not a silent decision) before any Figma write: apply
  only the fixes with verified low blast radius vs. also apply the two
  fixes that touch shared/structural surface (global `base/input` rebind,
  and collapsing 18 variants into 6 by deleting Password/File). User chose
  the safe-only path. This 3-way framing (safe-only / all / pick-by-fix)
  is a reusable pattern for any future "apply these findings live" request
  against a real design-system file — surface the blast-radius split
  explicitly rather than assuming permission to touch shared tokens just
  because a finding recommends it.

## 4. Figma Plugin API gotchas — confirms, refinements, and one contradiction of the Button session's notes

- **Confirms Button's finding:** a shared Effect Style is risky to edit in
  place when other components/instances depend on it — this session
  avoided the problem entirely by never editing `focus/default` /
  `focus/destructive` directly, detaching per-node `effects` instead (see
  §3). `node.effects = [...]` while `effectStyleId` was previously set
  **automatically clears `effectStyleId` to `""`** — no separate detach
  call was needed; confirmed by reading `effectStyleT` back after the
  write.
- **Possible contradiction of Button's documented gotcha** ("Setting a
  paint/effect's `color.a` in the same call that first attaches a
  `boundVariables` binding snaps alpha to 1"): this session called
  `figma.variables.setBoundVariableForPaint(paint, 'color', var)` /
  `setBoundVariableForEffect(effect, 'color', var)` in a **single write**,
  passing a paint/effect object that already had the target alpha
  (0.5, 0.20, 0.8, etc.) set on its `color.a` field before calling the
  helper — and the alpha was NOT snapped to 1 in any of the ~15 paint/
  effect writes made this session (verified by reading the returned
  object back immediately after every call). Possible explanation: the
  Button session's snap-to-1 bug may specifically affect a **second**
  write that changes `color.a` on an object that was already bound in a
  prior call, not a first-time bind where the correct alpha is already
  present in the object passed to the helper. Recommendation for the next
  session that touches paint/effect alpha: always read the write's return
  value immediately to confirm the alpha stuck, regardless of which
  pattern is used — don't assume either this session's or Button's
  behavior without checking.
- **`height`/`width` are single `setBoundVariable` keys** (unlike
  `cornerRadius`, which is 4 separate keys per Button's notes) — one
  `node.setBoundVariable('height', h8Var)` call correctly resized and
  rebound all 18 variant frames.
- **Read-only variable/style introspection scripts remain essential before
  any write**, beyond what `extraction.md` already documents for
  variables: this session also needed
  `figma.getLocalEffectStylesAsync()` to catch the alpha discrepancy in
  §1, and `page.findAllWithCriteria` + `effectStyleId` matching to check
  blast radius in §3 — neither is in the current extraction reference.

## 5. Repo/workflow boundaries for this engagement

- All live component fixes were applied directly in Figma, per explicit
  user direction ("Fix them on Figma"), and scoped down via an
  `AskUserQuestion` to the safe/low-blast-radius subset only (see §3).
- The audit itself ran inside `bx-monorepo`
  (`.claude/worktrees/shadcn-figma-audit-swarm-510a26/.audit/apollo-input`)
  as scratch/output space for the skill's snapshot + findings + report —
  that worktree was not otherwise touched, and this learnings file and its
  branch belong in `shadcnui-auditor`, not `bx-monorepo`.
- No skill code (schema, `consolidate.py`, agent prompts) was modified
  this session — §1's recommendations are unimplemented proposals for a
  future pass, unlike the Button session's PR #1 which landed schema
  changes directly.

## 6. Deferred by explicit user choice (not defects left unfixed by mistake)

- `components-001` — collapsing `Variant=Default|Password|File` (18
  variants) into a single State-only set (6 variants) driven by a `type`
  prop was scoped and costed (effort `L`) but not applied; deleting the 12
  Password/File variant nodes would break any existing instance in the
  file that references them, and the user chose the safe-fixes-only path.
- The global `base/input` rebind (an alternative to the component-scoped
  `input/border` fix in §2) was explicitly not taken, since `base/input`
  is also consumed by Textarea and Select.
- `components-003` (opaque `background` fill instead of `bg-transparent`)
  and `governance-002` (Code Connect prop mapping for the State enum) were
  not part of the safe-fixes bundle and remain open in the report.

## 7. Not yet done

- The audit was **not re-run** after remediation. The Button session's
  entry ends with a fresh compliance number (75%→82%); this session's
  report.html still reflects the pre-fix 80%/NEEDS FIXES state. Re-running
  the swarm against the now-fixed Figma node is the natural next step
  before treating this component as closed out.
