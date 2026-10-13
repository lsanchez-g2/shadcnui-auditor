# Extraction: Figma MCP → snapshot/

The orchestrator runs every Figma call. Specialists only read the files described here. Save raw tool output next to each normalized file (`*.raw.txt`) — findings must cite raw output as evidence, and the reviewer may need to re-read it when two specialists disagree.

## Directory

```
<audit dir>/
  snapshot/
    meta.json
    variables.json        (+ variables.raw.txt)
    styles.json           (+ styles.raw.txt)
    components.json       (+ components.raw.txt)
    nodes/<node-id>.json  (+ nodes/<node-id>.raw.txt)  one per component set in scope
    screenshots/<node-id>.png
    spec/theming.md, spec/components/<name>.md, spec/spec.json
  findings/               written by specialists
  merged.json, review.json, report.html   written by phases 2–4
```

## meta.json

```json
{
  "file_key": "…", "file_name": "…", "root_node_id": "…", "mode": "system|component",
  "flavor": "base|radix|aria", "audited_at": "ISO-8601",
  "docs_fetched": ["https://ui.shadcn.com/docs/theming", "…"],
  "in_scope_components": [{"name": "Button", "node_id": "12:34"}],
  "scope_note": "system mode only: one sentence on what was and was not inventoried"
}
```

`in_scope_components` is always a list of `{name, node_id}`; in system mode list the sets you sampled in depth (or an empty list) and put the prose in `scope_note` — the report renders both.

## Calls and where their output goes

| Call | On | Writes | Normalize to |
|---|---|---|---|
| `get_metadata` | root node | `nodes/<id>.json` (tree), `components.json` (list) | For every COMPONENT_SET: name, node_id, variant property names and their values, child component names. For every COMPONENT: name, node_id, parent set, property definitions (type: variant/boolean/text/instance-swap), layer tree with names, visibility, type. |
| `get_variable_defs` | root node (and per component set if root output is truncated) | `variables.json` | `collections[]` → `{name, modes[], variables[]}`; each variable → `{name, type, scopes, values_by_mode: {Light: "#hex" | "{alias/name}", Dark: …}, resolved_by_mode: {Light: "#hex", Dark: "#hex"}, alias_of: name|null, used_by: [node_ids]}` when available. Preserve the raw name exactly — naming is audited. |
| `get_design_context` | each component set in scope | merged into `nodes/<id>.json` | Per variant: auto-layout on/off, direction, padding (t/r/b/l), gap, width/height (fixed/hug/fill), corner radius (per corner if mixed), fills/strokes/text with bound variable or style name or raw hex, typography (family, weight, size, line-height), effects, opacity, bound variables per property. |
| `search_design_system` | queries: component names in scope, "foreground", "radius", "sidebar", "chart" | append to `components.json` / `variables.json` | Catches near-miss names in other collections so "missing" findings are checked against the whole library, not only the root node. |
| `get_screenshot` | each component set in scope | `screenshots/<id>.png` | Visual reference only. Specialists may cite it for state rendering. |

If a call returns truncated output, split by component set and merge. Note truncation in `meta.json.notes`.

## Normalization rules (so every specialist sees the same shape)

- Colors: keep the raw Figma value **and** add `hex` (6-digit, uppercase) plus `alpha` (0–1). Do not round alpha.
- Radius, padding, gap, sizes: numbers in px.
- Typography: `{family, style, weight, size, line_height}` with line-height in px (or `"auto"`).
- Variable references: `alias_of` uses the full variable path as Figma shows it (`color/semantic/primary`), never a shortened form.
- Layer paths: `Set / variant=…, size=… / Layer / Sublayer` — this becomes `layer_path` in findings.
- Never resolve or "clean" names. A specialist auditing naming needs to see `btn/primary CTA` exactly as authored.

## Lessons from real runs (read before extracting)

**Identifying the set.** The metadata XML labels a component set `<frame>`; what identifies it is that its direct children are `<symbol>` elements named `Prop=Value, Prop=Value`. A URL's `node-id` may be the page, a section, the set, or one variant — call `get_metadata` and look for the `<symbol>` parent. A page's metadata can exceed 100KB and is then saved to a host temp file; do not try to read it whole — grep it for `<symbol ` and take the enclosing element.

**Large results saved to a file.** When any MCP result is "saved to" a `/var/folders/...` path, that file is on the host: the Linux shell cannot see it, Read refuses it above ~25k tokens, and Grep omits lines longer than its cap (the whole result is one line). Recovery: grep for the specific tokens you need (`<symbol `, `data-node-id=`, a variable name) with `-o` and bounded context, or re-issue the call on smaller nodes. Prefer never to trigger it: do not call `get_design_context` on a set with more than ~20 variants.

