# Deneb Spec — Panel 2A, Mode Subgroup Forest Plot

Page 2, position 60, 100, 1480, 430. Source table: `mode_subgroup.csv`.

**Style matches Panel 1B exactly**: Segoe UI, `#404040` axis text at size 18,
`#404040` for CI lines/whiskers, `#EFEFEF` gridlines, transparent background.

**One thing this spec deliberately does not do:** hardcode a sort order or
literal category strings for the `family`/`mode` columns. The guide confirms
two facts about this table's real values (two rows carry the literal mode
string `"web - paper (interaction)"`; one row is "the paper-cell Family A row,
p = 0.0289") but never lists all 7 rows verbatim. Rather than invent plausible-
looking category names that might not match the real CSV, this spec builds the
row label by concatenating whatever `family`/`mode` actually contain, and
leaves the y-axis unsorted (`"sort": null`), which preserves the CSV's own row
order.

**Confirmed 2026-09-09** against `outputs/tables/mode_subgroup.csv`: 7 rows —
H1/A item nonresponse/web, H1/A item nonresponse/paper, H3/C response
error/web, H3/C response error/paper, H2/B break-off/web, H1/A item
nonresponse/web - paper (interaction), H3/C response error/web - paper
(interaction). Both facts above check out, and the CSV's own order already
groups by family (A, A, C, C, B, then the two interaction rows) — `"sort":
null` reads sensibly with no override needed.

**X-axis domain corrected 2026-09-09.** The prior placeholder (`[-2.2, 2.2]`)
did not fit the real data: `ci_lo_pp`'s minimum across the 7 rows is −1.28
(H1, paper), and `ci_hi_pp`'s maximum is **+4.80** (H2, break-off, web) — well
outside the placeholder's upper bound, which would have clipped that row's
whisker. Domain is now `[-2, 5.5]` (see the JSON below), comfortably covering
−1.28 to 4.80 with margin on both sides.

**Color rule:** flat, single color (`#404040`) on every point — this panel
must never imply significance through color (the original guide is explicit:
"Nothing in this panel may be coloured by how small a p-value is"). The two
interaction-contrast rows are distinguished by **shape** (diamond) instead,
which carries no significance implication.

## Spec state (synced to live Deneb, 2026-09-10)

Two changes are baked into the JSON below and match the live visual:

1. **Zero-line rendering fix.** The no-effect line had the same defect
   found on Panel 2B (`05-deneb-panel-2B-2C-dumbbell.md`, "Zero-line
   rendering fix"): only an `x` encoding, so it inherited the top-level
   nominal `y` (`row_label`) and collapsed to zero vertical extent. Fixed
   with explicit `y`/`y2` in pixel space, and moved to `#503E7A` (brand
   purple) so it reads as a fixed reference, not another data mark — it no
   longer shares `#404040` with the CI lines and whiskers.
2. **`"container"` sizing.** `"width": "container"`,
   `"height": "container"` (was `2000 × 350`) — the house pattern across
   1B / 2A / 2B / 2C, so Deneb hands Vega the real container size and
   fonts render at their declared pixel size. Comes with two-line row
   labels via `labelExpr` (`family` / `mode` on separate lines) and axis
   font bumped 16 → 18.

```json
{
  "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
  "background": "transparent",
  "padding": 10,
  "width": "container",
  "height": "container",
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
  "transform": [
    {
      "calculate": "datum['family'] + ' — ' + datum['mode']",
      "as": "row_label"
    },
    {
      "calculate": "indexof(datum['mode'], 'interaction') >= 0 ? 'interaction' : 'direct'",
      "as": "row_type"
    }
  ],
  "encoding": {
    "y": {
      "field": "row_label",
      "type": "nominal",
      "title": null,
      "sort": null,
      "axis": {
        "labelFontSize": 18,
        "labelFontWeight": 600,
        "labelExpr": "replace(datum.label, ' — ', '\\n')",
        "labelLineHeight": 20,
        "labelAlign": "right",
        "labelBaseline": "middle",
        "labelLimit": 340,
        "labelPadding": 12,
        "domain": false,
        "ticks": false
      }
    }
  },
  "layer": [
    {
      "description": "No-effect line — full-height pixel-space rule, lighter shade for comparison. Fixed 2026-09-10: previously had no y of its own and inherited the top-level nominal row_label y, collapsing to zero vertical extent.",
      "mark": { "type": "rule", "color": "#503E7A", "strokeWidth": 2 },
      "encoding": {
        "x": {
          "datum": 0,
          "type": "quantitative",
          "scale": { "domain": [-2, 5.5] }
        },
        "y": { "value": 0 },
        "y2": { "value": { "expr": "height" } }
      }
    },
    {
      "description": "95% CI of the difference for each row. Numeric ci_lo_pp / ci_hi_pp columns, already on the table — nothing parsed or derived.",
      "mark": { "type": "rule", "color": "#404040", "strokeWidth": 4 },
      "encoding": {
        "x": {
          "field": "ci_lo_pp",
          "type": "quantitative",
          "scale": { "domain": [-2, 5.5], "nice": false },
          "title": "percentage points (treatment − control)",
          "axis": {
            "grid": true,
            "gridColor": "#EFEFEF",
            "labelFontSize": 18,
            "labelFontWeight": 600
          }
        },
        "x2": { "field": "ci_hi_pp" }
      }
    },
    {
      "description": "Whisker caps.",
      "mark": { "type": "tick", "thickness": 4, "size": 20, "color": "#404040" },
      "encoding": { "x": { "field": "ci_lo_pp", "type": "quantitative" } }
    },
    {
      "mark": { "type": "tick", "thickness": 4, "size": 20, "color": "#404040" },
      "encoding": { "x": { "field": "ci_hi_pp", "type": "quantitative" } }
    },
    {
      "description": "Point estimate. Flat colour, never keyed to significance — shape (diamond vs. circle) is the only encoded distinction, marking the two interaction contrasts.",
      "mark": {
        "type": "point",
        "filled": true,
        "size": 260,
        "stroke": "white",
        "strokeWidth": 2,
        "color": "#404040"
      },
      "encoding": {
        "x": { "field": "diff_pp", "type": "quantitative" },
        "shape": {
          "field": "row_type",
          "type": "nominal",
          "scale": {
            "domain": ["direct", "interaction"],
            "range": ["circle", "diamond"]
          },
          "legend": {
            "title": "row type",
            "orient": "bottom",
            "labelFontSize": 18,
            "labelFontWeight": 600,
            "titleFontSize": 18,
            "titleFontWeight": 600,
            "symbolSize": 160
          }
        },
        "tooltip": [
          { "field": "family", "type": "nominal", "title": "family" },
          { "field": "mode", "type": "nominal", "title": "mode" },
          { "field": "diff_pp", "type": "quantitative", "format": "+.2f", "title": "effect (pp)" },
          { "field": "ci_lo_pp", "type": "quantitative", "format": "+.2f", "title": "CI low" },
          { "field": "ci_hi_pp", "type": "quantitative", "format": "+.2f", "title": "CI high" },
          { "field": "p_value", "type": "quantitative", "format": ".4f", "title": "p (uncorrected)" }
        ]
      }
    }
  ]
}
```

**Confirmed 2026-09-10 (live in Deneb):** zero-line fix, `#503E7A` colour,
`"container"` sizing, and the two-line `labelExpr` row labels all applied
and rendering. Full-height `#503E7A` rule at x = 0, distinct from the
`#404040` CI lines/whiskers and flat-grey points. The 7-row content, shape
encoding, and `[-2, 5.5]` domain from the 2026-09-09 confirmation above are
unaffected.
