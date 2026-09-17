let
    Source = Csv.Document(File.Contents(TablesFolder & "peeking_illustration.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Promoted, {{"hypothesis_id", type text}, {"fraction", type number}, {"n", Int64.Type}, {"diff_pp", type number}, {"z", type number}, {"p_value", type number}})
in
    Typed
