let
    Source = Csv.Document(File.Contents(TablesFolder & "primary_itt.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Promoted, {{"hypothesis_id", type text}, {"hypothesis", type text}, {"n_treatment", Int64.Type}, {"n_control", Int64.Type}, {"rate_treatment_pct", type number}, {"ci_treatment_pct", type text}, {"rate_control_pct", type number}, {"ci_control_pct", type text}, {"difference_pp", type number}, {"ci_difference_pp", type text}, {"ci_low_pp", type number}, {"ci_high_pp", type number}, {"relative_difference_pct", type number}, {"z", type number}, {"p_uncorrected", type number}, {"mde_empirical_pp", type number}, {"mde_grid_formula_pp", type number}, {"measured_deff", type number}, {"verdict", type text}, {"verdict_class", type text}}),
    // Guide section 2: 1:1 merge to mde on hypothesis_id (never on a label).
    // Expand ONLY these two columns -- primary_itt already carries
    // mde_empirical_pp / mde_grid_formula_pp, and expanding the copies
    // would suffix them .1 and make every later reference ambiguous.
    Merged = Table.NestedJoin(Typed, {"hypothesis_id"}, mde, {"hypothesis_id"}, "mde", JoinKind.LeftOuter),
    Expanded = Table.ExpandTableColumn(Merged, "mde", {"observed_effect_pp", "observed_effect_below_empirical_mde"}, {"observed_effect_pp", "observed_effect_below_empirical_mde"})
in
    Expanded
