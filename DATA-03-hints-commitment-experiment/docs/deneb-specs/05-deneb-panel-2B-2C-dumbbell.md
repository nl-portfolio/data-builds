# Deneb Spec — Panels 2B and 2C, Sensitivity Dumbbell

Page 2. Panel 2B, `sensitivity_filter_missing.csv` (3 rows: H1, H2, H3).
Panel 2C, `sensitivity_web_never_seen.csv` (**2 rows: H1, H3 only** — no H2
row exists in that table; H2 is web-only, so the web-never-seen denominator
check produces no distinct estimate for it. This is correct, not a load
error). Both tables share the same column names (`hypothesis`,
`primary_diff_pp`, `primary_ci_pp`, `primary_p`, `sensitivity_diff_pp`,
`sensitivity_ci_pp`, `sensitivity_p`).

**Shared mark/encoding logic, per-panel x-domain.** The `transform` /
`layer` / `encoding` blocks below are identical for both panels — bound
table and x-scale domain are the only differences:

| | Table | x-domain (no-effect line + connector layers) |
|---|---|---|
| Panel 2B | `sensitivity_filter_missing.csv` | `[-1.5, 2.5]` — covers H2's ~1.82 pp |
| Panel 2C | `sensitivity_web_never_seen.csv` | `[-0.5, 0.5]` — tight; every 2C value is between −0.22 and −0.02, so the shared 2B domain would bury them on the zero line (Neyda's call, 2026-09-10) |

**Sizing (both panels, 2026-09-10):** `"width": "container"`,
`"height": "container"` — no hardcoded pixels. This is the house pattern
now across 1B / 2A / 2B / 2C: Deneb passes the real visual-container size
to Vega, so fonts render at their declared pixel size instead of being
scaled with the SVG. The JSON below is the **Panel 2B** spec; the Panel 2C
delta (two domain values) is spelled out after it.

## Correction from an earlier draft of this plan

An earlier pass said this chart needed CI whiskers on each dot. It doesn't,
and can't: `primary_ci_pp` and `sensitivity_ci_pp` are pre-formatted **strings**
on both tables, not numeric bounds — the original guide is explicit that these
stay display-only and never get parsed ("Text CI columns... kept for human
display only... do not parse the strings in Power Query or DAX"). Building a
numeric CI here would mean deriving new numbers that don't exist as columns,
which is exactly the kind of recomputation this whole project exists to avoid.

**What this spec does instead:** a true dumbbell — one dot for the primary
estimate, one for the sensitivity estimate, a connecting line between them —
with both CI strings shown verbatim in the tooltip. This satisfies "no point
estimate without its interval" without parsing anything.

**How the two-column comparison becomes one chart:** a Vega-Lite `fold`
transform turns the two `*_diff_pp` columns into a tidy long-format field
(`series` = "primary_diff_pp" / "sensitivity_diff_pp", `diff_pp` = the value),
which is what makes the color legend work natively instead of hand-faking two
constant-colored layers. The original (un-folded) columns are still present on
every output row, which is why the connector-line layer below can still
reference `primary_diff_pp` / `sensitivity_diff_pp` directly.

**Style matches Panel 1B**: Segoe UI, `#404040` axis text, near-black `#1a1a1a`
for the connector (colour-standardised 2026-09-10, was `#8C8C8C`), grey/
dark-grey points for primary/sensitivity (no verdict-class color here — this
isn't a verdict-bearing panel).

## Zero-line rendering fix (2026-09-10) — read this before pasting

The no-effect line didn't render as a visible line in Deneb after Panel 2B was
built. Three guesses were tried and ruled out (explicit `"type":
"quantitative"`, explicit `"scale"` domain, a high-contrast colour change —
see `09-zero-line-troubleshooting.md`). None of those were the actual
problem, because none of them touched the axis that was actually broken.

**Root cause:** the no-effect line's layer only ever specified an `x`
encoding (`"datum": 0`). It never specified its own `y`. In a layered
Vega-Lite spec, a layer with no `y` of its own inherits the top-level `y`
encoding — here, `{"field": "hypothesis", "type": "nominal"}`. A rule mark
positioned by a single nominal `y` value, with no `y2`, has zero vertical
extent: both its endpoints land at the same band position. It wasn't
invisible because of colour or scale — it was invisible because it had no
length. That's also why the earlier attempts on Panel 1B and Panel 2A missed
it: `x` was never the broken part.

**The fix:** give the layer its own `y`/`y2`, in pixel space, so it always
spans the full plot height regardless of the top-level `y` encoding:

```json
"y": { "value": 0 },
"y2": { "value": { "expr": "height" } }
```

**Colour update (2026-09-10, later):** the no-effect line itself now uses
`#503E7A` (brand purple), not `#1a1a1a` — chosen so the fixed reference line
reads as visually distinct from every grey/near-black data mark on the
chart (CI-adjacent marks, the connector) rather than blending with them.
This refines, for the zero line specifically, the colour-standardisation
decision recorded in `08-progress-tracker.md`; the connector stays
`#1a1a1a` as already standardised. Both the fix and this colour are now
baked into the spec below.

**Also applied, same day:** the same fix and colour were carried over to
`04-deneb-panel-2A-forest-plot.md` and to Panel 1B's live spec (synced to
`powerbi/panelB_deneb_spec.json`) — see `08-progress-tracker.md`'s "Open
cross-cutting issues" for the full cross-panel status.

This block is the **Panel 2B** spec, synced to the live Deneb visual
2026-09-10. Comment text has been normalised for the doc; nothing that
affects rendering differs from live.

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
      "fold": ["primary_diff_pp", "sensitivity_diff_pp"],
      "as": ["series", "diff_pp"]
    },
    {
      "calculate": "datum.series === 'primary_diff_pp' ? 'Primary' : 'Sensitivity'",
      "as": "series_label"
    },
    {
      "calculate": "datum.series === 'primary_diff_pp' ? datum.primary_ci_pp : datum.sensitivity_ci_pp",
      "as": "ci_display"
    },
    {
      "calculate": "datum.series === 'primary_diff_pp' ? datum.primary_p : datum.sensitivity_p",
      "as": "p_display"
    }
  ],
  "encoding": {
    "y": {
      "field": "hypothesis",
      "type": "nominal",
      "title": null,
      "sort": null,
      "axis": {
        "labelFontSize": 18,
        "labelFontWeight": 600,
        "labelExpr": "indexof(datum.label, ' ') > 0 ? slice(datum.label, indexof(datum.label, ' ') + 1) + '\\n' + slice(datum.label, 0, indexof(datum.label, ' ')) : datum.label",
        "labelLineHeight": 20,
        "labelAlign": "right",
        "labelBaseline": "middle",
        "labelPadding": 10,
        "domain": false,
        "ticks": false
      }
    }
  },
  "layer": [
    {
      "description": "No-effect line — full-height pixel-space rule (explicit y/y2), distinctly coloured so it reads as a fixed reference, not a data mark.",
      "mark": { "type": "rule", "color": "#503E7A", "strokeWidth": 2 },
      "encoding": {
        "x": {
          "datum": 0,
          "type": "quantitative",
          "scale": { "domain": [-1.5, 2.5] }
        },
        "y": { "value": 0 },
        "y2": { "value": { "expr": "height" } }
      }
    },
    {
      "description": "Connector between the primary and sensitivity point estimates for each hypothesis — a dumbbell, not a CI.",
      "mark": { "type": "rule", "color": "#1a1a1a", "strokeWidth": 2 },
      "encoding": {
        "x": {
          "field": "primary_diff_pp",
          "type": "quantitative",
          "scale": { "domain": [-1.5, 2.5], "nice": false },
          "title": "percentage points (treatment − control)",
          "axis": { "grid": true, "gridColor": "#EFEFEF" }
        },
        "x2": { "field": "sensitivity_diff_pp" }
      }
    },
    {
      "description": "Primary and sensitivity points, colour-coded by series. CI shown only in the tooltip, as the pre-formatted string — never plotted as a whisker.",
      "mark": {
        "type": "point",
        "filled": true,
        "size": 260,
        "stroke": "white",
        "strokeWidth": 2
      },
      "encoding": {
        "x": { "field": "diff_pp", "type": "quantitative" },
        "color": {
          "field": "series_label",
          "type": "nominal",
          "scale": {
            "domain": ["Primary", "Sensitivity"],
            "range": ["#8C8C8C", "#404040"]
          },
          "legend": {
            "title": "estimate",
            "orient": "bottom",
            "labelFontSize": 18,
            "labelFontWeight": 600,
            "titleFontSize": 18,
            "titleFontWeight": 600,
            "symbolSize": 160
          }
        },
        "tooltip": [
          { "field": "hypothesis", "type": "nominal", "title": "hypothesis" },
          { "field": "series_label", "type": "nominal", "title": "estimate" },
          { "field": "diff_pp", "type": "quantitative", "format": "+.2f", "title": "effect (pp)" },
          { "field": "ci_display", "type": "nominal", "title": "95% CI" },
          { "field": "p_display", "type": "quantitative", "format": ".3f", "title": "p" }
        ]
      }
    }
  ]
}
```

### Panel 2C — same spec, two edits

Paste the block above, then change **both** `"domain": [-1.5, 2.5]` to
**`[-0.5, 0.5]`** (once in the no-effect-line layer, once in the connector
layer). Nothing else differs — same transforms, same fields, same
`labelExpr`, same `"container"` sizing. Bind it to
`sensitivity_web_never_seen.csv` (2 rows: H1, H3).

**Confirmed 2026-09-09** against both source CSVs: filter-missing diff
values run about −0.27 pp to 1.82 pp (H2), well inside Panel 2B's
`[-1.5, 2.5]`; web-never-seen values run about −0.22 pp to −0.02 pp, which
is why Panel 2C gets the tighter `[-0.5, 0.5]`.

**Confirmed 2026-09-10 (live in Deneb):** both dumbbells render with the
zero-line fix; `#503E7A` zero line distinct from the `#1a1a1a` connector
and gridlines; Primary/Sensitivity legend correct; CI strings show on
hover only. Sizing is `"container"` on both, so the earlier
`720×300 / 740×300` vs `700×250` vs `735×150 / 950×150` position tangle is
moot — the visual container size is whatever the Power BI frame is, and
`03-page-specs.md`'s stale position table just needs its 2B/2C rows
updated to the built container X/Y/W/H (still open, Phase 3 close-out).
