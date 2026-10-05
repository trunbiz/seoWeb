"""Find the base interpreter's Tcl/Tk and fail before creating an unusable EXE."""
import json
import os
from pathlib import Path
import sys

try:
    import tkinter
    import _tkinter
    root = Path(sys.base_prefix) / "tcl"
    tcl = root / f"tcl{_tkinter.TCL_VERSION}"
    tk = root / f"tk{_tkinter.TK_VERSION}"
    if (tcl / "init.tcl").is_file():
        os.environ["TCL_LIBRARY"] = str(tcl)
    if (tk / "tk.tcl").is_file():
        os.environ["TK_LIBRARY"] = str(tk)
    window = tkinter.Tk()
    window.withdraw()
    paths = {
        "TCL_LIBRARY": window.tk.eval("info library"),
        "TK_LIBRARY": window.tk.eval("set tk_library"),
    }
    window.destroy()
    # PyInstaller may otherwise silently exclude tkinter via its pre-find hook.
    from PyInstaller.utils.hooks.tcl_tk import tcltk_info
    if not tcltk_info.available:
        raise RuntimeError("PyInstaller cannot detect Tcl/Tk")
    print(json.dumps(paths))
except Exception as exc:
    print(f"Tkinter/Tcl/Tk preflight failed: {exc}\n"
          "Repair the base Python installation with 'tcl/tk and IDLE' enabled, then rebuild.", file=sys.stderr)
    sys.exit(1)
