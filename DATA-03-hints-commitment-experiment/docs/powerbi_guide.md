# Power BI Build Guide — Commitment Statement Experiment Scorecard

**The single build document. Spec and click-path in one file.** Everything
builds from this document and the CSVs in `outputs/tables/`, except the five
Deneb chart specs, which live outside it: `powerbi/panelB_deneb_spec.json`
(Panel 1B) and `docs/deneb-specs/04-deneb-panel-2A-forest-plot.md`,
`05-deneb-panel-2B-2C-dumbbell.md`, `06-deneb-panel-3B-balance.md` (Panels 2A,
2B, 2C, 3B). Everything else is core Power BI. `powerbi/BUILD-INSTRUCTIONS.md`
is a pointer to this file.

This builds a **three-page experiment scorecard** from the pre-computed result
tables in `outputs/tables/`. The statistical analysis is finished and locked
(Phase 5b, `src/analysis.py`). The scorecard **displays** those results; it does
**not** recompute them from the respondent frame. Recomputing in DAX would
re-introduce exactly the unit-of-analysis risk that this whole sub-project
exists to correct — the withdrawn Phase 5 computed variance over ~2 million
item cells instead of 7,278 respondents. Load the answers, do not re-derive
them.

**Model philosophy:** flat result tables, almost no relationships, DAX used only
for display formatting and the MDE reference band. Every number a viewer sees
traces to a single cell in a CSV under `outputs/tables/`.

**Keys (read before §2).** Every table keyed by hypothesis carries a stable
`hypothesis_id` column with values `H1` / `H2` / `H3`. **Join on `hypothesis_id`,
never on a display label.** Display labels are for showing to a viewer; joining
on a label string once made `H2 break-off (web)` and `H2 break-off (web only)`
miss each other, so the join silently returned BLANK.
The colour of the verdict callout is likewise driven by a categorical column
(`verdict_class`, values `DETECTED` / `INFORMATIVE_NULL` / `UNDERPOWERED_NULL`),
not by searching the free-text `verdict` string.

---

## Before you start — open the project

Everything that carries analytical risk is already built and checked: the 11
result tables with correct types, the `primary_itt` to `mde` merge on
`hypothesis_id`, and all 22 DAX measures with their rationale attached as model
descriptions. What is left is placing visuals on the three report pages.

Double-click **`powerbi/HINTS7-Commitment-Scorecard.pbip`**.

Each of the 11 table queries reads its source CSV via a `File.Contents(...)`
call with the folder path spelled out directly in that query — there is no
single shared parameter. Each one currently reads:

```
<path-to-this-repo>\outputs\tables\
```

**After cloning this repo, update all 11 queries** (Power Query Editor >
Transform Data > select each of the 11 tables > Advanced Editor) so that path
points to wherever you cloned `outputs/tables/` on your machine. The 11
manual-fallback `.pq` scripts in `powerbi/manual-fallback/power-query/` do use
a named `TablesFolder` parameter if you set one up — that's the easier path if
you're rebuilding from the fallback scripts rather than opening the `.pbip`
directly. **Keep the trailing backslash** on whatever path you set.

### After the first refresh, check these four things

| Check | Expected |
|---|---|
| `primary_itt` row count | 3, with `observed_effect_pp` and `observed_effect_below_empirical_mde` merged on (§2) |
| `mode_subgroup[n_tx]` | Whole Number, blank on the two `web - paper (interaction)` rows (§1) |
| Model view > relationships | **none** — every table is deliberately unrelated (§1, §2) |
| `_Measures` | 22 measures in four display folders (§4) |

Turn **off** File > Options > Current File > Data Load > "Autodetect new
relationships" before any further Get Data (§1).

### If the project will not open

The semantic model is the hard part and it is also recoverable by hand. Use
`powerbi/manual-fallback/`:

- `power-query/*.pq` — paste each into Home > Transform data > New Source >
  Blank Query > Advanced Editor, and name the query exactly as the filename.
  Create the `TablesFolder` text parameter first, and load `mde` before
  `primary_itt` (the merge references it).
- `measures.dax` — create a `_Measures` table (Home > Enter data, name it
  `_Measures`, delete the blank column), then add each measure with the format
  string and display folder noted above it. The comment block above each one is
  its rationale; keep it in the measure description.

If you are building the model from scratch rather than opening the `.pbip`,
§1 through §4 below are the specification to build it from.

---

## 1. Load the data

**Get Data > Text/CSV**, from `outputs/tables/`, one file at a time. Turn off
autodetect relationships first (File > Options > Current File > Data Load >
uncheck "Autodetect new relationships after data is loaded") — the tables below
share column names (`hypothesis_id`, `hypothesis`, `p_uncorrected`) on purpose
and must stay unrelated. The only join you make by hand is the `mde` → `primary_itt`
merge in §2.

| File | Rows | Use |
|---|---|---|
| `primary_itt.csv` | 3 (H1, H2, H3) | the scorecard's main table |
| `mde.csv` | 3 | MDE reference band per hypothesis |
| `multiplicity_holm_m3.csv` | 3 | corrected p-values (pre-registered family) |
| `multiplicity_holm_m5.csv` | 5 | corrected p-values (supplementary family) — footnote only |
| `sensitivity_filter_missing.csv` | 3 | primary vs sensitivity strip (Filter-Missing rule) |
| `sensitivity_web_never_seen.csv` | 2 | footnote sensitivity strip (Web-Never-Seen denominator; spec NOT changed) |
| `mode_subgroup.csv` | 7 | pre-registered subgroup panel |
| `per_protocol.csv` | 4 | descriptive strip, permanently labelled NON-RANDOMISED |
| `balance.csv` | 8 | balance panel |
| `assertion_history.csv` | 31 | build-integrity footnote (all "passed") |
| `peeking_illustration.csv` | 20 | optional inset, labelled ILLUSTRATION |

**Column types — set in Power Query before Close & Apply:**

| Column(s) | Type |
|---|---|
| `hypothesis_id`, `verdict_class`, `hypothesis`, `verdict`, `flag`, `covariate`, `group`, `family`, `mode`, `spec`, `overrepresented_level`, all `*_ci_*` string columns | Text |
| `n_treatment`, `n_control`, `n`, `n_tx`, `n_ctl`, `levels`, `dof` | Whole Number |
| `rate_*_pct`, `difference_pp`, `diff_pp`, `relative_difference_pct`, `mde_*_pp`, `observed_*_pp`, `measured_deff`, `chi2`, `max_arm_share_gap_pp`, `ci_lo_pp`, `ci_hi_pp`, `ci_low_pp`, `ci_high_pp`, `treatment_share_pct`, `control_share_pct` | Decimal Number |
| `p_uncorrected`, `p_value`, `p_holm`, `holm_threshold`, `primary_p`, `sensitivity_p`, `fraction` | Decimal Number |
| `reject_at_familywise_0.05`, `sign_agrees`, `both_null_at_0.05`, `observed_effect_below_empirical_mde` | True/False |

