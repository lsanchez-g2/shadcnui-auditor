# shadcn/ui baseline contract

This is what you *expect* to find on the live docs. It exists so you can (a) tell whether a fetch returned real content, and (b) build `snapshot/spec/spec.json` in a stable shape. The fetched page always wins over this file.

## Theming page — https://ui.shadcn.com/docs/theming

### Core pairs (surface + `-foreground`)
`background`, `card`, `popover`, `primary`, `secondary`, `muted`, `accent`

### Standalone
`destructive` (no `-foreground` in the current default theme; a `destructive-foreground` variable indicates a legacy theme — record as `legacy`, not as an error), `border`, `input`, `ring`

### Charts
`chart-1` … `chart-5`

### Sidebar
`sidebar`, `sidebar-foreground`, `sidebar-primary`, `sidebar-primary-foreground`, `sidebar-accent`, `sidebar-accent-foreground`, `sidebar-border`, `sidebar-ring`

### Radius scale (multiplicative, single base)
| token | factor |
|---|---|
| radius-sm | 0.6 |
| radius-md | 0.8 |
| radius-lg | 1.0 |
| radius-xl | 1.4 |
| radius-2xl | 1.8 |
| radius-3xl | 2.2 |
| radius-4xl | 2.6 |

Default `--radius: 0.625rem` (10px) → 6 / 8 / 10 / 14 / 18 / 22 / 26 px. Older docs used `calc(var(--radius) - 2px)`; if the fetched page shows the additive form the project is on a legacy scale — record which one you found in `spec.json.radius.mode`.

### Semantic roles ("Used by" column)
- `accent` — hover/focus/active surfaces: ghost buttons, menu highlights, hovered rows, selected items
- `muted` — subdued surfaces, low-emphasis text: descriptions, placeholders, empty states, helper text
- `secondary` — lower-emphasis filled actions
- `primary` — high-emphasis actions, selected states, badges
- `input` — form-control borders (distinct from `border`)
- `border` — default borders and separators
- `ring` — focus rings
- `popover` — floating surfaces (Popover, DropdownMenu, ContextMenu)
- `card` — elevated surfaces

### Default values
Authored in oklch. Dark-mode `border` = `oklch(1 0 0 / 10%)`, `input` = `oklch(1 0 0 / 15%)`, `sidebar-border` = `oklch(1 0 0 / 10%)`. Figma stores rgb/hex: convert before comparing, composite alpha over the actual backdrop before any contrast ratio.

### Extension pattern ("Adding New Tokens")
A custom token is valid when it is defined in both `:root` and `.dark` and follows the pair convention (`warning` / `warning-foreground`). Anything else custom is off-spec.

## Component pages — https://ui.shadcn.com/docs/components/<flavor>/<name>

Flavors: `base` (default; un-prefixed URLs redirect here), `radix`, `aria`. APIs differ. Examples of what changes:

| concern | base | radix |
|---|---|---|
| open/closed | `data-open` / `data-closed` | `data-state="open|closed"` |
| checked | `data-checked` / `data-unchecked` | `data-state="checked|unchecked"` |
| pressed | `data-pressed` | `data-state="on|off"` |
| disabled | `data-disabled` | `disabled` / `data-disabled` |

Always take the exact attribute names from the fetched code of the chosen flavor.

### What to extract per component into `spec.json.components[<name>]`
- `variants`: from the API Reference table (e.g. Button: default, outline, ghost, destructive, secondary, link)
- `sizes`: from the API Reference table (e.g. Button/base: default, xs, sm, lg, icon, icon-xs, icon-sm, icon-lg — note this is longer than the older sm/default/lg/icon list)
- `states`: hover, focus-visible, active, disabled, plus component-specific data-attributes from the code
- `anatomy`: sub-components (e.g. Card → Header, Title, Description, Content, Footer, Action)
- `classes`: the `cva` class strings per variant/size, so specialists can derive px

