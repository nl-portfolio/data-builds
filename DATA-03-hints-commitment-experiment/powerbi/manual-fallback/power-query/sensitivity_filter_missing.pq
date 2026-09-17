let
    Source = Csv.Document(File.Contents(TablesFolder & "sensitivity_filter_missing.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Promoted, {{"hypothesis", type text}, {"hypothesis_id", type text}, {"spec", type text}, {"primary_diff_pp", type number}, {"primary_ci_pp", type text}, {"primary_p", type number}, {"sensitivity_diff_pp", type number}, {"sensitivity_ci_pp", type text}, {"sensitivity_p", type number}, {"sign_agrees", type logical}, {"both_null_at_0.05", type logical}})
in
    Typed
