# Synthetic German evaluation benchmark 008-v1

This directory identifies the versioned benchmark used by Spec 008. The executable fixture is generated deterministically by `evaluation.benchmark.default_dataset()` so the checked-in source remains small and reviewable. It contains 100 synthetic German scenarios divided into 60 development, 20 validation, and 20 held-out cases, with unique families and fixed candidate hashes.

The fixture is synthetic-only, uses no external patient data, and is not clinical safety validation. Held-out cases are selected by family and are not available to tuning or model-selection code.

