# Spec 006 Evaluation Handoff

The versioned development fixture and raw-count report are in
`specs/006-source-coverage/fixtures/cov-001-010-v1.json` and
`specs/006-source-coverage/evaluation/spec006-development-evaluation-v1.json`.

The held-out synthetic set has 10 cases, of which 9 contain applicable annotated
expected facts and 1 is an unresolved source item excluded from the benchmark
denominator. Results are:

| Metric | Numerator | Denominator | Result |
| --- | ---: | ---: | ---: |
| Benchmark completeness | 3 faithfully covered facts | 9 applicable facts | 0.3333 |
| Omission detection recall | 6 correctly flagged omissions | 6 annotated omissions | 1.0 |
| False omission warning rate | 0 false warnings | 3 reviewed non-omissions | 0.0 |

Runtime `runtimeCompleteness` remains an operational count over system-extracted
facts and must not be substituted for the manually annotated benchmark metric.
The absent Specs 007 and 008 mean final severity/approval mapping and release
threshold compatibility remain unresolved. This synthetic report is not clinical
safety validation.