**`mode_subgroup[n_tx]` and `[n_ctl]` need a two-step cast.** The CSV writes them
as floats (`1061.0`) and leaves them blank on the two `web - paper (interaction)`
rows, so a direct text-to-Whole-Number step errors. Apply `type number` first,
then `Int64.Type`:

```m
= Table.TransformColumnTypes ( Source, {{"n_tx", type number}, {"n_ctl", type number}} )
= Table.TransformColumnTypes ( #"Previous Step", {{"n_tx", Int64.Type}, {"n_ctl", Int64.Type}} )
```

The two blank interaction rows stay blank, and that is correct: an interaction is
a contrast between two cells, so it has no single arm n. Do not fill them with 0.

`hypothesis_id` is on `primary_itt`, `mde`, `multiplicity_holm_m3`,
`multiplicity_holm_m5`, `sensitivity_filter_missing`,
`sensitivity_web_never_seen`, `mode_subgroup`, `per_protocol` and
`peeking_illustration` (the last two are single-hypothesis tables — all rows
`H1`). `balance.csv` and `assertion_history.csv` are not hypothesis-keyed and
carry no `hypothesis_id`.

`primary_itt.csv` reports every rate and difference in **percentage points
already** (e.g. `difference_pp = -0.2129` means −0.21 pp). Do **not** multiply
by 100 again in DAX. `p_*` columns are probabilities in [0, 1].

No date table. This is a single cross-sectional experiment; no time
intelligence applies.

---

## 2. Relationships

One, optional, inactive-friendly: `primary_itt[hypothesis_id]` (1) to
`mde[hypothesis_id]` (1) — actually a 1:1, so instead of a relationship just
merge in Power Query (Merge Queries > join `primary_itt` to `mde` on
**`hypothesis_id`**).

**Expand only two columns: `observed_effect_pp` and
`observed_effect_below_empirical_mde`.** Do **not** expand `mde_empirical_pp`
or `mde_grid_formula_pp` — `primary_itt` already has both, with identical
values, and expanding the copies makes Power Query suffix them
(`mde_empirical_pp.1`) and every later reference to `primary_itt[mde_empirical_pp]`
ambiguous. The MDE values the measures in §4.2 read come from `primary_itt`'s
own `mde_empirical_pp` / `mde_grid_formula_pp` columns. `mde.csv` keeps its
duplicated columns because a reader may open it on its own.

**After expanding, rename both columns to drop Power Query's `mde.` prefix**, so
they read `primary_itt[observed_effect_pp]` and
`primary_itt[observed_effect_below_empirical_mde]`. Every reference in §4 and §5
uses the unprefixed names.

**`observed_effect_pp` is unsigned.** It is `ABS(difference_pp)`, so H1 is
`+0.2129` where `difference_pp` is `−0.2129`. Nothing in this layout plots it,
and nothing should: **plot `difference_pp`, never `observed_effect_pp`.** Panel
B's direction annotation depends on the sign, and a chart built off the unsigned
column would put H1's reduction on the wrong side of zero.

