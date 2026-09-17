let
    Source = Csv.Document(File.Contents(TablesFolder & "per_protocol.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Promoted, {{"hypothesis_id", type text}, {"group", type text}, {"n", Int64.Type}, {"rate_pct", type number}, {"ci_lo_pct", type number}, {"ci_hi_pct", type number}})
in
    Typed
