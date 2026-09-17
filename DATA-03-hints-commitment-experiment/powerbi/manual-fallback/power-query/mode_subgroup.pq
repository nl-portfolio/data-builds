let
    Source = Csv.Document(File.Contents(TablesFolder & "mode_subgroup.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Promoted, {{"hypothesis_id", type text}, {"family", type text}, {"mode", type text}, {"n_tx", type number}, {"n_ctl", type number}, {"rate_tx_pct", type number}, {"rate_ctl_pct", type number}, {"diff_pp", type number}, {"ci_lo_pp", type number}, {"ci_hi_pp", type number}, {"z", type number}, {"p_value", type number}}),
    // These arrive as "1061.0" and are blank on the interaction rows.
    // Text -> Int64 direct would error; go via number, keep nulls null.
    WholeNumbers = Table.TransformColumnTypes(Typed, {{"n_tx", Int64.Type}, {"n_ctl", Int64.Type}})
in
    WholeNumbers
