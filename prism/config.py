"""Environment configuration; no external services required for the demo."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("PRISM_DATA_DIR", str(ROOT / "data")))
