import sys
from pathlib import Path


# Ensure the api app package is importable as `app`
APP_DIR = Path(__file__).resolve().parents[1] / "app"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

