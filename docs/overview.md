# shadcn/ui Figma Audit Swarm — what it is and how it works

## In one sentence

Paste a Figma URL, get back a senior-level audit of how closely that design system (or one component) matches shadcn/ui — tokens, light/dark modes, contrast, states, variants, layout, naming — as an interactive HTML report with a score, a prioritized fix list, and evidence for every finding.

## Why it exists

Design-to-dev handoff breaks when Figma and the shadcn code disagree in ways nobody notices: a button that is 44px tall where the code says 32, a focus ring bound to a grey that isn't `ring`, a `secondary-foreground` token that exists but nothing uses, dark mode faked through variable names. Finding these by hand across 130 component sets takes days and depends on who is looking. The skill does it in about 15 minutes per component, the same way every time, against the live spec rather than anyone's memory of it.

## How it works

One orchestrator and eight specialists, each owning a single concern, plus a senior reviewer and two scripts.

**Step 1 — extract once.** The orchestrator identifies what the URL points to (a whole file, a page, a component set, or a single component), fetches today's shadcn documentation and the component's actual source code from the shadcn registry, and pulls the Figma data through the Figma MCP connector: variables with their light/dark values and alias chains, styles, component properties, and a sample of variants with their measured padding, heights, fonts, and bound tokens. Everything is written to a snapshot on disk. Nothing downstream touches Figma or the web again, so all eight specialists reason from identical data.

**Step 2 — eight specialists in parallel.** Tokens (is the semantic token set complete and paired, is radius derived from one base, are tokens used for their documented role). Variables (primitive → semantic → component tiers, raw values where aliases belong, orphans, broken aliases, wrong scopes). Modes (does every token have a deliberate value in both Light and Dark). Contrast (WCAG 2.1 ratios for every surface/foreground pair, computed by a script with alpha compositing and oklch support, never estimated). States (the variant × state matrix, one state convention per library, focus rings that actually use `ring`). Components (1:1 parity with the shadcn API: names, variants, sizes, measured px versus the Tailwind classes, anatomy, props). Styles (text and effect styles versus Tailwind classes, styles that duplicate variables). Governance (descriptions, doc links, hidden layers, naming drift between siblings, Code Connect readiness). Each writes findings in one shared format; a finding without evidence from the snapshot and a citation into the shadcn docs is rejected.

**Step 3 — consolidate by code, not opinion.** A script validates every findings file, merges duplicates (eight agents describing the same focus ring in eight sentences become one finding credited to all eight), flags disagreements, and computes the score. Component audits get a compliance percentage. System audits get a weighted health score: pairing 20%, contrast 25%, mode parity 20%, architecture 20%, state/variant coverage 15%. Because the number comes from code, two runs on the same file give the same number.

**Step 4 — senior review.** A reviewer reads the merged findings, resolves the disagreements, writes the verdict and the fix order grouped by root cause (one missing token → six unbound layers → one fix), and separates real defects from deliberate brand choices that happen to differ from shadcn. It can lower a finding's severity with a stated reason. It cannot add findings or raise severities — a specialist's evidence always outranks the reviewer's judgment.

**Step 5 — the report.** A self-contained HTML page: verdict and score, top issues, fix order with effort estimates, every finding with current value / expected value / exact fix / evidence / docs link, the contrast matrix with the math shown, coverage matrices, what is already compliant (so nobody "fixes" it), and an off-spec inventory of things shadcn doesn't define at all.

## Rules it will not break

It never audits from memory; the spec is fetched every run because shadcn's own defaults have changed materially (radius scale, button sizes, Base UI as the default flavor). It never guesses a value it could read; anything it cannot verify is labelled unverified rather than scored. It does not invent, remove, or add: things outside the shadcn spec are listed as off-spec, never folded into the score. Every fix is written for the designer who will execute it — exact variable name, exact value, exact layer.

## Verdicts

- **READY FOR HANDOFF** — no critical or high findings, compliance ≥ 90%.
- **NEEDS FIXES** — the normal case; work through the fix order.
- **BLOCKED (off-spec)** — the component's API surface has variants or properties shadcn doesn't define and nobody has documented them as intentional. The report states the cheapest unblock, which is usually a one-line component description.

## What it has been run on so far

A production design system (one client, seven runs): Button, Card, Switch, Checkbox, Input, Dialog (component mode, 75–84% compliance) and the whole file (system mode, health 76/100 across 130 component sets, 1,999 checks). Recurring findings across the library: focus rings bound to a neutral grey instead of `ring`; every component one Tailwind size step larger than base-nova; `primary` not stepping between Light and Dark; 26 `custom/*` variables named as Tailwind class strings holding raw hex.

## What it needs from you to run

A Figma URL (file, page, or component), the Figma MCP connector enabled, and which shadcn flavor engineering uses (Base UI, Radix, or React Aria — the APIs differ). It reads the variable structure itself; if the file is view-only it asks for screenshots of the Variables panel instead.

## Known limits

Large component sets are sampled (every axis value at defaults plus the full state row), not inspected variant by variant; unsampled variants are marked as such. Publish status isn't exposed by the Figma connector. A nested component set referenced inside the audited one needs its own URL. And the reviewer's judgment about "brand choice vs defect" is a judgment — the report shows its reasoning so you can overrule it.
