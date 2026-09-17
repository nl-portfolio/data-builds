let
    Source = Csv.Document(File.Contents(TablesFolder & "multiplicity_holm_m3.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Promoted, {{"hypothesis", type text}, {"hypothesis_id", type text}, {"p_uncorrected", type number}, {"holm_threshold", type number}, {"p_holm", type number}, {"reject_at_familywise_0.05", type logical}})
in
    Typed
