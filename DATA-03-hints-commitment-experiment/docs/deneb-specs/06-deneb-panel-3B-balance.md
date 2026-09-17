# Deneb Spec — Panel 3B, Balance Dot Plot

Page 3, position 60, 240, 1480, 340. Source table: `balance.csv`. Visual
title (set in Power BI's own title field, not in this spec): "POST-HOC — NOT
PRE-REGISTERED."

## Correction from an earlier draft of this plan

An earlier pass assumed the gap needed computing (`treatment_share_pct −
control_share_pct`) via a transform. It doesn't: `balance.csv` already has
`max_arm_share_gap_pp` as its own column (confirmed in the original guide's
§1 type table). This spec does zero arithmetic — it plots an existing column
directly, which is the more correct choice given §7's blanket prohibition on
recomputing anything.

**Color rule — the one this panel exists to get right:** bound to `flag`
only, using the exact literal strings the guide specifies (`"balanced"` /
`"IMBALANCED (p<0.01)"`), reusing Panel 1B's own verdict palette (`#4F6228`
green, `#C0504D` red) rather than inventing new hex values. **Never bind
color to `p_value` on this panel** — the guide calls this out by name as the
mistake that would light up the one row that shouldn't be highlighted this
way.

## Zero-line rendering fix (2026-09-10) — applied

Panel 3B was the last spec still carrying the broken zero-line pattern that
was found and fixed on Panel 2B / 2A / 1B (full root cause in
`05-deneb-panel-2B-2C-dumbbell.md`'s "Zero-line rendering fix" section): the
"no gap between arms" `rule` layer had only an `x` encoding (`"datum": 0`),
so it inherited the top-level nominal `y` (`covariate`) and collapsed to
zero vertical extent — never rendering as a visible line. Fixed the same
way, explicit `y`/`y2` in pixel space:

```json
"y": { "value": 0 },
"y2": { "value": { "expr": "height" } }
```

The line's colour is also moved to `#503E7A` (brand purple), matching the
zero/no-effect line on Panel 2B / 2A / 1B, so the "perfect balance"
reference reads consistently across all pages rather than as dark grey here
and purple everywhere else. The dot colours (`#4F6228` / `#C0504D`, bound to
`flag`) are untouched. Both changes are in the JSON below. Confirm with
Neyda that the `#503E7A` colour is wanted here — the cross-panel
consistency argument is the only reason for it; 3B has no grey data marks
for a `#404040` line to blend into.

```json
{
  "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
  "background": "transparent",
  "padding": 10,
  "width": 2000,
  "height": 480,
  "config": {
    "view": { "stroke": "transparent" },
    "axis": {
      "labelFontSize": 18,
      "titleFontSize": 18,
      "titleColor": "#404040",
      "labelColor": "#404040",
      "labelFontWeight": 600
    },
    "font": "Segoe UI"
  },
  "data": { "name": "dataset" },
  "encoding": {
    "y": {
      "field": "covariate",
      "type": "nominal",
      "title": null,
      "sort": null,
      "axis": {
        "labelFontSize": 16,
        "labelFontWeight": 600,
        "labelLimit": 300,
        "domain": false,
        "ticks": false
      }
    }
  },
  "layer": [
    {
      "description": "Zero line — no gap between arms. Full-height pixel-space rule (fixed 2026-09-10: previously had no y of its own and inherited the top-level nominal covariate y, collapsing to zero vertical extent).",
      "mark": { "type": "rule", "color": "#503E7A", "strokeWidth": 2 },
      "encoding": {
        "x": {
          "datum": 0,
          "type": "quantitative",
          "scale": { "domain": [-6, 6] }
        },
        "y": { "value": 0 },
        "y2": { "value": { "expr": "height" } }
      }
    },
    {
      "description": "Balance gap per covariate. max_arm_share_gap_pp is an existing column on balance.csv — nothing computed in this spec, per §7's prohibition on recomputing anything.",
      "mark": {
        "type": "point",
        "filled": true,
        "size": 260,
        "stroke": "white",
        "strokeWidth": 2
      },
      "encoding": {
        "x": {
          "field": "max_arm_share_gap_pp",
          "type": "quantitative",
          "scale": { "domain": [-6, 6], "nice": false },
          "title": "percentage-point gap (overrepresented level, treatment − control)",
          "axis": { "grid": true, "gridColor": "#EFEFEF" }
        },
        "color": {
          "field": "flag",
          "type": "nominal",
          "scale": {
            "domain": ["balanced", "IMBALANCED (p<0.01)"],
            "range": ["#4F6228", "#C0504D"]
          },
          "legend": {
            "title": "balance",
            "orient": "bottom",
            "labelFontSize": 16,
            "labelFontWeight": 600,
            "titleFontSize": 16,
            "titleFontWeight": 600,
            "symbolSize": 160
          }
        },
        "tooltip": [
          { "field": "covariate", "type": "nominal", "title": "covariate" },
          { "field": "overrepresented_level", "type": "nominal", "title": "overrepresented level" },
          { "field": "treatment_share_pct", "type": "quantitative", "format": ".1f", "title": "treatment %" },
          { "field": "control_share_pct", "type": "quantitative", "format": ".1f", "title": "control %" },
          { "field": "p_value", "type": "quantitative", "format": ".4f", "title": "p (context only — not the colour rule)" },
          { "field": "flag", "type": "nominal", "title": "flag" }
        ]
      }
    }
  ]
}
```

**Confirmed 2026-09-09** against the full `balance.csv`: `max_arm_share_gap_pp`
ranges from about 0.78 to 4.21 pp across all 8 rows (the 4.21 is the
survey-mode row). Domain `[-6, 6]` comfortably covers this with margin — no
change needed.

**Re-confirmed 2026-09-10** against `balance.csv` before the Phase 4 build:
8 rows, `flag` is exactly `balanced` (7) / `IMBALANCED (p<0.01)` (1, the
`Survey mode (FormType)` row) — matches the colour-scale domain literally.
All 8 gap values positive (0.78–4.21), so every dot sits right of the zero
line; that's expected for a max-gap metric, not a domain problem. `covariate`
labels carry their parenthetical variable codes (`Age group (AgeGrpB)` …) —
`labelLimit: 300` handles them; `sort: null` keeps CSV order (Age, Sex,
Race, Education, Income, Marital, Survey mode, Design stratum), which is
*not* the gap-sorted order the mockup shows — follow the spec unless Neyda
asks to sort by gap.

**Font-size note:** like Panel 1B and 2A, this spec's internal `width: 2000`
is much larger than the 1480-px visual container, so Deneb scales the whole
SVG (text included) down to fit. This is the cross-panel font-scaling issue
logged separately — not fixed here; build 3B as-is for now.
