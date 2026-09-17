let
    Source = Csv.Document(File.Contents(TablesFolder & "assertion_history.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Promoted, {{"estimate", type text}, {"n_respondents", Int64.Type}, {"point_pct", type number}, {"se_pp", type number}, {"implied_n", type number}, {"implied_n_over_n", type number}, {"design_effect_rate", type number}, {"guard", type text}})
in
    Typed
