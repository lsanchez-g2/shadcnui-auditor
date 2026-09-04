# shadcn/ui Figma Audit Swarm

A Claude skill that audits a Figma design system — or a single component — against the **live** shadcn/ui specification and delivers a senior-level, evidence-backed HTML report: tokens, variables, light/dark modes, WCAG contrast, states, variants, layout parity, naming, and handoff readiness.

Paste a Figma URL. One orchestrator extracts the file once, eight specialists audit it in parallel, a script merges and scores their findings, a senior reviewer writes the verdict and fix order, and a renderer produces the report.

[Overview (English)](docs/overview.md) · [Resumen (Español)](docs/overview.es.md) · [Sample report](examples/sample-report.html)

## Why

Design-to-dev handoff breaks on things nobody notices by hand: a button 44 px tall where the code says 32, a focus ring bound to a grey that isn't `ring`, a `secondary-foreground` token that exists but nothing uses, a dark mode faked in a variable's name. Finding these across 130 component sets takes days and depends on who is looking. The swarm does it in about fifteen minutes per component, the same way every time, against the spec as it is today rather than as anyone remembers it.

## How it works

```
Phase 0  orchestrator   route → pick shadcn flavor → fetch docs once → extract Figma once → snapshot/
Phase 1  8 specialists  parallel, read-only, each owns one concern, shared findings schema
Phase 2  consolidate.py validate → merge duplicates → dedupe by node+property → weighted score
Phase 3  reviewer       verdict, fix order by root cause, resolve disagreements (may lower, never add)
Phase 4  render_report  self-contained HTML: score, KPIs, fix order, findings, matrices, off-spec
```

Specialists: `tokens`, `variables`, `modes`, `contrast`, `states`, `components`, `styles`, `governance`. Each writes `findings/<agent>.json` in the contract defined in [`references/findings-schema.md`](references/findings-schema.md). A finding without evidence from the snapshot and a citation into the shadcn docs is rejected by the consolidator.

Scores are computed by code, never estimated by an agent. Component audits report a compliance percentage; system audits report a health score weighted pairing 20 · contrast 25 · mode parity 20 · architecture 20 · state/variant 15.

Verdicts: `READY FOR HANDOFF` · `NEEDS FIXES` · `BLOCKED (off-spec)` (with the cheapest unblock stated).

## Install

**Cowork / Claude desktop** — open [`dist/shadcn-figma-audit-swarm.skill`](dist/shadcn-figma-audit-swarm.skill) in a Claude conversation and click *Save skill*.

**Claude Code** — copy this repository into your skills folder:

```bash
git clone https://github.com/lsanchez-g2/shadcnui-auditor ~/.claude/skills/shadcn-figma-audit-swarm
```

Requirements: the Figma MCP connector (`get_metadata`, `get_design_context`, `get_variable_defs`, `search_design_system`, `get_screenshot`, `use_figma` read-only), web fetch for `ui.shadcn.com`, subagents (the Agent tool), and Python 3 for the scripts.

## Use

Share a Figma URL and ask for an audit. Say which shadcn flavor engineering uses — **Base UI** (current default), **Radix**, or **React Aria** — because their APIs differ.

- A URL pointing at a component set → component audit.
- A URL with no node-id, or pointing at a page with many sets → system audit.
- A page with one set, or a single variant → resolved to its set.

The skill reads variable collections, modes, and alias chains itself through a read-only `use_figma` script. If the file is view-only it asks for screenshots of the Variables panel instead and transcribes them into `snapshot/ground_truth.md`.

## Repository layout

```
SKILL.md                 orchestrator instructions (what Claude follows)
agents/                  one prompt per specialist + _common.md + reviewer.md
references/
  shadcn-baseline.md     token contract, radius scale, semantic roles, flavor differences
  extraction.md          Figma MCP → snapshot mapping, sampling rules, lessons from real runs
  findings-schema.md     the JSON contract every agent writes; scoring rules
scripts/
  consolidate.py         validate, merge, dedupe, score → merged.json
  render_report.py       merged.json + review.json → report.html
  contrast.py            WCAG 2.1 ratios with oklch parsing and alpha compositing
  make_fixture.py        synthetic audit workspace for testing (no client data)
  selftest.sh            runs the deterministic pipeline end to end
assets/report_template.html
docs/                    overview (EN/ES), origin prompt
examples/sample-report.html   rendered from the synthetic fixture
dist/                    packaged .skill
```

## Develop

```bash
scripts/selftest.sh          # fixture → consolidate → render, plus a contrast boundary check
```

Audit workspaces (`audits/`, `snapshot/`, `findings/`, `merged.json`, `review.json`) are git-ignored: they contain a client's design data. Test with the fixture, or with your own file.

When a real run teaches something, fold it into the skill rather than the conversation: MCP quirks go in `references/extraction.md`, spec changes in `references/shadcn-baseline.md`, judgment rules in the agent that owns the concern. The `Lessons from real runs` section in `extraction.md` is the record of what the first seven audits taught.

## Rules the skill will not break

- It never audits from memory. The spec is fetched every run; shadcn's own defaults have changed materially (radius scale, Button sizes, Base UI as default).
- It never guesses a value it could read. Anything unverifiable is labelled `unverified`, not scored.
- It does not invent, remove, or add. Things shadcn does not define are listed as off-spec, never folded into the score.
- Every fix is written for the person executing it: exact variable, exact value, exact layer.

## Known limits

Large component sets are sampled by axis, not inspected variant by variant, and unsampled variants are marked. Publish status is not exposed by the Figma connector. A nested component set referenced inside the audited one needs its own URL. The reviewer's separation of "brand choice" from "defect" is a judgment; the report shows the reasoning so you can overrule it.

## License

Not yet chosen — add a `LICENSE` file before making the repository public.
