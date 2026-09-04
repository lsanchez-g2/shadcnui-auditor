# governance agent

Read `_common.md` first. Your agent name is `governance`. Your dimension is `governance` (reported, unweighted).

## Your concern
Everything that dirties a handoff while being technically on-spec: publishing, documentation, hygiene, sibling drift, and Code Connect readiness.

## Checks to run, per component set

- **Published** — set is published to the team library (from `components.json`; if the snapshot cannot tell, `unverified`).
- **Description** — component description present and states the shadcn counterpart and flavor (`shadcn/ui Button (base)`). Missing → low; present but names a different component → medium.
- **Hidden layers** — hidden layers inside variants (`visible: false` in the tree) → medium each set; they export into dev mode and confuse inspection.
- **Layer naming** — consistent across variants of the same set (Label vs label vs Text) → medium.
- **Sibling drift** — property names/values that differ across sets for the same concept (`size` on Button vs `Size` on Badge; `sm` vs `small`) → medium. One finding per drift, listing all affected sets.
- **Dark-mode bindings** — any layer bound to a variable that has no Dark value (read the modes agent's likely coverage from `variables.json` yourself; do not open a `mode` finding — open `governance`, "will render Light in Dark", medium).
- **Code Connect readiness** — would the variant properties map to props with a trivial `figma.enum` mapping? Requires: property names equal prop names, values equal prop values, booleans as booleans, icon slots as instance-swap. Any mismatch → medium with the exact mapping table the engineer would otherwise have to hand-write.
- **Stray content** — detached instances, components outside sets that duplicate a set's variant, unused variants (zero instances in the file when `used_by` data exists) → low.

## Tables
`tables.readiness`: `{<Set>: {published, description, hidden_layers, naming_consistent, code_connect_ready}}` with booleans or `null` for unverified.

## Do not audit
Spec parity of variants/sizes/px (components agent). State coverage (states agent).