Leave every other CSV unrelated. The scorecard panels read their own table and
nothing filters through. Where a panel needs a value looked up from another
table by hypothesis (only §4.1's Holm measure does), the lookup is on
`hypothesis_id`, never on a label.

---

## 3. Slicers

**One slicer only:** `primary_itt[hypothesis]` (values: the three hypothesis
labels), set to **single-select**, defaulting to "H1 item nonresponse".

**Do not add any other slicer.** Specifically, **do not build a slicer on
survey mode, arm, agreement status, demographic group, stratum, or any
respondent attribute.** There is no respondent-level table in this model, by
design — see §1. A subgroup slicer would let the dashboard show a contrast the
locked analysis did not pre-register and did not make. The pre-registered mode
subgroup is shown as a fixed panel (§5, Panel 2A) with its results already
computed; it is not interactive.

---

## 4. DAX measures

Create a `_Measures` table (Home > Enter Data, name it `_Measures`, delete the
blank column). All measures below live there.

### 4.1 Selected-hypothesis scalars

```DAX
-- The main table has exactly one row per hypothesis, so SELECTEDVALUE returns
-- the single value under the current slicer selection (and BLANK if the user
-- multi-selects, which the slicer is configured to disallow anyway).
Effect (pp) = SELECTEDVALUE ( primary_itt[difference_pp] )

Effect CI (pp) = SELECTEDVALUE ( primary_itt[ci_difference_pp] )   -- string, exactly as the cell reads, e.g. "[-0.437, 0.012]"

-- Numeric CI bounds of the difference, for Panel 1B whiskers. Native columns on
-- primary_itt (Phase 5c) -- no string parsing needed.
CI Low (pp)  = SELECTEDVALUE ( primary_itt[ci_low_pp] )
CI High (pp) = SELECTEDVALUE ( primary_itt[ci_high_pp] )

Rate Treatment (%) = SELECTEDVALUE ( primary_itt[rate_treatment_pct] )
Rate Control (%)   = SELECTEDVALUE ( primary_itt[rate_control_pct] )

N Treatment = SELECTEDVALUE ( primary_itt[n_treatment] )
N Control   = SELECTEDVALUE ( primary_itt[n_control] )

p (uncorrected) = SELECTEDVALUE ( primary_itt[p_uncorrected] )

-- Corrected p from the PRE-REGISTERED family (m = 3). Looked up by
-- `hypothesis_id` (never the label), so it is correct regardless of visual and
-- immune to any label wording drift between the two tables.
p (Holm, pre-registered family) =
CALCULATE (
    SELECTEDVALUE ( multiplicity_holm_m3[p_holm] ),
    TREATAS ( VALUES ( primary_itt[hypothesis_id] ), multiplicity_holm_m3[hypothesis_id] )
)

Verdict = SELECTEDVALUE ( primary_itt[verdict] )
```

**The verdict callout binds to `primary_itt[verdict_vis]` directly, not through
a measure** (§5.1, Panel 1A). That column carries the reader-facing verdict
string. There is no `[Verdict Display]` measure. `[Verdict]` above is the
auditable raw value and belongs in the card's tooltip, not on its face.

### 4.2 MDE band — the most important object on the page

```DAX
-- Empirical MDE = 2.8 x SE(difference), the honest per-arm minimum detectable
-- effect at 80% power. This is what the experiment could actually detect for
-- this outcome. Displayed as a symmetric band +/- this value around zero.
MDE (empirical, pp) = SELECTEDVALUE ( primary_itt[mde_empirical_pp] )

-- The pre-registration grid's own formula, evaluated at the observed baseline
-- with Phase 4b's MEASURED design effect substituted. Shown as a second,
-- wider reference line so a viewer sees both "what the plan assumed" and
-- "what the data delivered".
MDE (grid formula, pp) = SELECTEDVALUE ( primary_itt[mde_grid_formula_pp] )

MDE band lower = -1 * [MDE (empirical, pp)]
MDE band upper =      [MDE (empirical, pp)]

-- TRUE when the observed effect is inside the band, i.e. smaller than what the
-- experiment could detect. Reads the stored flag; it does NOT re-derive
-- ABS(effect) < MDE in DAX, which would be a recomputation §7 prohibits.
-- [Verdict Colour] drives the callout colour, off `verdict_class`; this
-- measure is for the Panel 1B band annotation only.
Effect within MDE = SELECTEDVALUE ( primary_itt[observed_effect_below_empirical_mde] )

-- Categorical verdict class, emitted by src/analysis.py from the same branch
-- that writes the prose `verdict`. One of "DETECTED", "INFORMATIVE_NULL",
-- "UNDERPOWERED_NULL". This is what the colour switches on.
Verdict Class = SELECTEDVALUE ( primary_itt[verdict_class] )

-- Exact-match SWITCH on the categorical column. No substring search on prose
-- anywhere: SEARCH("DETECTED", [Verdict]) is case-insensitive and matches
-- "could not have detected it" in the H2/H3 verdict strings, which would
-- colour two null results as detected effects. Colour keys on the class, never
-- on English prose.
Verdict Colour =
SWITCH (
    [Verdict Class],
    "DETECTED",          "#C0504D",   -- red: effect distinguishable from zero
    "INFORMATIVE_NULL",  "#4F6228",   -- green: null, and a meaningful effect could have been detected
    "UNDERPOWERED_NULL", "#E36C0A",   -- amber: null, but a plausible effect could not have been detected
    "#E36C0A"                          -- amber fallback (no verdict_class should be outside the three above)
)
```

**How `verdict_class` is assigned — and which part of it is the pre-registered
rule.** For the **primary** hypothesis (H1) the class is emitted by
`src/analysis.py` from the same branch of the pre-registered verdict rule that
writes the prose `verdict`: `INFORMATIVE_NULL` when the observed effect is below
the MDE and the MDE is under the plan's 3 pp informativeness bar, `DETECTED` when
the CI excludes zero at ≥ 3 pp. For the **secondary** hypotheses (H2, H3),
`UNDERPOWERED_NULL` is a **conservative presentation convention, not the
pre-registered rule**: the plan's informative / underpowered dichotomy and its
3 pp bar were written for the primary outcome and are meaningless against H2's
4.3 pp empirical MDE and H3's 0.36 % baseline. The convention never colours a
null as a detected effect. Any verdict path the locked plan does not cover (a
secondary passing uncorrected p but not Holm; an H1 effect in the 3–5 pp
indeterminate MDE band) **raises in `src/analysis.py`** rather than emitting a
class — so `verdict_class` is only ever one of the three values above, and the
amber fallback line in the `SWITCH` is unreachable by construction.

**On the two MDE numbers (`1.8` vs `1.203`).** The pre-registration's tabulated
Family A grid lists **1.8 pp** as its smallest MDE, at an *assumed* 5 % baseline
nonresponse rate. `mde_grid_formula_pp` on `primary_itt` is **1.203 pp**: the
*same* formula (`2.8·√(p(1−p)(1/nₜ+1/nᴄ))·√DEFF`) re-evaluated at the *observed*
1.44 % control-arm baseline with Phase 4b's measured design effect. Different
inputs, so a different number. This guide and the dashboard use **1.203**
throughout — the value that matches the realised data. Where `RESULTS.md` prose
says "grid's smallest MDE 1.8 pp" it means the tabulated grid row, not this
cell; both statements are correct.

### 4.3 Display strings

```DAX
Effect Label =
VAR s = IF ( [Effect (pp)] >= 0, "+", "" )
RETURN s & FORMAT ( [Effect (pp)], "0.00" ) & " pp   " & [Effect CI (pp)] & " pp"

Arms Label =
"Treatment n = " & FORMAT ( [N Treatment], "#,0" ) &
"   |   Control n = " & FORMAT ( [N Control], "#,0" )

p Label =
"p = " & FORMAT ( [p (uncorrected)], "0.000" ) & " uncorrected   |   " &
"p = " & FORMAT ( [p (Holm, pre-registered family)], "0.000" ) & " Holm (family of 3)"

-- Both arm rates carry their own CI. No point estimate goes on this page
-- without its interval. `ci_treatment_pct` / `ci_control_pct` are pre-formatted
-- strings on `primary_itt`; print them, do not parse them.
Rates Label =
"Treatment " & FORMAT ( [Rate Treatment (%)], "0.00" ) & "% " &
    SELECTEDVALUE ( primary_itt[ci_treatment_pct] ) & "   vs   " &
"Control "  & FORMAT ( [Rate Control (%)], "0.00" ) & "% " &
    SELECTEDVALUE ( primary_itt[ci_control_pct] )
```

---

## 5. Layout — three report pages

Canvas **1600 x 1000** on every page, "Fit to page". Positions are
`x, y, width, height`.

The nine panels and where they live:

| Panel | Page | Role | Visual |
|---|---|---|---|
| 1A | 1 — Scorecard | Headline + verdict callout | Cards + callout |
| 1B | 1 — Scorecard | Effect vs. MDE (anchor visual) | Deneb — error-bar / dot plot |
| 2A | 2 — Robustness | Pre-registered subgroup — mode | Deneb — forest plot |
| 2B | 2 — Robustness | Filter-Missing sensitivity | Deneb — dumbbell |
| 2C | 2 — Robustness | Web-Never-Seen sensitivity (footnote) | Deneb — dumbbell |
| 3A | 3 — Appendix | Multiplicity strip | Text box + 3 cards |
| 3B | 3 — Appendix | Balance check (post-hoc) | Deneb — dot plot |
| 3C | 3 — Appendix | Per-protocol (non-randomised) | Table |
| 3D | 3 — Appendix | Peeking illustration (optional) | Native line chart |

The five Deneb chart specs live outside this file: `powerbi/panelB_deneb_spec.json`
(Panel 1B) and `docs/deneb-specs/04-deneb-panel-2A-forest-plot.md`,
`05-deneb-panel-2B-2C-dumbbell.md`, `06-deneb-panel-3B-balance.md` (Panels 2A,
2B, 2C, 3B).

### 5.0 Page chrome colors

Chrome palette, from Neyda's brand style guide
(`brand-guidelines/brand-style-guide.md`); `powerbi/Theme.json` sets fonts
only. Full swatches also in the "Scorecard Color Key" reference.

**Chrome only. Never touches the verdict, balance, or panel chart colors in
§4.2 and the Deneb specs.** Those stay exactly as built — DAX-tied, reused
across Panels 1B, 2A, 2B, 2C, 3B.

| Role | Hex | Used for |
|---|---|---|
| Background | `#faf8f5` | Report canvas, all 3 pages |
| Card | `#ffffff` | Panel/card surface backgrounds |
| Ink | `#1a1a1a` | Titles, panel headers, primary body text |
| Muted | `#5c5c5c` | Sub-titles, captions, footers, header sub-lines |
| Line | `#e6e2dc` | Card borders, dividers |
| Accent | `#503e7a` | Outlined provenance tags (below), section labels |
| Accent Dark | `#291752` | Filled provenance tag text |
| Accent Soft | `#ece7f5` | Filled provenance tag background |

**Provenance tag system — three tiers, one hue family, no red/green/amber.**
Every panel or legend that flags a data-provenance claim ("not
pre-registered," "post-hoc," "footnote," "non-randomised," "illustration")
uses brand accent purple, never the verdict colors — red, green, and amber
mean something specific in §4.2 and must never mean anything else on this
report. The three tiers are told apart by weight, not hue:

1. **Pre-registered — the default, no flag needed.** Ink `#1a1a1a` text, no
   chip.
2. **Post-hoc / footnote** (Panel 3B's title, Panel 2C's title). Filled chip:
   Accent Soft `#ece7f5` background, Accent Dark `#291752` text.
3. **Not randomised / illustration** (Panel 3C's title, Panel 3D's title —
   the strongest caution). Outlined chip: transparent background, 1.5px
   Accent `#503e7a` border and text.

**A provenance tag never uses red.** Red is reserved for the DETECTED verdict
color (§4.2) and Panel 3B's IMBALANCED marks. A reader seeing red text should
read "an effect was detected," never "don't read this causally" — so the
not-randomised tier (page 3 legend, Panel 3C and 3D titles) is purple, not red.

### 5.1 Page 1 — Scorecard

| # | Panel | Position | Visual |
|---|---|---|---|
| — | Title | 0, 0, 1600, 60 | Text box |
| — | Sub-title | 0, 60, 1600, 45 | Text box |
| — | Slicer | 10, 115, 215, 205 | Slicer, `primary_itt[hypothesis]` (§3) |
| — | Provenance legend | 10, 330, 215, 120 | Text box — one tier only, see below |
| 1A | Headline | 235, 115, 1355, 140 | Cards + callout |
| 1B | Effect vs. MDE | 235, 265, 1355, 560 | Deneb (`powerbi/panelB_deneb_spec.json`) |
| — | Footer | 235, 845, 1355, 90 | Text box |

No slicer sync to pages 2–3 — confirm the Sync Slicers pane shows this slicer
applied to page 1 only.

Title bar (color: Ink `#1a1a1a`, canvas behind it: Background `#faf8f5`):
**"Did a commitment statement improve HINTS 7 data quality?"**
Sub-title (static text box, color: Muted `#5c5c5c`): *"Pre-registered RCT,
HINTS 7 (2024). Plan locked and publicly committed 2026-09-02 (commit
238c6c8) before any arm-split statistic was computed. Intention-to-treat:
assigned to the statement arm (n = 1,513) vs everyone not assigned
(n = 5,765)."*

Left rail: the single `hypothesis` slicer (§3) and the static provenance legend
below.

**Provenance legend (static text box, left rail).** Page 1 carries only
pre-registered material, so the legend is one tier:
*"PRE-REGISTERED — everything on this page."* (color: Ink `#1a1a1a`, no
chip — this is the default tier, §5.0). Add one line beneath it, in Muted
`#5c5c5c`: *"Post-hoc and descriptive panels are on pages 2–3."* The full
three-tier legend (pre-registered / post-hoc / not-randomised) moves to page
3 (§5.3), where all three provenance classes actually appear together.

### Panel 1A — Headline (top, full width)

Four card visuals stacked, then a callout on the right:

1. **`[Effect Label]`** — the big number, e.g. `-0.21 pp   [-0.437, 0.012] pp`.
   Font colour: conditional formatting > **Format by field value** >
   `[Verdict Colour]`.
2. **`[Rates Label]`** — each arm rate with its CI, so this card is wide.
3. **`[Arms Label]`**
4. **`[p Label]`**
5. **Callout card, right-aligned: `primary_itt[verdict_vis]`** — bound
   directly to the column (no measure in between, §4.1), on the
   `[Verdict Colour]` background. For H1 this currently reads "No effect on
   item nonresponse (−0.21 pp). The study could reliably detect changes
   this small — this is a real null, not an inconclusive test." (Corrected
   2026-09-15 — the previous quote in this section, "INFORMATIVE NULL
   (observed effect < MDE, MDE < 3 pp)", was the pseudocode-style wording
   from an earlier build pass and no longer matches the live
   `verdict_vis` string; see `docs/decisions.md`, 2026-09-15.)

**Do not put `[Verdict]` on the card.** H1's raw string leads with the rule
expression `DISCONFIRMING (rates within 1 pp, or CI spans both directions) ->
NULL;`, which renders as pseudocode with an ASCII arrow on the primary outcome's
headline while H2 and H3 render as sentences. `[Verdict]` stays in the model as
the auditable raw value and belongs in the card's tooltip, not its face.

For H1 the headline reads `-0.21 pp   [-0.437, 0.012] pp` in green
(`INFORMATIVE_NULL`). Green here means *the null is informative*, not *good
news* — the callout text says which, so do not shorten it.

### Panel 1B — Effect vs. MDE (full width)

Full width at `235, 265, 1355, 560`. Spec: `powerbi/panelB_deneb_spec.json`.

**Tooling — read before you start this panel.** Panel 1B cannot be built with a
core Power BI visual. It needs a shaded band whose width differs per row (H1
0.32 pp, H2 4.27 pp, H3 0.12 pp), and an Analytics-pane constant line carries one
value for the whole visual, not one per category. Two options, in order of
preference:

1. **Deneb** (Vega-Lite custom visual, AppSource, free). This is what the build
   uses. The spec is written and ready at `powerbi/panelB_deneb_spec.json`;
   install Deneb, drop it on the page, and paste the spec. Everything below is
   already encoded in it.
2. **Native fallback**, if a custom visual cannot be installed: three separate
   single-row charts stacked, each with its own constant-line pair at that row's
   MDE. This loses the shared axis, which is most of the panel's value, so take
   it only if option 1 is unavailable.

**Building it with Deneb, step by step:**

1. Visualizations pane > Get more visuals > search "Deneb" (free, certified,
   AppSource). Drop a Deneb visual into the Panel 1B slot.
2. Into **Values**, drag these `primary_itt` columns, in this order:
   `hypothesis`, `difference_pp`, `ci_low_pp`, `ci_high_pp`, `mde_empirical_pp`,
   `mde_grid_formula_pp`, `verdict_class`. Set each numeric one to **Don't
   summarize**.
3. Edit > paste the contents of `powerbi/panelB_deneb_spec.json` into the
   Specification pane. Provider: Vega-Lite.

All three rows show at once — the visual is deliberately **not** driven by the
slicer, so a viewer sees the whole pre-registered set together.

`outputs/figures/panelB_preview.png` is this exact spec rendered against
`primary_itt.csv` outside Power BI. The built visual should match it.

**Caption under the panel:**

> Shaded band = the empirical MDE, the smallest effect this experiment could
> have detected at 80% power. Dashed pair = the pre-registration grid formula
> re-evaluated at the observed baseline. **A dot inside the band means the
> experiment could not have resolved an effect that small.** Negative =
> the commitment statement reduced the failure rate, which is the direction H1
> predicted — not a reversal.

**Do not narrow the x-axis.** It is fixed at ±5.5 pp so H2's interval fits and so
H1's 0.21 pp effect stays visibly small. Shrinking the axis to make the effect
look large is the failure mode a reviewer checks for first.

**Specification.** A horizontal **error-bar / dot plot**, one row per hypothesis (use all three
rows of `primary_itt`, not the slicer selection, so the viewer sees the whole
pre-registered set at once):

- x-axis: percentage points, centred on 0, symmetric range at least
  ±5 pp so H2's CI fits.
- Dot at `difference_pp`, whiskers from `ci_low_pp` and `ci_high_pp` —
  numeric Decimal columns already on `primary_itt` (Phase 5c). Nothing to
  parse. Ignore the `ci_difference_pp` string for plotting; it is there for
  humans.
- **A shaded vertical band from `MDE band lower` to `MDE band upper`** behind
  the dots, per row, drawn with the `[MDE (empirical, pp)]` measure. This is
  the reference the whole page is built around: **if the dot and its whole CI
  sit inside the band, the experiment could not have detected an effect that
  small, and the label on the band must say so.** Add a second, lighter pair
  of reference lines at `± [MDE (grid formula, pp)]` labelled "pre-registration
  grid MDE".
- A solid line at x = 0 labelled "no effect".
- Direction annotation under the axis: *"negative = commitment statement
  reduced the failure rate (the predicted direction)"*. Do **not** label a
  negative effect a "reversal" — a reduction is what H1 predicted.

If the result is a null (it is), the MDE band is the most important object on
this page. Make it visually dominant: fill it, label it, and put its numeric
value (`0.32 pp` for H1) in the annotation.

Page 1 footer (`235, 845, 1355, 90`, Muted `#5c5c5c`): *"31/31 estimates
passed the implied-n guard. Full validation:
`outputs/phase6_validation_reference.md`. Robustness checks: page 2.
Appendix: page 3."* The full build-integrity footnote is on page 3 (§5.3).

---

### 5.2 Page 2 — Robustness (pre-registered only)

| Element | Position | Visual | Source |
|---|---|---|---|
| Header | 0, 0, 1600, 50 | Text | "Robustness — pre-registered checks" (color: Ink `#1a1a1a`) |
| Header sub-line | 0, 46, 1600, 26 | Text | "One exception, tagged below: Panel 2C is a footnote check, not pre-registered." (color: Muted `#5c5c5c`) |
| Panel 2A — Mode subgroup | 60, 100, 1480, 430 | Deneb (forest plot) | `mode_subgroup.csv`. Spec: `docs/deneb-specs/04-deneb-panel-2A-forest-plot.md` |
| Panel 2A caption | 60, 535, 1480, 40 | Text | see below |
| Panel 2B — Filter-missing | 60, 555, 720, 300 | Deneb (dumbbell) | `sensitivity_filter_missing.csv`. Spec: `docs/deneb-specs/05-deneb-panel-2B-2C-dumbbell.md` |
| Panel 2B caption | 60, 860, 720, 40 | Text | see below |
| Panel 2C — Web-never-seen | 800, 555, 740, 300 | Deneb (dumbbell) | `sensitivity_web_never_seen.csv`. Same spec file as Panel 2B. **Title carries a tag — see below** |
| Panel 2C caption | 800, 860, 740, 40 | Text | see below |
| Footer pointer | 60, 910, 1480, 50 | Text | "Balance, per-protocol, multiplicity, and the peeking check continue on page 3." |

No slicer on this page at all — every panel shows its complete row set,
unfiltered, always (§3: one slicer, page 1 only).

**Panel 2C is not pre-registered.** Panel 2A (mode subgroup) and Panel 2B
(Filter-Missing) were both committed in `docs/pre-registration.md` in
advance. Panel 2C, the Web-Never-Seen check, was not — it came from a
denominator-construction discrepancy found after the frame was built
(`docs/decisions.md`, Phase 3b finding / Phase 5b decision 4): the
pre-registration's table said Web-Never-Seen items should be excluded from
Family A's denominator, the as-built code didn't, and the ruling was to keep
the as-built version and report the literal pre-registration wording as a
**"footnote sensitivity."** It stays on this page, but its title carries a
visible tag (below) and the header sub-line names the exception.

### Panel 2A — Pre-registered mode subgroup

Deneb forest plot from `mode_subgroup.csv`: `family`, `mode`, `diff_pp`,
`ci_lo_pp`, `ci_hi_pp`, `p_value`, `n_tx`, `n_ctl`. Visual header:
**"Pre-registered subgroup — mode"**.

Caption (color: Muted `#5c5c5c`): *"Collider caveat: mode is measured after
randomisation and differs by arm in the responding sample (page 3, Panel 3B)
— these are descriptive cells, not de-confounded effects. The pooled ITT
estimate (page 1) is the unbiased reference."*

**Colour rule — flat, never on `p_value`.** Every point is one flat colour
(`#404040`): nothing in this panel may imply significance through colour. The
two interaction-contrast rows (`mode = web - paper (interaction)`) are
distinguished by shape (diamond vs. circle) instead. The paper-cell Family A
row (p = 0.0289) is not a finding; it is a stratified cell that does not
survive multiplicity, and the caption says so.

The CSV has 7 rows; its own order groups by family (A, A, C, C, B, then the
two `web - paper (interaction)` rows), so the spec's `"sort": null` preserves
it. X-axis domain is `[-2, 5.5]` — the H2 break-off row's CI runs to +4.80 pp.

### Panels 2B & 2C — Sensitivity strip (two Deneb dumbbells)

Same spec, two instances bound to different source tables. One dot for the
primary estimate, one for the sensitivity estimate, a connecting line between
them, both CI strings shown in the tooltip. **The CI columns
(`primary_ci_pp`, `sensitivity_ci_pp`) are pre-formatted strings — never
parsed into numeric whiskers**; the dumbbell's connector satisfies "no point
estimate without its interval" without deriving a new number.

Both captions in Muted `#5c5c5c`.

- **Panel 2B caption:** *"Filter-Missing coding (pre-registered dual
  spec). Sign and magnitude agree with the primary estimate for all three
  hypotheses; neither H1 reading survives Holm."*
