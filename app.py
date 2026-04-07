import runpy
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = ROOT_DIR / "frontend"

for path in (str(FRONTEND_DIR), str(ROOT_DIR)):
    if path not in sys.path:
        sys.path.insert(0, path)


if __name__ == "__main__":
    runpy.run_module("frontend.app", run_name="__main__")
