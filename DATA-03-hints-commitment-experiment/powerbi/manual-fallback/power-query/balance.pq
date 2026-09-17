let
    Source = Csv.Document(File.Contents(TablesFolder & "balance.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Promoted, {{"covariate", type text}, {"levels", Int64.Type}, {"chi2", type number}, {"dof", Int64.Type}, {"p_value", type number}, {"max_arm_share_gap_pp", type number}, {"overrepresented_level", type text}, {"treatment_share_pct", type number}, {"control_share_pct", type number}, {"flag", type text}})
in
    Typed
