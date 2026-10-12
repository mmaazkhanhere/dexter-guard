# Evidence verification prompt v1

Compare each immutable atomic claim with only the supplied immutable German
transcript. Return one structured finding per claim using the `EvidenceStatus`
enum and `EVIDENCE_ANNOTATION-v1`. Cite source character spans using zero-based,
end-exclusive Unicode code-point offsets. Never infer a resident, diagnosis,
certainty, attribution, or negation that is not established by the transcript.

