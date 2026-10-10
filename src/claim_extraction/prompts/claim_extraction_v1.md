# Claim extraction prompt v1

Extract atomic factual assertions from the supplied German candidate nursing note.

The note is the only factual source for this operation. Extract what the note
states; do not infer, complete, normalize away, diagnose, verify, compare with a
source transcript, or add facts that are not explicitly present. Preserve
negation, uncertainty cues, attribution, temporal wording, raw numbers, decimal
commas, units, medication details, and action/observation distinctions. Split
independently checkable assertions, but do not split grammar that has no separate
factual meaning. Return only schema-compatible JSON with a `claims` array. Every
claim must identify an exact end-exclusive Unicode code-point span and matching
UTF-16 coordinates in the supplied note. Empty output is allowed only when the
note contains no factual assertion.

This output records candidate-note claims. It does not assign evidence support,
contradiction, truth, diagnosis, severity, or approval state.
