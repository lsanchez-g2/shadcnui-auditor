# Learnings — Apollo v2 (SA) Button Audit & Remediation

Session notes from auditing and remediating the Apollo Button component
(Figma file `3401ZFUHoboOwA6GGjAEsq`, node `37:931`, "Apollo v2 (SA) Design
System") against the `shadcnui-auditor` skill. Captured here so the next
audit — of this component or any other — doesn't rediscover the same traps.

## 1. Auditor discipline improvements (landed in `fix/apollo-button-audit-remediation`, PR #1)

The original audit report over-claimed certainty in several places. The
schema and agent prompts were tightened so a finding can't assert more than
the evidence supports:

- **Absence ≠ evidence of absence.** A variable/mode/state not found in a
  sampled subset must not be reported as "does not exist anywhere in the
  file." Added `evidence_scope` (`component` / `global` / `not_applicable`)
  so a finding states plainly whether it was checked file-wide or only on
  the audited component.
- **Alias vs. hardcoded claims need proof, not name-guessing.** A variable
  named `base/ring` is not proof it's aliased to anything — it could be a
  raw value with a semantic-sounding name. Added `alias_status`
  (`aliased_verified` / `aliased_target_unknown` / `not_aliased_verified` /
  `unknown`), which forces the agent to actually walk the `VARIABLE_ALIAS`
  chain before asserting binding status.
- **Mode claims need real cell values.** "Works in Dark mode" based on the
  variable's *name* containing "dark" is not verification. Added
  `mode_evidence` (`cell_values` / `name_inference` / `not_applicable`),
  enforced independently of category via a `MODE_RENDER_CLAIM` regex in
  `consolidate.py --strict` — any finding text matching a mode-parity claim
  must carry `cell_values` evidence or it fails the strict check.
- **Sampling ≠ exhaustive.** "All 264 variants comply" is a different claim
  from "the 12 sampled variants comply." Added a 3-state `confidence`
  (`verified` / `inferred` / `unverified`) plus a separate `sample_scope`
  (`exhaustive` / `sampled`), enforced via a `UNIVERSAL_VARIANT_CLAIM` regex
  independent of the confidence value — you can be "verified" on a sample
  and still must say so.
- **shadcn is a reference, not ground truth.** Apollo is its own design
  system built on shadcn's structure; not every difference from shadcn
  Base/New York is a defect. Added a reviewer-only `divergence_status` on
  `review.json`, with an `accepted_divergences` list and a recomputed
  adjusted-vs-raw compliance score (`scripts/_scoring.py`) so a legitimate,
  confirmed brand decision doesn't keep tanking the score on every re-run.

See `references/findings-schema.md`, `scripts/consolidate.py`,
`scripts/_scoring.py`, and `agents/*.md` for the actual mechanics; 26 new
regression tests live in `tests/test_regression.py`.

## 2. Real defects fixed on the Button (Figma)

- Focus ring wasn't reliably bound to `base/ring`; on Default/Destructive it
  visually collided with the fill/border color even though the token was
  technically correct, because both `base/ring` and `base/primary` resolved
  to the same hex. Fixed by adding a proper background-colored ring-offset
  (2px, drawn *outside* the button) **only** on the two variants where the
  literal ring color collides with the variant's own border/fill color
  (Default, Destructive). Secondary/Outline/Ghost/Link keep a plain
  `base/ring`-bound 1px inside stroke, matching their own rest-state border
  — no ring-offset needed there, since there's no color collision.
- Secondary variant's icon-size buttons used `foreground` while the
  non-icon sizes used `secondary-foreground` for the label/icon color —
  inconsistent token usage across sizes of the same variant. Unified on
  `secondary-foreground`.
- Corner radius across all 264 variants was a mix of literal numbers and
  partial bindings. Rebound to the shared radius variable on all four
  corner keys (see gotcha below — `cornerRadius` isn't one key).
- Outline/Ghost had no dedicated hover/active tokens (hover reused rest
  colors or hardcoded values); added proper token bindings for both states.
- `custom/*` variables had inconsistent/legacy names; renamed to match the
  current API.
- Component property values used mixed-case / non-API-matching strings
  (e.g. `Default` vs `default`); renamed to lowercase to match the actual
  component API consumed by code.
- `base/border` (global token) failed contrast in one theme; fixed via the
  shared `colors/border-light` intermediate variable rather than a
  component-local override, since the finding was file-wide, not
  Button-specific.
- Padding and typography had drifted from the spec on a couple of sizes;
  corrected **and bound to existing tokens** (`spacing/2`, `spacing/2-5`,
  and existing named text styles `text-xs/leading-normal/semibold`,
  `text-sm/leading-normal/semibold`) rather than left as raw numbers — see
  §4, this was a hard user correction mid-session.
- Destructive/Default fill+text retinted per the shadcn reference spec;
  confirmed with the user as the final, intentional choice (kept even after
  a later question about why it looked different from before — user's
  explicit call: "déjalo así como está, no cambies nada").

## 3. Confirmed intentional Apollo divergences (do NOT normalize to shadcn)

- **Outline variant's border is Apollo's own purple (`base/primary`), not a
  neutral border color like shadcn's Outline.** An early pass "fixed" this
  by rebinding it to a neutral border token, which the user caught
  immediately ("antes tenia un outline de color primary, ahora no, ¿por
  qué?") — reverted. This is a deliberate brand distinction, not a bug.
  Lesson: a visual difference from the shadcn reference is not
  automatically a defect — confirm intent before "fixing" anything that
  changes a variant's visual identity, even if it looks like a plausible
  alignment to spec.
- Not every variant needs the same focus-ring *technique* even though they
  should all look visually consistent — Default/Destructive need the
  ring-offset construction, others don't (see §2). Don't over-apply a fix
  that was only needed for a subset of variants to the whole set.

## 4. The one rule the user had to repeat: always bind to a real token

> "veo que no has asignado variables ni semánticos a los cambios, la
> instrucción dice que sí. siempre tienes que asignar variables, nada
> hardcoded."

Concretely: when a numeric/color value is corrected, search for an
*existing* variable or text style that already represents that value and
bind to it (`setBoundVariable`, or `textStyleId` for typography) — never
leave the corrected value as a raw literal, even temporarily, even if the
number matches. If no existing token fits, that's itself a finding to
surface (missing token), not license to hardcode.

## 5. Figma Plugin API gotchas hit repeatedly

- **Setting a paint/effect's `color.a` in the same call that first attaches
  a `boundVariables` binding snaps alpha to 1.** Hit 3 times (ring color,
  a shared effect style, a set of detached per-node effects). Workaround:
  two separate writes — first bind the variable (alpha wrong immediately
  after), then a second write that touches *only* `color.a` on the
  already-bound paint/effect. The alpha sticks on the second write.
- **Editing a shared EFFECT STYLE's nested `color.a` does not propagate to
  node instances that already have that style attached** — confirmed via
  `getStyleByIdAsync` showing the corrected value while every attached
  node's own `.effects` read still showed the old value, even after
  explicitly detaching and reattaching `effectStyleId`. No fix found within
  the shared-style model. Workaround adopted: detach the nodes and set
  independent per-node `effects` arrays instead of relying on the shared
  style. This is a real platform limitation — worth flagging early if a
  future audit needs to bulk-edit a shared effect style's alpha.
- **`cornerRadius` is not one boundVariable key.** It binds via four
  separate keys: `topLeftRadius`, `topRightRadius`, `bottomLeftRadius`,
  `bottomRightRadius`. Binding "corner radius" means binding all four.
- **Renaming a component property only renames the property-name prefix,
  not its variant option values.** `componentSet.editComponentProperty(name,
  {name: newName})` updates the property key in every child's name string
  automatically, but if the *values* of that property also need renaming
  (e.g. `Default` → `default`), each child's `.name` string has to be
  edited individually — there's no bulk rename for option values.
- **Auto-layout hug-height regression is easy to trigger silently.** A
  frame with `counterAxisSizingMode: 'AUTO'` recalculates its height from
  content the moment a child's `lineHeight` changes. Changing a label's
  text style shrank one button's height (44→36) because that one node
  hadn't been converted to `FIXED` sizing like its 29 siblings. Always
  check `primaryAxisSizingMode`/`counterAxisSizingMode` on every affected
  node before editing typography on auto-layout frames, and set
  `counterAxisSizingMode='FIXED'` + explicit `resize()` where the frame
  must not reflow.
- **Cross-collection alias resolution needs the alias's own collection and
  mode, not the mode you started with.** Resolving a value where the alias
  chain crosses from "3. Mode" (Light/Dark) into "2. Theme" (single
  "Default" mode) by reusing the Dark modeId returns `undefined` — "2.
  Theme" has no Dark mode. Fix: at every hop of an alias chain, look up
  that variable's *own* collection and its own matching (or sole) mode ID,
  never assume the mode carries over unchanged.
- **Fonts must be loaded before mutating text properties on existing
  nodes.** `await figma.loadFontAsync({family, style})` before setting
  `fontSize`/`lineHeight`/`textStyleId`, or the mutation silently no-ops or
  throws depending on node state.

## 6. Repo/workflow boundaries for this engagement

- `shadcnui-auditor` (`~/.claude/skills/shadcnui-auditor`) is the only repo
  the user authorized branching/committing in for this work; PR #1
  (`fix/apollo-button-audit-remediation`) carries the schema/script/prompt
  remediation.
- `bx-monorepo` was explicitly declared out of scope mid-session and must
  not be touched in any way going forward, including not reverting commits
  already made there earlier in the session.
- All component-level fixes for this audit were applied live and directly
  in Figma (not in code), per explicit user direction ("por ahora, arregla
  solo lo del archivo Figma").

## 7. Deferred by explicit user choice (not defects left unfixed by mistake)

- `states-001` — adding a `State=Invalid` variant axis (48 new variants)
  was scoped but not applied; user chose not to take this on in this pass.
- The Outline/Ghost hover-color-to-`muted` change ("10b") was also left
  undone by the user's own selection when choosing which batch of fixes to
  apply.

Re-running the full audit after remediation: compliance moved from 75%
(2 critical findings) to 82% (0 critical findings).