- **Panel 2C caption:** *"Web-Never-Seen denominator (footnote check;
  specification not changed). Excluding these cells takes H1 from −0.21 pp to
  −0.10 pp — same direction, null gets clearer."*

**Panel 2C's title carries a visible tag; Panel 2B's does not.** Set Panel
2C's visual title (Power BI's own title field, same mechanism Panel 3B uses
on page 3) to **"Web-Never-Seen — FOOTNOTE, NOT PRE-REGISTERED."** Style it
as the §5.0 tier-2 filled chip: Accent Soft `#ece7f5` background, Accent Dark
`#291752` text — never the verdict colors. Panel 2B keeps a neutral title
("Filter-Missing sensitivity" or similar) in Ink `#1a1a1a`, no chip — it
*is* pre-registered. The caption is easy to skim past; the title tag isn't,
so the tag carries the distinction.

Diff values range −0.27 pp to 1.82 pp; the spec's `[-1.5, 2.5]` domain
covers them.

---

### 5.3 Page 3 — Appendix (post-hoc & descriptive)

| Element | Position | Visual | Source |
|---|---|---|---|
| Header | 0, 0, 1600, 50 | Text | "Appendix — post-hoc & descriptive" (color: Ink `#1a1a1a`) |
| Legend | 0, 50, 1600, 40 | Text | Two tiers: "POST-HOC — Panel 3B" (filled Accent chip) and "NOT RANDOMISED / ILLUSTRATION — Panel 3C, Panel 3D" (outlined Accent chip) — see §5.0 tag system |
| Panel 3A — Multiplicity | 60, 110, 1480, 110 | Text + 3 Cards | see below |
| Panel 3B — Balance | 60, 240, 1480, 340 | Deneb (dot plot) | `balance.csv`. Spec: `docs/deneb-specs/06-deneb-panel-3B-balance.md` |
| Panel 3B caption | 60, 590, 1480, 40 | Text | verbatim below, Muted `#5c5c5c` |
| Panel 3C — Per-protocol | 60, 640, 700, 230 | Table | `per_protocol.csv` |
| Panel 3D — Peeking inset (optional) | 800, 640, 740, 230 | Line chart (native) | `peeking_illustration.csv` — **build decision pending**, see note |
| Footer | 60, 880, 1480, 90 | Text | build-integrity footnote, verbatim below, Muted `#5c5c5c` |

