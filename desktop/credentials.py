"""Keep the desktop API key encrypted for the current Windows user with DPAPI."""

import ctypes
from ctypes import wintypes
import os
from pathlib import Path


class _Blob(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_ubyte))]


def _crypt(data: bytes, decrypt=False) -> bytes:
    if os.name != "nt":
        raise OSError("Защищённое хранение ключа доступно только в Windows")
    buffer = ctypes.create_string_buffer(data)
    source = _Blob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)))
    result = _Blob()
    crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    kernel32.LocalFree.restype = ctypes.c_void_p
    if decrypt:
        function = crypt32.CryptUnprotectData
        function.argtypes = [
            ctypes.POINTER(_Blob),
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_void_p,
            wintypes.DWORD,
            ctypes.POINTER(_Blob),
        ]
        ok = function(
            ctypes.byref(source), None, None, None, None, 1, ctypes.byref(result)
        )
    else:
        function = crypt32.CryptProtectData
        function.argtypes = [
            ctypes.POINTER(_Blob),
            wintypes.LPCWSTR,
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_void_p,
            wintypes.DWORD,
            ctypes.POINTER(_Blob),
        ]
        ok = function(
            ctypes.byref(source),
            "2GIS Business Parser",
            None,
            None,
            None,
            1,
            ctypes.byref(result),
        )
    if not ok:
        raise OSError("Windows не удалось обработать защищённый API-ключ")
    try:
        return ctypes.string_at(result.pbData, result.cbData)
    finally:
        kernel32.LocalFree(ctypes.cast(result.pbData, ctypes.c_void_p))


def save_api_key(key: str, directory: Path):
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "api-key.dpapi"
    if not key:
        path.unlink(missing_ok=True)
        return
    protected = _crypt(key.encode("utf-8"))
    temporary = path.with_suffix(".tmp")
    temporary.write_bytes(protected)
    temporary.replace(path)


def load_api_key(directory: Path) -> str:
    path = directory / "api-key.dpapi"
    if not path.exists():
        return ""
    return _crypt(path.read_bytes(), decrypt=True).decode("utf-8")
