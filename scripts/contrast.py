#!/usr/bin/env python3
"""WCAG 2.1 contrast with alpha compositing and oklch support.

Usage:
  contrast.py --fg "#111827" --bg "#FFFFFF"
  contrast.py --fg "oklch(1 0 0 / 10%)" --bg "oklch(0.145 0 0)" --backdrop "#0A0A0A"
  contrast.py --batch pairs.json     # [{"pair": "...", "fg": "...", "bg": "...", "backdrop": "..."}]

Prints composited hexes and the ratio (2 dp) plus AA / AA-large-UI / AAA verdicts.
Alpha colours are composited over --backdrop (default: the other colour, if opaque).
"""
import argparse
import json
import math
import re
import sys

# ---------- parsing ----------

def _clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


def _parse_alpha(tok):
    tok = tok.strip()
    if tok.endswith('%'):
        return float(tok[:-1]) / 100.0
    return float(tok)


def parse_color(s):
    """Return (r, g, b, a) with r,g,b in 0..1 linear-free sRGB gamma space."""
    s = s.strip()
    m = re.fullmatch(r'#?([0-9a-fA-F]{3,8})', s)
    if m:
        h = m.group(1)
        if len(h) in (3, 4):
            h = ''.join(c * 2 for c in h)
        if len(h) == 6:
            h += 'FF'
        if len(h) != 8:
            raise ValueError(f'bad hex: {s}')
        r, g, b, a = (int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4, 6))
        return r, g, b, a
    m = re.fullmatch(r'rgba?\(([^)]*)\)', s, re.I)
    if m:
        parts = re.split(r'[,\s/]+', m.group(1).strip())
        parts = [p for p in parts if p]
        vals = []
        for p in parts[:3]:
            vals.append(float(p[:-1]) / 100.0 if p.endswith('%') else float(p) / 255.0)
        a = _parse_alpha(parts[3]) if len(parts) > 3 else 1.0
        return vals[0], vals[1], vals[2], a
    m = re.fullmatch(r'oklch\(([^)]*)\)', s, re.I)
    if m:
        body = m.group(1)
        alpha = 1.0
        if '/' in body:
            body, atok = body.split('/')
            alpha = _parse_alpha(atok)
        L, C, H = [p for p in re.split(r'[,\s]+', body.strip()) if p]
        L = float(L[:-1]) / 100.0 if L.endswith('%') else float(L)
        C = float(C)
        H = 0.0 if H.lower() == 'none' else float(H)
        r, g, b = oklch_to_srgb(L, C, H)
        return r, g, b, alpha
    raise ValueError(f'unrecognised colour: {s}')


# ---------- oklch -> sRGB (CSS Color 4 reference) ----------

def oklch_to_srgb(L, C, H):
    h = math.radians(H)
    a = C * math.cos(h)
    b = C * math.sin(h)
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b
    l, m, s = l_ ** 3, m_ ** 3, s_ ** 3
    r_lin = +4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s
    g_lin = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s
    b_lin = -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s
    return tuple(_clamp(_gamma(_clamp(v))) for v in (r_lin, g_lin, b_lin))


def _gamma(v):
    return 12.92 * v if v <= 0.0031308 else 1.055 * (v ** (1 / 2.4)) - 0.055


def _linear(v):
    return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4


# ---------- compositing & ratio ----------

def composite(fg, backdrop):
    r, g, b, a = fg
    br, bg_, bb, _ = backdrop
    return (r * a + br * (1 - a), g * a + bg_ * (1 - a), b * a + bb * (1 - a), 1.0)


def luminance(c):
    r, g, b, _ = c
    return 0.2126 * _linear(r) + 0.7152 * _linear(g) + 0.0722 * _linear(b)


def ratio(c1, c2):
    l1, l2 = luminance(c1), luminance(c2)
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


def to_hex(c):
    return '#' + ''.join(f'{round(_clamp(v) * 255):02X}' for v in c[:3])


def evaluate(fg_s, bg_s, backdrop_s=None):
    fg = parse_color(fg_s)
    bg = parse_color(bg_s)
    backdrop = parse_color(backdrop_s) if backdrop_s else None
    # Composite the surface first (it may itself be translucent, e.g. dark border tokens).
    if bg[3] < 1.0:
        if backdrop is None:
            raise ValueError('bg has alpha; --backdrop required')
        bg = composite(bg, backdrop)
    if fg[3] < 1.0:
        fg = composite(fg, bg)
    r = ratio(fg, bg)
    return {
        'foreground_hex': to_hex(fg),
        'surface_hex': to_hex(bg),
        'backdrop_hex': to_hex(backdrop) if backdrop else None,
        'ratio': round(r, 2),
        'aa': r >= 4.5,
        'aa_large_ui': r >= 3.0,
        'aaa': r >= 7.0,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--fg')
    ap.add_argument('--bg')
    ap.add_argument('--backdrop')
    ap.add_argument('--batch', help='JSON file: [{pair, fg, bg, backdrop?}]')
    args = ap.parse_args()
    if args.batch:
        with open(args.batch) as f:
            rows = json.load(f)
        out = []
        for row in rows:
            try:
                res = evaluate(row['fg'], row['bg'], row.get('backdrop'))
                res['pair'] = row.get('pair')
                out.append(res)
            except Exception as e:  # keep going; report the bad row
                out.append({'pair': row.get('pair'), 'error': str(e)})
        print(json.dumps(out, indent=2))
        return
    if not (args.fg and args.bg):
        ap.error('--fg and --bg required (or --batch)')
    res = evaluate(args.fg, args.bg, args.backdrop)
    print(json.dumps(res, indent=2))


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f'error: {e}', file=sys.stderr)
        sys.exit(1)