Panels 3C and 3D sit at `y=640, h=230` — clear of the Panel 3B caption above
(ends `y=630`) and the footer below (starts `y=880`).

**Panel 3D — build or skip is still open.** It is the one optional panel.
Whether 740×230 next to Panel 3C reads clearly is a judgment call for the
rendered page — build Panel 3C first, confirm page 3 reads cleanly, then add
Panel 3D only if there is real room left.

**Provenance legend (page 3, full three tiers).** All three provenance
classes appear together here, so page 3 carries the legend page 1 dropped.
No red — nothing here can be misread as the DETECTED verdict color:

| Swatch | Label | Panels |
|---|---|---|
| Ink `#1a1a1a` text, no chip | **PRE-REGISTERED** — in the locked plan, commit `238c6c8` | 3A |
| Filled chip — Accent Soft `#ece7f5` bg, Accent Dark `#291752` text | **POST-HOC** — not pre-specified, reported for completeness | 3B |
| Outlined chip — transparent bg, 1.5px Accent `#503e7a` border and text | **NOT RANDOMISED / NOT EVIDENCE** — descriptive or illustrative only | 3C, 3D |

### Panel 3A — Multiplicity (sentence + 3 chips)

One text box (full width, color: Ink `#1a1a1a` — this panel is
pre-registered, tier 1, no chip): *"Holm-Bonferroni over the three pre-registered outcome families. The
correction family is fixed by the plan, not by how many tests completed.
None of the three survive; adding the two pre-registered mode-interaction
tests (family of 5) changes nothing."*

