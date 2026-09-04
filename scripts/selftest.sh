#!/usr/bin/env bash
# Runs the deterministic half of the pipeline on synthetic data. No Figma or network needed.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
TMP="$(mktemp -d)"
python3 "$HERE/make_fixture.py" "$TMP/fixture"
python3 "$HERE/consolidate.py" "$TMP/fixture" --strict
python3 "$HERE/render_report.py" "$TMP/fixture" --out "$TMP/fixture/report.html"
python3 "$HERE/contrast.py" --fg "#767676" --bg "#FFFFFF" | grep -q '"ratio": 4.54' && echo "contrast.py: OK (4.54 boundary case)"
echo "selftest passed — report at $TMP/fixture/report.html"