### Tailwind class → px (Tailwind v4 defaults, 1 unit = 4px)
Heights: `h-6`=24, `h-7`=28, `h-8`=32, `h-9`=36, `h-10`=40, `h-11`=44, `h-12`=48. Sizes: `size-3`=12, `size-3.5`=14, `size-4`=16, `size-5`=20, `size-6`=24, `size-7`=28, `size-8`=32, `size-9`=36. Spacing: `p/px/gap-0.5`=2, `-1`=4, `-1.5`=6, `-2`=8, `-2.5`=10, `-3`=12, `-4`=16, `-6`=24; `--spacing(n)` = n×4. Type: `text-xs`=12/16, `text-sm`=14/20, `text-base`=16/24, `text-lg`=18/28, `text-[0.8rem]`=12.8; `leading-none`=1, `leading-snug`=1.375, `leading-normal`=1.5; `font-medium`=500, `font-semibold`=600. Rings/borders: `ring-1`=1, `ring-3`=3, `ring-[3px]`=3, `border`=1. Radius: `rounded-sm`=radius×0.6, `rounded-md`=×0.8, `rounded-lg`=×1.0, `rounded-xl`=×1.4, `rounded-2xl`=×1.8, `rounded-full`=9999. Arbitrary values (`h-[18.4px]`, `rounded-[min(var(--radius-md),10px)]`) are literal — copy the number from the class. `opacity-50`=50%.

### Component-specific traps (found in real audits — check the fetched source, these change)
- **Card** (base-nova): spacing is one root variable `--card-spacing` (`py-(--card-spacing)` on root, `px-(--card-spacing)` on sections, default `--spacing(6)`=24, `size=sm` → `--spacing(4)`=16). The Figma file may put padding on each section instead; compare the *derived inset*, not the layer it lives on. Root uses `ring-1 ring-foreground/10` (no `border`), `rounded-xl`, `text-card-foreground`; title uses `leading-snug`. Anatomy: Card, CardHeader, CardTitle, CardDescription, CardAction, CardContent, CardFooter (`data-slot` names).
- **Switch / Checkbox / Radio** (base): the docs page has no prop table — props come from Base UI. State attributes are `data-checked`, `data-unchecked`, `data-indeterminate`, `data-disabled`, `data-readonly`, `data-focus-visible`; there is no pressed state. Sizes are only what the registry `cva` defines (Switch has `size: default|sm`; Checkbox has none).
- **Non-interactive components** (Card, Separator, Skeleton, Badge without `render`): no hover/focus/disabled expectations exist. States and contrast agents log size × default only.

### Contrast exemptions the spec itself relies on
`border` (light `oklch(0.922 0 0)` ≈ 1.26:1 on white), `ring-foreground/10`, and `input` are decorative separators in shadcn's own theme and do not meet 3:1. WCAG 1.4.11 applies only to boundaries needed to identify a control or its state. So: a Card/Separator border below 3:1 is *not* a finding (record `exempt: true`, reason "decorative per spec"); an Input's border, a Checkbox's unchecked box outline, or a focus ring below 3:1 *is* (they identify a control or state). Say which case applies in `evidence`.

### State conventions (canonical — values below are base-nova as of 2026-09; the fetched `cva` wins)
- Filled buttons: hover via opacity modifier (`hover:bg-primary/80`), not a hover token
- Ghost / outline buttons: hover via `muted` in base-nova (`hover:bg-muted hover:text-foreground`); menu items and hovered rows still use `accent`
- Disabled: `disabled:opacity-50 disabled:pointer-events-none`
- Focus: `focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50`
- Invalid: `aria-invalid:border-destructive aria-invalid:ring-3 aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40`
- Active: `active:translate-y-px` (geometry, no colour token)
- Other base-nova examples that differ from older docs: Button `rounded-lg`, sizes h-6/h-7/h-8/h-9 (xs/sm/default/lg), destructive is tinted (`bg-destructive/10 text-destructive`); Badge has `ghost` and `link` variants, `h-5 rounded-4xl`; Toggle sizes `default|sm|lg`. Treat every number in this file as an example of the *shape* of the check, never as the expected value.

Dedicated state tokens (`primary-hover`, `primary-disabled`/`primary-disabled-foreground`) are legitimate extensions if paired and mode-complete. A file must use one convention. Mixing is a finding.

## Sanity check for a healthy fetch
A real theming page contains the strings `Radius Scale`, `Adding New Tokens`, `--radius-2xl`. A real component page contains `Installation` and `Usage` sections and at least one example; many base-flavor pages have **no** `API Reference` table because props are delegated to Base UI — that is normal, not a stub. The registry item (`/r/styles/<style>/<name>.json`) must contain a `files[0].content` with `cva(` or `data-slot=` — if it does not, you fetched the wrong style or name. Retry once, then stop and report.