Below it, three small Card visuals side by side (~480 wide each), one per
hypothesis, each bound to `multiplicity_holm_m3[p_holm]` with a
**visual-level filter** `hypothesis_id = H1` / `H2` / `H3`. Card labels:
"H1 — Holm p.", "H2 — Holm p.", "H3 — Holm p." No chart, no table — three
numbers and one sentence don't need an axis.

### Panel 3B — Balance

Deneb dot plot. Visual title (Power BI's own title field): **"POST-HOC — NOT
PRE-REGISTERED"** — this is the page's only post-hoc panel, and without the
tag its one red `IMBALANCED (p<0.01)` row reads as a finding the analysis did
not make. Style the title as the §5.0 tier-2 filled chip: Accent Soft
`#ece7f5` background, Accent Dark `#291752` text — a different purple, not a
lighter red, so it can't be read as a second verdict color next to the
chart's own `#4F6228`/`#C0504D` marks.

From `balance.csv`: `covariate`, `p_value`, `max_arm_share_gap_pp`,
`overrepresented_level`, `treatment_share_pct`, `control_share_pct`, `flag`.
Plots `max_arm_share_gap_pp` directly — an existing column, nothing computed.
**Colour bound to `flag` only, never `p_value`** — same rule as Panel 2A.

The caption's "70.1% vs 65.9% web" must trace to cells, not to `RESULTS.md`
prose: on the `Survey mode (FormType)` row, `overrepresented_level` =
`HINTS7, standard version - web`, `treatment_share_pct` ≈ 70.1,
`control_share_pct` ≈ 65.9.

Caption (Muted `#5c5c5c`): *"Deferred from Phase 1. Covariate set not
pre-specified. **This check is conditional on response** — every covariate,
survey mode included, is measured after randomisation, so a gap is a finding
about the responding sample, not evidence randomisation failed (Phase 1
identified the arm flag by an independent route). 7 of 8 balanced including
the design stratum; survey mode differs (`treatment_share_pct` 70.1% vs
`control_share_pct` 65.9% web, p = 0.002) — reported, not adjusted, and not a
reason to reopen Phase 1. The effect is null within each mode (Panel 2A), so
the imbalance does not drive the result."*

`max_arm_share_gap_pp` ranges 0.78 to 4.21 pp (the 4.21 is the survey-mode
row); the spec's `[-6, 6]` domain covers it.

### Panel 3C — Descriptive per-protocol

From `per_protocol.csv`. Visual title: **"NON-RANDOMISED — NOT CAUSAL"**,
styled as the §5.0 tier-3 outlined chip (transparent background, 1.5px Accent
`#503e7a` border and text). Caption (color: Muted `#5c5c5c`): *"Among the
statement arm: those who agreed show lower item nonresponse than those who
did not (1.17% vs 1.86%). This is selection, not effect — agreement tracks
engagement and education. Descriptive only. The 14 who declined are
described, not tested."* Its fourth row (`Declined only`, n = 14) has blank
rate cells by design — leave it blank and leave the row in; it is the only
on-page evidence that 14 people declined. Turn totals off — this is the only
table in the build.

### Panel 3D — Peeking illustration (optional)

If built (see the build-or-skip note above): native line chart from
`peeking_illustration.csv` (`fraction` on x, `p_value` on y, reference line
at 0.05). Title: **"ILLUSTRATION — NOT EVIDENCE"**, same §5.0 tier-3
outlined chip as Panel 3C — transparent background, 1.5px Accent `#503e7a`
border and text.

**Fix the y-axis to 0 to 1.** Do not let it auto-scale. The series ranges
0.063 to 0.999 and never crosses 0.05, so an auto-scaled axis would zoom the
bottom of the range and make the trajectory look as though it approaches
significance. Panel 1B is the only other visual with a fixed axis, for the
same reason.

Caption (color: Muted `#5c5c5c`): *"Cumulative H1 p-value under a seeded-random respondent order. The
p-value never falls below 0.05 here; what the series actually shows is a sign
reversal — the effect reads +0.17 pp at 10% of the sample and −0.21 pp at 100%.
That is the noise repeated looking would expose you to. Not an inference."*

### Build-integrity footnote (page 3 footer)

Color: Muted `#5c5c5c`, same as every other footer/caption on this build.

*"All 31 estimates logged in `assertion_history.csv` passed the
`implied_n ≤ respondents` guard; `implied_n / n` ranged 0.16–0.79. (The 31 rows
are the pre-registered ITT and subgroup estimates plus the pooled, Filter-Missing
and Web-Never-Seen sensitivity estimates the guard also ran on; an earlier draft
of this footnote said 27, before the Web-Never-Seen block was added.) Arm-split
rates and SEs reproduced three ways (weighting.py, from-scratch numpy, R survey)
to 6 decimal places. Withdrawn Phase 5 figures (H1 z = −13.14, H3 z = −3.53) are
superseded."*

### Page-wide: turn totals off on the one remaining table

Panel 3C is the only table visual in the build — Panels 3A, 2A, 2B, 2C, 3B
are chips, charts, or cards. Open Format > Column headers / Totals and set
**Totals: Off**. Two reasons: the §4 measures return BLANK at a totals row,
and every column here is one Power BI must not add up. Confirm it in the §7
prohibition pass before export.

---

## 6. Known pitfalls (from DATA-01, mapped to this build)

1. **`ALL()` / `ALLSELECTED()` scope bugs.** DATA-01 hit two. Here the defence
   is structural: there is **no respondent grain and no measure iterates a
   table**. Every measure is a `SELECTEDVALUE` or a `CALCULATE` +
   `TREATAS` lookup over a 3–8 row table. Do not "improve" any measure into a
   `SUMX`/`FILTER`/`RANKX` over `ALL(...)` — there is nothing to iterate and it
   would only create a scope bug.

2. **`ALLSELECTED` vs a visual/Filters-pane filter.** DATA-01's KPI card read
   1.00 forever because `ALLSELECTED` treated a visual-level filter like a
   slicer. Mitigation here: the only slicer is `hypothesis`, and
   `p (Holm, pre-registered family)` uses `TREATAS ( VALUES ( primary_itt[
   hypothesis_id] ), … )` — it follows the slicer selection explicitly (via
   the id column, one per row) rather than relying on `ALLSELECTED`. If you add
   a visual-level filter on `hypothesis` to any card, that measure still
   resolves correctly because `VALUES` picks up whatever is in context. Do not
   switch it to `ALLSELECTED`.

3. **Measures that must NOT be re-scoped by a slicer.** `[MDE (empirical, pp)]`,
   `[Effect (pp)]`, `[p (uncorrected)]`, `[p (Holm, pre-registered family)]`,
   `[Verdict]` are all keyed to the single `hypothesis` selection and nothing
   else. If a second slicer is ever added (it must not be — §3), these would
   silently start returning BLANK when the extra slicer excluded the row.
   There is no "mode" or "arm" column on `primary_itt` for a slicer to bite,
   which is the point.

4. **Percentage-point columns are already in pp.** `difference_pp = -0.2129`
   is −0.21 pp. `p_*` columns are in [0, 1]. Format `p_*` with `"0.000"`, the
   pp columns with `"+0.00;-0.00"`. A stray `* 100` here would turn a −0.21 pp
   null into a −21 pp headline — the same order-of-magnitude class of error the
   sub-project is correcting.

5. **Text CI columns.** `ci_difference_pp`, `primary_ci_pp`, `sensitivity_ci_pp`
   are strings, kept for human display only. **For the Panel 1B whiskers, use
   the numeric `ci_low_pp` / `ci_high_pp` columns on `primary_itt`** (Phase 5c
   emits them from `analysis.py`). Do not parse the strings in Power Query or
   DAX. The sensitivity panels (2B, 2C) display their CI strings as text and never
   plot them, so they need no numeric split.

---

## 7. What must not be built

- **No slicer, filter, drill-through, or parameter that subsets the scorecard
  to a subgroup the pre-registration did not name** — no arm, mode, agreement
  status, age, sex, race, education, income, stratum, or item-level cut. The
  model has no respondent table specifically so this is impossible by
  construction; keep it that way.
- **No recomputation of any rate, SE, p-value, or MDE in DAX from a
  respondent-level source.** The numbers are locked in `outputs/tables/`. The
  scorecard is a display of a finished analysis.
- **No "significance" styling that implies a detected effect.** Every headline
  here is a null. The verdict colour for H1 is green (informative null), not
  red. Do not add a "★ significant" flag, a green up/down arrow on the effect,
  or traffic-light KPI that reads a 0.063 p-value as a near-miss worth chasing.
- **No conditional format keyed on a p-value, anywhere on the page.** Colour on
  the categorical column that already carries the verdict (`verdict_class`,
  `flag`, `reject_at_familywise_0.05`, the literal `mode` string), never on how
  small a number is. Formatting on `p_value` would light up `mode_subgroup`'s
  paper-cell row (p = 0.0289) and nothing else, manufacturing the one finding the
  analysis declined to make.
- **No auto-scaled axis on any visual that shows an effect or a p-value.**
  Panel 1B's x-axis is fixed at ±5.5 pp and Panel 3D's y-axis at 0 to 1. An
  axis fitted to the data makes a 0.21 pp effect fill the frame.
- **No totals row on any table visual.** Every column here is one that must not
  be summed.
- **No point estimate without its interval.** Panel 1A's rates carry
  `ci_treatment_pct` / `ci_control_pct`, Panels 2B and 2C carry `primary_ci_pp` /
  `sensitivity_ci_pp`, Panel 1B carries whiskers. If a number appears alone, it is
  a defect.
- **No editable "peek" control** on Panel 3D. It is a static picture.
- **Do not drop the NON-RANDOMISED / ILLUSTRATION / POST-HOC labels** from
  Panels 2A, 3B, 3C and Panel 3D to make the page tidier. The repetition is
  the mitigation for R7 and the pre-registration discipline.

### The prohibition pass — run this before exporting

Walk the list above with the built page in front of you, one visual at a time.
This is a gate, not a glance.

- [ ] Exactly one slicer, on `hypothesis`, single-select. No arm, mode,
      agreement, demographic, stratum or item-level cut anywhere — including in
      the Filters pane and any drill-through.
- [ ] No visual recomputes a rate, SE, p-value or MDE. Every number traces to
      one cell in `outputs/tables/`.
- [ ] No "significant" flag, no up/down arrow on the effect, no traffic light
      reading 0.063 as a near miss.
- [ ] Every effect on the page carries its interval. Panel 1A's rates show
      `ci_treatment_pct` / `ci_control_pct`; Panels 2B and 2C show `primary_ci_pp`
      and `sensitivity_ci_pp`; Panel 1B shows whiskers. A number standing alone
      is a defect.
- [ ] **No conditional format anywhere on the page is keyed on a p-value.**
      Check Panels 3A, 2A and 3B individually. Formatting on `p_value` would light
      up `mode_subgroup`'s paper row (p = 0.0289) and nothing else.
- [ ] `NON-RANDOMISED` on Panel 3C, `POST-HOC — NOT PRE-REGISTERED` on Panel 3B,
      `ILLUSTRATION` on Panel 3D if built, the Panel 2A collider caveat and the
      Panel 3B conditional-on-response caveat all present. The repetition is the
      mitigation — do not tidy it away.
- [ ] Panel 1B's x-axis untouched at ±5.5 pp; Panel 3D's y-axis fixed at
      0 to 1. Nothing on the page auto-scales.
- [ ] The left-rail provenance legend is present and its three tiers match the
      panels they claim.
- [ ] Totals off on every table visual, confirmed one visual at a time.
- [ ] The callout card binds to `primary_itt[verdict_vis]` (the column), not
      `[Verdict]`.

Then **test every measure with the slicer moved**, not just at rest: select H1,
H2 and H3 in turn and confirm Panel 1A's five values change together and none
goes blank. DATA-01 shipped two `ALL()` scoping bugs and an
`ALLSELECTED`-vs-visual-filter bug that only appeared under slicer interaction.

Finally, cross-check the numbers you see against
`outputs/phase6_validation_reference.md`. Every value on the page should appear
there in exactly that rounded form.

**This pass closes R19** (`docs/risks-and-pitfalls.md`), which is MITIGATED in
spec but not CLOSED until it has been run against a real page.

---

## 8. Build order

Panel 1B first. It is the anchor and the only panel with a tooling dependency, so
confirm it renders before investing in the rest.

1. Power Query: load all 11 CSVs, set types with the §1 two-step cast for
   `mode_subgroup`, merge `mde` into `primary_itt` on `hypothesis_id` (§2),
   autodetect relationships off.
2. `_Measures` table and all §4 DAX.
3. Page shell: canvas 1600 x 1000, title, sub-title, slicer, provenance legend.
4. **Panel 1B** in Deneb. Confirm against `outputs/figures/panelB_preview.png`.
5. Panel 1A headline, now that the measures are final.
6. Page 2: Panel 2A, then Panels 2B and 2C.
7. Page 3: Panels 3A, 3B, 3C; the page-3 footer footnote; then Panel 3D
   (optional) last.
8. Totals off everywhere, then the §7 prohibition pass and the slicer-move test.

---

## 9. Export

- **File > Export > Export to PDF** → `powerbi/HINTS7-Commitment-Scorecard.pdf`
- PNG screenshots → `outputs/figures/` — at minimum each of the three pages,
  and Panel 1B on its own for the portfolio card.

Do not export before the §7 prohibition pass. The exports are what reach the
case study, and a defect in an exported PNG outlives the file it came from.

Completing this section is the Phase 6 hard stop.
