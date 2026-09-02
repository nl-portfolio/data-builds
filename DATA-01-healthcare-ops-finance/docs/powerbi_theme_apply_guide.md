# Applying the "Clinical" Theme to the .pbix

Companion to `brand_style_guide.md`, `color_palette_healthcare.md`, `typography_system.md`.
Theme file: `powerbi/Healthcare Ops and Finance - Clinical Theme.json`.

Applies to: `powerbi/Healthcare Ops & Finance — SPARCS Inpatient Discharges 2024.pbix`
(the canonical copy, per project decision 2026-07-13).

---

## 1. Import the theme

1. Open the `.pbix` in Power BI Desktop.
2. **View** tab (ribbon) → **Themes** → **Browse for themes...**
3. Select `powerbi/Healthcare Ops and Finance - Clinical Theme.json`.
4. Power BI applies it to every page immediately: categorical colors, card/table/slicer
   backgrounds and borders, and Calibri across text classes (KPI numbers, panel titles,
   headers, labels).
5. Spot-check each of the six pages. A few visuals with manually-overridden colors
   (set directly on the visual rather than inherited from the theme) won't update
   automatically — reset those to theme default first: select the visual → Format
   visual (paint roller) → the relevant color property → **Revert to default**.
6. **Ctrl+S** to save. The theme is now embedded in the file.

## 2. Manual fix: Page 2 sequential ramps

The base theme can't express single-hue ordinal ramps, since `dataColors` is one flat
list Power BI cycles through for any categorical field. `apr_severity_of_illness` and
`apr_risk_of_mortality` need their own ramps set directly on two Page 2 visuals so order
reads at a glance instead of looking like five unrelated categories.

**For each visual:** select it → Format visual (paint roller icon) → **Data colors** →
if categories aren't listed individually, expand the section (or toggle "Show all") →
click each category's swatch → enter the hex below.

**Severity of illness** (teal ramp):

| Tier | Hex |
|---|---|
| Minor | `#C9E0DE` |
| Moderate | `#7FB8B4` |
| Major | `#3E8F8A` |
| Extreme | `#146C6C` |
| Undetermined | `#9AA5AF` |

**Risk of mortality** (red-orange ramp):

| Tier | Hex |
|---|---|
| Minor | `#F3D9CE` |
| Moderate | `#E3A489` |
| Major | `#D06B44` |
| Extreme | `#CC4A30` |
| Undetermined | `#9AA5AF` |

**Accessibility note:** the two lightest steps of each ramp (Minor, Moderate) fall
below the 3:1 graphical-contrast floor against a white card. If the visual type
supports a per-point border/outline (Format visual → Border or Outline), set it to
`#C9D2D8` (border-strong) at 1px. If not available on that visual type, leave as-is —
the text label on each bar/segment already carries the meaning, per the "color never
carries meaning alone" rule.

## 3. What the theme file already covers

- **Categorical colors:** the 8-color palette in palette-doc order (Navy → Taupe),
  so new visuals default to it and existing multi-category visuals re-flow into it
  on import.
- **Semantic colors:** `good` #2C8655, `neutral`/warn #9A6F18, `bad`/risk #CC4A30 —
  wired to Power BI's own good/neutral/bad theme slots (KPI indicators, gauges).
- **Typography:** Calibri across all four Power BI text classes — `callout` (KPI
  big numbers, 16pt), `title` (visual/panel titles, 12pt, secondary-text color,
  standing in for the H3 panel-title role), `header` (18pt, unchanged), `label`
  (9pt, general axis/data-label/legend text and table/matrix column headers and
  values). Note: Power BI's theme schema for `textClasses` only accepts
  `fontFace`, `fontSize`, and `color` — it rejected a `bold` property here
  (validation error on import), so weight for these four classes comes out
  regular by default. Bold *is* still applied via `visualStyles` on card KPI
  numbers and table/pivot header rows (see below), since visual-level style
  objects do support `bold`. If you want the H1 report title, H2 section
  headers, or H3 panel titles bold, set that directly on the text box / visual
  title in Power BI (Format visual → Title → Font).
  **2026-07-14 size update:** visual/chart/table titles set to 12pt; axis
  labels, data labels, legend text, and table/matrix column headers and values
  set to 9pt (both `textClasses.label` and the explicit `tableEx`/`pivotTable`
  overrides); KPI card callout value set to 16pt bold, KPI card label set to
  10pt regular. Slicer header/item sizes (13pt/12pt) were intentionally left
  unchanged — not part of this size pass.
- **Surfaces:** white card fill, `#F5F8F9` page canvas, `#EEF2F3` alternating/nested
  panel fill, `#E2E8EC` hairline borders on every visual by default.
- **Table/matrix/slicer styling:** header row fill and text, gridline color, and
  slicer header/item fonts all set to match.

## 4. What still needs a human eye

- The two Page 2 ramps above (can't be scripted into the base theme).
- Any visual with a manual color override from before the retrofit (won't inherit
  the theme until reverted to default, step 5 above).
- Small-caps / letter-spacing on H3 panel titles (`+0.04em`, uppercase) — Power BI's
  theme JSON has no text-transform or letter-spacing property, so this stays a
  visual/text-box-level manual touch if you want it to match the HTML mockup exactly.
- Icon set from the brand guide (section 5) is not part of this theme pass — it's a
  separate, optional addition (Power BI has no native icon system; would mean
  inserting SVG images per panel header).
