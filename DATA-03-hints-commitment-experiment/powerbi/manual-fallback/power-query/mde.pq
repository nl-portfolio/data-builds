let
    Source = Csv.Document(File.Contents(TablesFolder & "mde.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Promoted, {{"hypothesis_id", type text}, {"hypothesis", type text}, {"observed_baseline_rate_pct", type number}, {"n_treatment", Int64.Type}, {"n_control", Int64.Type}, {"measured_rate_deff", type number}, {"mde_grid_formula_pp", type number}, {"mde_empirical_pp", type number}, {"observed_effect_pp", type number}, {"observed_effect_below_empirical_mde", type logical}})
in
    Typed
