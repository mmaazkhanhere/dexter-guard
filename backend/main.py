"""Vercel Services entrypoint for the composed FastAPI application."""

from pathlib import Path
import sys

backend_root = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_root / "src"))

from app.main import app  # noqa: E402

__all__ = ["app"]