**Sampling a large set.** Per-variant `get_design_context` calls return ~2–4k tokens each and always work. Pick the sample by axis, not by Button habits: for every variant property, take every value with all other properties at their defaults; then take the full state row (every State value) for the default variant at the default size; then add the cells where the spec says something changes (hover on ghost/outline, focus on destructive, checked on toggles, invalid on inputs). Record the sample list and the count of unsampled variants in `meta.json.notes`; agents must mark claims about unsampled variants `unverified`. If the set has ≤ 20 variants, sample all of them.

**`get_variable_defs` is flat — use `use_figma` for structure.** `get_variable_defs` returns `name → resolved value` for the current mode with no collection, mode, alias, or scope data. The full picture comes from a **read-only** `use_figma` script (load the `/figma-use` skill or the `skill://figma/figma-use/SKILL.md` resource first, as the tool requires). One script, run per collection to stay under the ~20 KB return cap:

```js
// read-only: enumerate one collection with per-mode values and alias chains
const cols = await figma.variables.getLocalVariableCollectionsAsync();
const col = cols.find(c => c.name === COLLECTION_NAME);          // pass the name in
const modes = col.modes.map(m => ({ id: m.modeId, name: m.name })); // note: modeId, not id
const out = [];
for (const id of col.variableIds) {
  const v = await figma.variables.getVariableByIdAsync(id);
  const vals = {};
  for (const m of modes) {
    const raw = v.valuesByMode[m.id];
    vals[m.name] = raw?.type === 'VARIABLE_ALIAS'
      ? { alias: (await figma.variables.getVariableByIdAsync(raw.id))?.name }
      : raw;
  }
  out.push({ name: v.name, type: v.resolvedType, scopes: v.scopes, description: v.description, values: vals });
}
return { collection: col.name, modes: modes.map(m => m.name), variables: out };
```

Write the result to `variables.json` in the shape this reference defines (`values_by_mode`, `alias_of`, `scopes`) and set `modes_exposed: true`. Chunk by collection; for a 500-row primitives collection, page `variableIds` in slices of ~150. Component metadata comes the same way: `node.componentPropertyDefinitions`, `node.description`, `node.documentationLinks` on each component set. A script that only reads is safe to run against a client file; never call anything that mutates (`create*`, `set*`, `remove`, `.name =`).

When `use_figma` is unavailable (no desktop connection, or the file is view-only), fall back to the user's Variables-panel screenshots → `ground_truth.md`. Variable names alone are never evidence about mode cells — a `dark:` inside a name is a naming finding, nothing more.

