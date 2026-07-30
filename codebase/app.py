"""Compatibility launcher. Backend/frontend are split into codebase/backend and codebase/frontend."""
from pathlib import Path
import sys

BACKEND_DIR = Path(__file__).resolve().parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from server import main  # noqa: E402

if __name__ == "__main__":
    main()
