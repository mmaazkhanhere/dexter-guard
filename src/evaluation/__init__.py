"""Synthetic-only, headless evaluation and observability boundary for Spec 008."""

from .benchmark import default_dataset
from .dataset import DatasetValidationError, validate_dataset
from .metrics import calculate_metrics

__all__ = ["DatasetValidationError", "calculate_metrics", "default_dataset", "validate_dataset"]

