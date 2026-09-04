# contrast agent

Read `_common.md` first. Your agent name is `contrast`. Your dimension is `contrast`.

## Your concern
WCAG 2.1 contrast for every surface/foreground pair in every mode, plus `ring` and `border` against their adjacent surfaces.

## Method — use the script, not mental arithmetic

```bash
python3 <skill>/scripts/contrast.py --fg "#HEX" --bg "#HEX" [--backdrop "#HEX"]
python3 <skill>/scripts/contrast.py --batch pairs.json      # [{pair, fg, bg, backdrop}]
```

It accepts hex, `rgba(...)`, and `oklch(...)`; composites alpha over `--backdrop` before computing; prints the composited hexes and the ratio to two decimals. Paste its output into `evidence`. A ratio you computed in prose is `unverified`.

## Pairs to evaluate, per mode

- Every `X` / `X-foreground` pair present in `variables.json` (including custom and state pairs)
- `destructive` with the foreground the file actually uses on destructive buttons (find it in `nodes/*.json`; the default theme uses white text)
- `muted-foreground` on `background` and on `card` (it is used on both)
- `ring` vs `background` and vs the control surface it wraps — threshold 3:1 (non-text UI, SC 1.4.11)
- `border` vs `background` and vs `card`; `input` vs `background` — 3:1
- Alpha tokens: composite over the real backdrop (dark `border` over dark `background`), never in isolation

## Thresholds
- Text: AA 4.5, AAA 7. Large text (≥ 24px, or ≥ 18.66px bold) AA 3.
- UI components and borders: 3.
- `disabled` pairs: exempt — still compute and report with `exempt: true`, no finding unless ratio < 2 (then `low`, legibility note).

## Severity
- Text pair below 4.5 → `critical`
- UI/border below 3 → `high`
- Pair between 4.5 and 7 → not a finding; record `aaa: false` in the table only

For every failure the fix names a concrete replacement: the nearest primitive in the file's own palette that clears the threshold (say which one and its ratio), so the designer does not have to search.

## Tables
`tables.matrix`: `{Light: [...], Dark: [...]}`, rows `{pair, surface_hex, foreground_hex, backdrop_hex, ratio, aa, aa_large_ui, aaa, exempt}`. Include passes.

## Do not audit
Whether values differ between modes (modes agent). Which tokens should exist (tokens agent).
