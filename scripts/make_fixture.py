#!/usr/bin/env python3
"""Generate a synthetic audit workspace (no client data) for testing the pipeline.

Usage: make_fixture.py <out dir>
Then:  consolidate.py <out dir> && render_report.py <out dir>
"""
import json, os, sys

def main():
    A = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else 'fixture')
    os.makedirs(f'{A}/snapshot', exist_ok=True); os.makedirs(f'{A}/findings', exist_ok=True)
    SRC = "https://ui.shadcn.com/docs/theming#theme-tokens"; BTN = "https://ui.shadcn.com/docs/components/base/button"
    json.dump({"file_key": "demo", "file_name": "Acme Design System (sample)", "root_node_id": "1:1", "mode": "component",
               "flavor": "base", "audited_at": "2026-09-04",
               "docs_fetched": ["https://ui.shadcn.com/docs/theming", BTN, "https://ui.shadcn.com/r/styles/base-nova/button.json"],
               "in_scope_components": [{"name": "Button", "node_id": "1:1"}]}, open(f'{A}/snapshot/meta.json', 'w'), indent=2)

    def F(agent, n, **k):
        d = dict(id=f"{agent}-{n:03d}", category="pairing", dimension="pairing", severity="high", node_id="1:1",
                 layer_path="Button / variant=default", element="x", current_value="—", expected_value="—", source=SRC,
                 evidence="variables.json › …", current_score=4, fix="…", effort="S", benefit="1:1 token mapping",
                 final_score=10, confidence="verified"); d.update(k); return d
    def chk(dim, name, ok, fid=None): return dict(dimension=dim, name=name, passed=ok, finding_id=fid)
    def file(agent, checks, findings, tables=None, **k):
        json.dump(dict(agent=agent, mode="component", flavor="base", spec_sources=[SRC], checks=checks, findings=findings,
                       compliant=k.get('compliant', [f"{agent}: baseline pairs present in both modes"]), off_spec=k.get('off_spec', []),
                       unverified=k.get('unverified', []), tables=tables or {}, notes=k.get('notes', "")),
                  open(f'{A}/findings/{agent}.json', 'w'), indent=2)

    file("tokens", [chk("pairing", f"pair {t}", True) for t in ["primary", "secondary", "muted", "accent", "card", "popover"]]
         + [chk("pairing", "primary-disabled pair", False, "tokens-001"), chk("pairing", "radius-md = base×0.8", False, "tokens-002")],
         [F("tokens", 1, element="primary-disabled — missing foreground pair", current_value="none", expected_value="primary-disabled-foreground",
            fix="Create color/semantic/primary-disabled-foreground; Light+Dark alias primary-foreground; scope text+fill",
            evidence="variables.json › full Semantic collection pull (system-mode, all 40 tokens) has primary-disabled, no *-foreground anywhere",
            evidence_scope="global"),
          F("tokens", 2, category="radius", layer_path="Semantic / radius/radius-md", node_id=None, element="radius-md not derived from base",
            current_value="6", expected_value="8 (10 × 0.8)", source="https://ui.shadcn.com/docs/theming#radius-scale",
            evidence="variables.json › radius-md=6, radius=10", fix="Set radius-md to alias radius × 0.8", severity="medium")],
         tables={"inventory": [{"token": t, "present": True, "collection": "Semantic", "mode_coverage": "Light+Dark", "aliased": True, "notes": ""}
                               for t in ["background", "foreground", "primary", "primary-foreground", "secondary", "muted", "accent", "border", "input", "ring"]]
                 + [{"token": "primary-disabled-foreground", "present": False, "collection": None, "mode_coverage": "none", "aliased": None, "notes": "custom pair incomplete"}]})
    file("variables", [chk("architecture", "primary aliases primitive", True), chk("architecture", "ghost fill not primitive", False, "variables-001"),
                       chk("architecture", "radius-md derived", False, "variables-002"),
                       chk("architecture", "secondary-hover alias target known", False, "variables-003")],
         [F("variables", 1, category="architecture", dimension="architecture", layer_path="Button / variant=ghost / Fill", element="fill — bound directly to a primitive",
            current_value="tailwind/transparent", expected_value="semantic alias or no fill", fix="Remove the fill; ghost has none in the spec",
            evidence="nodes/1-1.json › ghost.fill", severity="medium"),
          F("variables", 2, category="radius", dimension="architecture", layer_path="Semantic / radius/radius-md", node_id=None, element="radius-md not derived from base",
            current_value="6", expected_value="8px via alias radius×0.8", evidence="chains: radius-md status=raw", fix="Alias radius-md → radius ×0.8", severity="medium"),
          F("variables", 3, category="alias", dimension="architecture", layer_path="Semantic / secondary-hover", node_id=None,
            element="alias target unknown — get_variable_defs exposes only the resolved hex", current_value="#F5F5F5 (resolved)",
            expected_value="confirm secondary-hover aliases a primitive (not a raw literal) via use_figma or ground_truth.md",
            evidence="variables.json › secondary-hover has no alias_of field (get_variable_defs is a flat name→value map, no chain data)",
            fix="Run the read-only use_figma script (references/extraction.md) or ask for a Variables-panel screenshot to confirm the chain",
            severity="medium", confidence="unverified", alias_status="aliased_target_unknown")],
         tables={"chains": [{"variable": "primary", "tier": "semantic", "alias_of": "neutral/900", "resolves_to": "#171717", "status": "ok"},
                            {"variable": "radius-md", "tier": "semantic", "alias_of": None, "resolves_to": "6", "status": "raw"},
                            {"variable": "ring", "tier": "semantic", "alias_of": "neutral/400", "resolves_to": "#A3A3A3", "status": "ok"},
                            {"variable": "secondary-hover", "tier": "semantic", "alias_of": None, "resolves_to": "#F5F5F5", "status": "unknown"}]})
    file("modes", [chk("mode", f"{t} both modes", True) for t in ["primary", "secondary", "muted-foreground", "accent", "ring"]]
         + [chk("mode", "accent-hover distinct in Dark", False, "modes-001")],
         [F("modes", 1, category="mode", dimension="mode", layer_path="Semantic / accent-hover", node_id=None, element="accent-hover identical in Light and Dark",
            current_value="violet/200 / violet/200", expected_value="distinct Dark value", fix="Set Dark accent-hover to violet/800",
            evidence="ground_truth.md: accent-hover row", severity="medium", mode_evidence="cell_values")],
         tables={"parity": [{"token": "primary", "light": "#171717", "dark": "#EBEBEB", "identical": False, "deliberate": True},
                            {"token": "accent-hover", "light": "#DDD6FE", "dark": "#DDD6FE", "identical": True, "deliberate": None}]})
    file("contrast", [chk("contrast", "primary pair Light", True), chk("contrast", "primary pair Dark", True),
                      chk("contrast", "muted-foreground/card Dark", False, "contrast-001"), chk("contrast", "ring vs background", False, "contrast-002")],
         [F("contrast", 1, category="contrast", dimension="contrast", severity="critical", layer_path="Button / variant=ghost / Label",
            element="muted-foreground on card fails AA in Dark", current_value="#8A8A8A on #171717 = 4.21", expected_value="≥ 4.5",
            evidence="contrast.py: fg #8A8A8A bg #171717 ratio 4.21", fix="Set Dark muted-foreground to neutral/400 (#A3A3A3, 6.1:1)"),
          F("contrast", 2, category="a11y", dimension="contrast", severity="high", layer_path="Button / variant=default, state=focus / Ring",
            element="focus ring — 1.50:1 vs background", current_value="#A3A3A3 @50% on #FFFFFF = 1.50", expected_value="≥ 3:1 (SC 1.4.11)",
            evidence="contrast.py: composited #D1D1D1 on #FFFFFF 1.50", fix="Bind ring effect colour to base/ring @50% and add the 1px border-ring")],
         tables={"matrix": {
             "Light": [{"pair": "primary", "surface_hex": "#171717", "foreground_hex": "#FAFAFA", "backdrop_hex": None, "ratio": 17.16, "aa": True, "aa_large_ui": True, "aaa": True, "exempt": False},
                       {"pair": "secondary", "surface_hex": "#F5F5F5", "foreground_hex": "#171717", "backdrop_hex": None, "ratio": 15.9, "aa": True, "aa_large_ui": True, "aaa": True, "exempt": False},
                       {"pair": "ring/background", "surface_hex": "#FFFFFF", "foreground_hex": "#D1D1D1", "backdrop_hex": "#FFFFFF", "ratio": 1.5, "aa": False, "aa_large_ui": False, "aaa": False, "exempt": False},
                       {"pair": "primary-disabled", "surface_hex": "#EDE9FE", "foreground_hex": "#8F73C0", "backdrop_hex": None, "ratio": 3.2, "aa": False, "aa_large_ui": True, "aaa": False, "exempt": True}],
             "Dark": [{"pair": "primary", "surface_hex": "#EBEBEB", "foreground_hex": "#171717", "backdrop_hex": None, "ratio": 15.1, "aa": True, "aa_large_ui": True, "aaa": True, "exempt": False},
                      {"pair": "muted-foreground/card", "surface_hex": "#171717", "foreground_hex": "#8A8A8A", "backdrop_hex": None, "ratio": 4.21, "aa": False, "aa_large_ui": True, "aaa": False, "exempt": False}]}})
    V = ["default", "secondary", "destructive", "outline", "ghost", "link"]; S = ["default", "hover", "focus-visible", "disabled"]
    cells = {f"{v}|{s}": ("missing" if (v == "ghost" and s == "focus-visible") else "inconsistent" if (v == "link" and s == "disabled") else "present") for v in V for s in S}
    file("states", [chk("state_variant", f"{v}|{s}", cells[f"{v}|{s}"] == "present", ("states-001" if cells[f"{v}|{s}"] == "missing" else None)) for v in V for s in S],
         [F("states", 1, category="state", dimension="state_variant", severity="high", layer_path="Button / variant=ghost", element="focus-visible state missing",
            current_value="none", expected_value="ring 3px ring/50 + border-ring", source=BTN, evidence="nodes/1-1.json › no state=focus for ghost",
            fix="Add state=focus-visible variant: 3px ring bound to ring @50%")],
         tables={"coverage": {"Button": {"variants": V, "states": S, "cells": cells, "convention": "opacity"}}})
    file("components", [chk("state_variant", "Button variants complete", True), chk("state_variant", "Button sizes complete", False, "components-001"),
                        chk("architecture", "label typography", False, "components-002"), chk("architecture", "icon slot 16px", True), chk("architecture", "auto layout on", True)],
         [F("components", 1, category="size", dimension="state_variant", severity="high", layer_path="Button / size", element="size property — missing icon-sm, icon-lg values",
            current_value="default, sm, lg, icon", expected_value="default, xs, sm, lg, icon, icon-xs, icon-sm, icon-lg", source=BTN + "#api-reference",
            evidence="components.json › Button.size values", fix="Add size=xs (24), icon-xs (24), icon-sm (28), icon-lg (36) per cva", effort="M"),
          F("components", 2, category="typography", dimension="architecture", severity="medium", layer_path="Button / variant=default / Label", element="label weight — 600 on every size",
            current_value="600", expected_value="500 (font-medium)", source=BTN, evidence="nodes/1-1.json › label.font.weight=600", fix="Bind label to Text/sm/medium (500)")],
         tables={"parity": {"Button": {"axes": {"naming": "pass", "variants": "pass", "sizes": "fail", "states": "fail", "tokens": "pass", "layout": "pass",
                                                 "typography": "fail", "anatomy": "pass", "props": "pass", "a11y": "unverified"}}}},
         off_spec=[{"item": "variant=warning on Button", "recommendation": "document as intentional extension", "reason": "not in Button API (base)"},
                   {"item": "State=Pressed", "recommendation": "remove", "reason": "base has no pressed state; active is translate-y-px"}])
    file("styles", [chk("architecture", "Text/sm/medium maps to text-sm font-medium", True), chk("architecture", "shadow/xs matches shadow-xs", True)], [],
         tables={"styles": [{"style": "Text/sm/medium", "kind": "text", "maps_to": "text-sm font-medium", "status": "ok"},
                            {"style": "Text/sm/semibold", "kind": "text", "maps_to": "text-sm font-semibold", "status": "unused"}]})
    file("governance", [chk("governance", "Button published", True), chk("governance", "Button description", False, "governance-001"), chk("governance", "property names match props", True)],
         [F("governance", 1, category="governance", dimension="governance", severity="low", layer_path="Button", element="component description missing",
            current_value="", expected_value="'shadcn/ui Button (base)'", source=BTN, evidence="components.json › Button.description = ''",
            fix="Add description naming the shadcn counterpart and flavor")],
         tables={"readiness": {"Button": {"published": True, "description": False, "hidden_layers": 0, "naming_consistent": True, "code_connect_ready": True}}},
         unverified=[{"check": "Badge published", "missing": "Badge not in snapshot"}])
    json.dump({"verdict": "NEEDS FIXES",
               "verdict_paragraph": "A solid token foundation with two structural gaps — the disabled pair and the radius derivation — and one verified contrast failure. Read the findings in two piles: defects to fix regardless of brand (contrast, focus ring, missing pair) and on-spec-API/off-spec-rendering choices (weight 600, pill radius) that need one decision before touching 264 variants.",
               "top_issues": ["contrast-001 — muted-foreground on card is 4.21:1 in Dark; set to neutral/400", "contrast-002 — focus ring composited grey at 1.50:1; bind to ring @50%",
                              "tokens-001 — primary-disabled has no foreground pair", "components-001 — four sizes missing versus the base API", "states-001 — ghost has no focus-visible state"],
               "fix_order": [{"step": 1, "finding_ids": ["contrast-001"], "root_cause": "Dark muted-foreground too dark", "action": "Set Dark muted-foreground to neutral/400 (#A3A3A3)", "effort": "S"},
                             {"step": 2, "finding_ids": ["contrast-002", "states-001"], "root_cause": "focus effect style bound to a grey unrelated to ring", "action": "Rebind focus/default to base/ring @50%, add 1px border-ring; add ghost focus-visible variant", "effort": "S"},
                             {"step": 3, "finding_ids": ["tokens-001"], "root_cause": "pair created without foreground", "action": "Create primary-disabled-foreground and bind disabled labels", "effort": "S"},
                             {"step": 4, "finding_ids": ["tokens-002", "variables-002"], "root_cause": "radius scale entered as numbers", "action": "Alias all radius-* to base with multipliers", "effort": "S"},
                             {"step": 5, "finding_ids": ["components-001", "components-002"], "root_cause": "size scale predates base-nova", "action": "Decide: adopt base-nova sizes/weights or document the pill system as an extension", "effort": "L"}],
               "resolutions": [{"finding_ids": ["tokens-002", "variables-002"], "decision": "Same fix, different wording; keep the alias phrasing.", "basis": "theming#radius-scale"}],
               "demotions": [{"finding_id": "variables-001", "from": "high", "to": "medium", "reason": "transparent primitive has no visual effect"}], "gaps": [],
               "recommendations": [{"title": "Adopt opacity-based states library-wide", "rationale": "Button already uses opacity; token-based disabled elsewhere would create a mixed convention.", "aligns_with": "bg-primary/80, opacity-50"},
                                   {"title": "Add a semantic radius tier", "rationale": "Components bind border-radius/* primitives; a single radius token with derived scale keeps the file 1:1 with --radius.", "aligns_with": "--radius, rounded-lg"}],
               "needs_verification": [],
               "accepted_divergences": [{"finding_ids": ["components-002"],
                                         "rationale": "Label weight 600 is consistent across every sampled Button size/variant (not a one-off) and the set description already calls the pill system a deliberate brand extension; normalizing to 500 would touch every variant for a documented, intentional choice, not a defect.",
                                         "evidence": "components.json › Button.description names the weight-600 system explicitly; nodes/1-1.json shows weight=600 on all 6 sampled variants"}]},
              open(f'{A}/review.json', 'w'), indent=2)
    print(f"fixture written to {A}")

if __name__ == '__main__':
    main()
