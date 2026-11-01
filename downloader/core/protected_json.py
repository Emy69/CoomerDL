"""JSON files encrypted for the current Windows user.

Cookies are as good as a password, so they are stored with DPAPI: only the
same Windows account on the same machine can read them back. Files written
before this existed are plain JSON and are still read; they get encrypted the
next time they are saved. On other platforms the file stays plain JSON.
"""

import base64
import ctypes
import json
import os

_MARKER = "dpapi"
_DESCRIPTION = "CoomerDL cookies"


class _DataBlob(ctypes.Structure):
    _fields_ = [
        ("cbData", ctypes.c_ulong),
        ("pbData", ctypes.POINTER(ctypes.c_char)),
    ]


def _call_dpapi(func, data: bytes, *args) -> bytes:
    buf = ctypes.create_string_buffer(data, len(data))
    blob_in = _DataBlob(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))
    blob_out = _DataBlob()
    if not func(ctypes.byref(blob_in), *args, None, None, None, 0, ctypes.byref(blob_out)):
        raise ctypes.WinError()
    try:
        return ctypes.string_at(blob_out.pbData, blob_out.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(blob_out.pbData)


def _protect(data: bytes) -> bytes:
    return _call_dpapi(ctypes.windll.crypt32.CryptProtectData, data, _DESCRIPTION)


def _unprotect(data: bytes) -> bytes:
    return _call_dpapi(ctypes.windll.crypt32.CryptUnprotectData, data, None)


def available() -> bool:
    return os.name == "nt"


def is_protected(doc) -> bool:
    return isinstance(doc, dict) and doc.get(_MARKER) is True and "data" in doc


def load(path):
    """The stored value, or None when the file does not exist.

    Raises ValueError when the file cannot be decoded, for example when it
    was encrypted by another Windows account.
    """
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        doc = json.load(f)
    if not is_protected(doc):
        return doc
    if not available():
        raise ValueError("This file was encrypted on Windows and can't be read here.")
    try:
        raw = _unprotect(base64.b64decode(doc["data"]))
    except OSError as e:
        raise ValueError(f"Can't decrypt {os.path.basename(path)}: {e}") from e
    return json.loads(raw.decode("utf-8"))


def save(path, value):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    if available():
        raw = json.dumps(value, ensure_ascii=False).encode("utf-8")
        doc = {_MARKER: True, "data": base64.b64encode(_protect(raw)).decode("ascii")}
    else:
        doc = value
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=4, ensure_ascii=False)
    os.replace(tmp, path)
