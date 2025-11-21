"""WSGI entry point for production deployments (e.g. Render)."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api import app  # noqa: E402

__all__ = ("app",)
