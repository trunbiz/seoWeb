"""Initialize writable storage and bundled Chromium before application imports."""
import os
from pathlib import Path
import sys

os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "0"
data_dir = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local")) / "SeoWeb"
data_dir.mkdir(parents=True, exist_ok=True)
os.chdir(data_dir)
# --windowed has no console; startup error handling still needs valid streams.
if sys.stdout is None:
    sys.stdout = open(data_dir / "startup.log", "a", encoding="utf-8", buffering=1)
if sys.stderr is None:
    sys.stderr = sys.stdout