**A node whose family maps to more than one shadcn sub-component needs a live structural probe, not just `get_design_context`.** `get_design_context` reconstructs JSX from the render tree; it cannot show `componentPropertyReferences` (which instance property actually drives a nested part), `strokeAlign` (`OUTSIDE` vs `INSIDE`/`CENTER` — the difference between a border that adds to the box and one that doesn't), or auto-layout `itemSpacing`/`layoutPositioning` (`AUTO` vs absolute). A real audit (Avatar) called three "architecture" findings on exactly this gap — a nested badge, group wrapper, and count part all looked wrong in the reconstructed JSX but were correct in the live node. So: whenever a component set's children include a nested or sibling badge, group, or count part (i.e. its shadcn mapping is more than one sub-component), run this **read-only** `use_figma` probe on the set's default variant in addition to `get_design_context`, not instead of it:

```js
// read-only: structural facts get_design_context cannot show
const node = await figma.getNodeByIdAsync(NODE_ID);
const probe = (n) => ({
  name: n.name,
  type: n.type,
  strokeAlign: n.strokeAlign ?? null,
  layoutMode: n.layoutMode ?? null,
  itemSpacing: n.itemSpacing ?? null,
  layoutPositioning: n.layoutPositioning ?? null,
  componentPropertyReferences: n.componentPropertyReferences ?? null,
  componentPropertyDefinitions: n.componentPropertyDefinitions ?? null,
  children: (n.children ?? []).map(probe),
});
return probe(node);
```

Store the result as `nodes/<id>.json.structural_probe` (a sibling key to the `get_design_context`-derived fields, never a replacement). Findings in the `architecture` category on a multi-sub-component node must cite `structural_probe`, not the reconstructed JSX alone — a claim about linked properties, border placement, or auto-layout spacing sourced only from `get_design_context` is `unverified`.

**`get_metadata` without a node-id truncates the page list** (a real file returned 31 of 83 pages with no warning). Verify with the read-only script `return figma.root.children.map(p => ({id: p.id, name: p.name}))` and reconcile before declaring anything absent. If a component is on none of the listed pages, audit the node directly and record `parent_page: unknown`.

**`search_design_system` is one query per call** — the tool advertises a `queries` array but the server clamps it to one; do not batch. It exposes `variableCollectionName`, `description`, library `updatedAt`, and sometimes `scopes` (present for `base/*`, absent for some groups) — useful as a cross-check on `use_figma` output and as the closest thing to a publish signal. It returns `componentKey`, never a node id, so a nested set found this way (an icon set instanced inside the audited component) cannot be pulled into the snapshot; record it as `referenced_sets` in `components.json`, mark its checks unverified, and ask the user for its URL. Results include sibling libraries that publish the same token names; keep only hits whose library is the audited file.

**`get_screenshot` returns a short-lived URL**, not bytes. Download it with `curl -L -o snapshot/screenshots/<id>.png "<url>"` from bash. It renders the current mode only (usually Light) — say so in `meta.json` so the modes agent does not treat it as Dark evidence.

**Fetching the spec — use the shared cache.** Raw fetched text goes to `<outputs>/spec-cache/<YYYY-MM-DD>/<url-as-filename>` the first time any audit fetches it; every audit's `snapshot/spec/` is then populated by copying from today's cache. This solves two failures seen in real runs: a later audit inheriting a *summary* someone wrote instead of the page (so: the cache holds only raw fetch output, never notes), and the fetch tool answering "already fetched this session" with no content to an agent that never saw the first fetch (so: check the cache before fetching, and if the tool still returns nothing, add a harmless query string like `?audit=<timestamp>` to get a fresh copy). `theming.md` and `components/<name>.md` must be page content because agents cite anchors from them. The docs page hides the `cva` class strings behind "View Code"; the registry item `https://ui.shadcn.com/r/styles/<style>/<component>.json` (default style `base-nova`) has the source — save it as `components/<name>.registry.json`. Composite components (Dialog, Card sections) legitimately have no `cva`; their contract is the `data-slot` names and class strings per slot.

**System mode spec fetching.** Do not fetch docs for 130 sets. Fetch theming once, the registry JSON for every set whose name maps to a shadcn component (cheap, one call each, gives the `cva`), and docs pages only for the sets you will sample in depth. Record the mapping `figma set → shadcn name | none` in `spec/spec.json.mapping`.

**Components with no API table.** Some base-flavor pages (Switch, Checkbox, Card…) defer props to Base UI and show no `variant`/`size` rows. That is not a stub fetch. Derive the API from the registry source (`cva` variants, `data-slot` names, `data-*` attributes) and, when props matter, fetch the primitive's page at `https://base-ui.com/react/components/<name>` and save it as `components/<name>.primitive.md`. Record which source the API came from in `spec.json`.

**Component descriptions and doc links are exposed** in `get_design_context` output (the "Component descriptions" block). Capture them into `components.json`; the governance agent needs them. Publish status is not exposed — `search_design_system` returning the set from the library is the closest proxy; otherwise mark it unverified.

**Reusing `ground_truth.md`.** It covers only the collection groups the user photographed. Write which groups it does *not* cover at the top (e.g. `custom/*`, `alpha/*`), and when `variables.json` shows names from an uncovered group, ask the user for that group's screenshot before treating those variables' modes as unknown-forever.

## Ground truth from the user (fills what the MCP cannot see)

`get_variable_defs` hides collections, modes, and alias targets — the three things the modes and variables agents need most. Ask the user for screenshots of the Variables panel (the collection holding the semantic tokens, Light and Dark columns visible, alias chips legible). Transcribe them into `snapshot/ground_truth.md`: collections with counts and modes, then one line per row `token → light alias → dark alias`, marking anything odd (identical in both modes, dark aliasing a `-light` value, semantic aliasing a raw primitive, missing mode suffix, name mismatch between tiers). Note which rows the screenshots did not cover.

Agents treat `ground_truth.md` as snapshot data: a check it settles moves from `unverified` to pass/fail, with `evidence` citing "ground_truth.md: <row>". Ask for it in the first message of a system-level audit; for a component audit ask when the first run comes back with mode/alias checks unverified — the user is more willing once they see the gap.

## Component mode

Same calls, one component set. Still run `get_variable_defs` on the root and `search_design_system` for the component name — a token the component appears to be missing may exist elsewhere in the library.
