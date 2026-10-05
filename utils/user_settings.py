"""Per-user UI settings, protected with Windows DPAPI (including API keys)."""

import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import tempfile


def settings_path():
    return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local")) / "SeoWeb" / "settings.dat"


class _Blob(ctypes.Structure):
    _fields_ = [("size", wintypes.DWORD), ("data", ctypes.POINTER(ctypes.c_ubyte))]


def _protect(data, decrypt=False):
    if os.name != "nt":
        raise OSError("Saving protected settings requires Windows")
    crypt = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    buffer = ctypes.create_string_buffer(data)
    source = _Blob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)))
    output = _Blob()
    function = crypt.CryptUnprotectData if decrypt else crypt.CryptProtectData
    function.argtypes = [ctypes.POINTER(_Blob), ctypes.c_void_p, ctypes.c_void_p,
                         ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(_Blob)]
    function.restype = wintypes.BOOL
    if not function(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(output)):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return ctypes.string_at(output.data, output.size)
    finally:
        kernel.LocalFree(output.data)


def load_settings(path=None):
    path = Path(path) if path is not None else settings_path()
    if not path.exists():
        return {}
    payload = json.loads(_protect(path.read_bytes(), decrypt=True).decode("utf-8"))
    if not isinstance(payload, dict) or payload.get("version") != 1 or not isinstance(payload.get("values"), dict):
        raise ValueError("Invalid saved settings format")
    return payload["values"]


def save_settings(values, path=None):
    path = Path(path) if path is not None else settings_path()
    data = _protect(json.dumps({"version": 1, "values": values}, ensure_ascii=False).encode("utf-8"))
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix="settings-", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
