"""Vercel Services entrypoint for the composed FastAPI application."""

from pathlib import Path
import sys

repository_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repository_root / "src"))

from app.main import app  # noqa: E402

__all__ = ["app"]
