"""Native Windows notification icon, without another GUI toolkit or browser bundle."""

from __future__ import annotations
import ctypes
from ctypes import wintypes
import os
import threading
from typing import Callable

MENU = [
    (101, "open", "Открыть приложение"),
    (102, "2gis", "Открыть 2ГИС"),
    (103, "pause", "Приостановить поиск"),
    (104, "resume", "Продолжить последний поиск"),
    (105, "window", "Показать окно управления"),
    (106, "exit", "Завершить работу"),
]


def icon_pixels(size=32):
    """White square and black outline layers, BGRA plus a transparency mask."""
    pixels = bytearray(size * size * 4)
    for y in range(3, size - 3):
        for x in range(3, size - 3):
            if (x < 6 or x >= size - 6) and (y < 6 or y >= size - 6):
                continue
            i = (y * size + x) * 4
            pixels[i : i + 4] = bytes([255, 255, 255, 255])

    def line(a, b):
        x0, y0 = a
        x1, y1 = b
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            if 0 <= x0 < size and 0 <= y0 < size:
                i = (y0 * size + x0) * 4
                pixels[i : i + 4] = bytes([0, 0, 0, 255])
            if x0 == x1 and y0 == y1:
                break
            e = 2 * err
            if e >= dy:
                err += dy
                x0 += sx
            if e <= dx:
                err += dx
                y0 += sy

    for points in [
        [(8, 12), (16, 8), (24, 12), (16, 16), (8, 12)],
        [(8, 17), (16, 21), (24, 17)],
        [(8, 22), (16, 26), (24, 22)],
    ]:
        for a, b in zip(points, points[1:]):
            line(a, b)
    rowbytes = ((size + 31) // 32) * 4
    mask = bytearray(rowbytes * size)
    # CreateIcon expects bottom-up scan lines for the XOR/color bitmap.
    bottom_up = bytearray()
    for y in range(size - 1, -1, -1):
        bottom_up.extend(pixels[y * size * 4 : (y + 1) * size * 4])
        for x in range(size):
            if not pixels[(y * size + x) * 4 + 3]:
                mask[(size - 1 - y) * rowbytes + x // 8] |= 1 << (7 - x % 8)
    return bytes(bottom_up), bytes(mask)


class TrayIcon:
    def __init__(self, dispatch: Callable[[str], None]):
        self.dispatch = dispatch
        self.available = False
        self.window_created = False
        self.hwnd = None
        self.thread = None
        self._ready = threading.Event()

    def start(self):
        if os.name != "nt":
            return False
        self.thread = threading.Thread(
            target=self._run, name="parser-tray", daemon=True
        )
        self.thread.start()
        self._ready.wait(4)
        return self.available

    def stop(self):
        if self.hwnd and os.name == "nt":
            user = ctypes.WinDLL("user32", use_last_error=True)
            user.PostMessageW.argtypes = [
                wintypes.HWND,
                wintypes.UINT,
                wintypes.WPARAM,
                wintypes.LPARAM,
            ]
            user.PostMessageW(self.hwnd, 0x0010, 0, 0)
        if self.thread and self.thread.is_alive():
            self.thread.join(3)

    def _run(self):
        user = ctypes.WinDLL("user32", use_last_error=True)
        shell = ctypes.WinDLL("shell32", use_last_error=True)
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        LRESULT = ctypes.c_ssize_t
        WNDPROC = ctypes.WINFUNCTYPE(
            LRESULT, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM
        )

        class WNDCLASS(ctypes.Structure):
            _fields_ = [
                ("style", wintypes.UINT),
                ("lpfnWndProc", WNDPROC),
                ("cbClsExtra", ctypes.c_int),
                ("cbWndExtra", ctypes.c_int),
                ("hInstance", wintypes.HINSTANCE),
                ("hIcon", wintypes.HICON),
                ("hCursor", wintypes.HANDLE),
                ("hbrBackground", wintypes.HANDLE),
                ("lpszMenuName", wintypes.LPCWSTR),
                ("lpszClassName", wintypes.LPCWSTR),
            ]

        class GUID(ctypes.Structure):
            _fields_ = [
                ("Data1", wintypes.DWORD),
                ("Data2", wintypes.WORD),
                ("Data3", wintypes.WORD),
                ("Data4", ctypes.c_ubyte * 8),
            ]

        class NOTIFYICONDATA(ctypes.Structure):
            _fields_ = [
                ("cbSize", wintypes.DWORD),
                ("hWnd", wintypes.HWND),
                ("uID", wintypes.UINT),
                ("uFlags", wintypes.UINT),
                ("uCallbackMessage", wintypes.UINT),
                ("hIcon", wintypes.HICON),
                ("szTip", wintypes.WCHAR * 128),
                ("dwState", wintypes.DWORD),
                ("dwStateMask", wintypes.DWORD),
                ("szInfo", wintypes.WCHAR * 256),
                ("uVersion", wintypes.UINT),
                ("szInfoTitle", wintypes.WCHAR * 64),
                ("dwInfoFlags", wintypes.DWORD),
                ("guidItem", GUID),
                ("hBalloonIcon", wintypes.HICON),
            ]

        kernel.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
        kernel.GetModuleHandleW.restype = wintypes.HMODULE
        user.DefWindowProcW.argtypes = [
            wintypes.HWND,
            wintypes.UINT,
            wintypes.WPARAM,
            wintypes.LPARAM,
        ]
        user.DefWindowProcW.restype = LRESULT
        user.CreateWindowExW.argtypes = [
            wintypes.DWORD,
            wintypes.LPCWSTR,
            wintypes.LPCWSTR,
            wintypes.DWORD,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            wintypes.HWND,
            wintypes.HMENU,
            wintypes.HINSTANCE,
            ctypes.c_void_p,
        ]
        user.CreateWindowExW.restype = wintypes.HWND
        user.RegisterClassW.argtypes = [ctypes.POINTER(WNDCLASS)]
        user.RegisterClassW.restype = wintypes.WORD
        user.UnregisterClassW.argtypes = [wintypes.LPCWSTR, wintypes.HINSTANCE]
        user.DestroyWindow.argtypes = [wintypes.HWND]
        user.RegisterWindowMessageW.argtypes = [wintypes.LPCWSTR]
        user.RegisterWindowMessageW.restype = wintypes.UINT
        user.CreateIcon.argtypes = [
            wintypes.HINSTANCE,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_ubyte,
            ctypes.c_ubyte,
            ctypes.c_void_p,
            ctypes.c_void_p,
        ]
        user.CreateIcon.restype = wintypes.HICON
        user.DestroyIcon.argtypes = [wintypes.HICON]
        user.CreatePopupMenu.restype = wintypes.HMENU
        user.AppendMenuW.argtypes = [
            wintypes.HMENU,
            wintypes.UINT,
            ctypes.c_size_t,
            wintypes.LPCWSTR,
        ]
        user.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
        user.SetForegroundWindow.argtypes = [wintypes.HWND]
        user.TrackPopupMenu.argtypes = [
            wintypes.HMENU,
            wintypes.UINT,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            wintypes.HWND,
            ctypes.c_void_p,
        ]
        user.TrackPopupMenu.restype = wintypes.UINT
        user.DestroyMenu.argtypes = [wintypes.HMENU]
        user.PostMessageW.argtypes = [
            wintypes.HWND,
            wintypes.UINT,
            wintypes.WPARAM,
            wintypes.LPARAM,
        ]
        user.GetMessageW.argtypes = [
            ctypes.POINTER(wintypes.MSG),
            wintypes.HWND,
            wintypes.UINT,
            wintypes.UINT,
        ]
        user.GetMessageW.restype = ctypes.c_int
        user.TranslateMessage.argtypes = [ctypes.POINTER(wintypes.MSG)]
        user.DispatchMessageW.argtypes = [ctypes.POINTER(wintypes.MSG)]
        user.DispatchMessageW.restype = LRESULT
        shell.Shell_NotifyIconW.argtypes = [
            wintypes.DWORD,
            ctypes.POINTER(NOTIFYICONDATA),
        ]
        shell.Shell_NotifyIconW.restype = wintypes.BOOL
        instance = kernel.GetModuleHandleW(None)
        classname = "2GISBusinessParserTray" + str(id(self))
        data = None
        icon = None
        callback_message = 0x8001
        taskbar_created = user.RegisterWindowMessageW("TaskbarCreated")

        @WNDPROC
        def procedure(hwnd, message, wparam, lparam):
            if message == callback_message:
                if lparam == 0x0203:
                    self.dispatch("open")
                elif lparam in (0x0205, 0x007B):
                    menu = user.CreatePopupMenu()
                    try:
                        for identifier, action, title in MENU:
                            user.AppendMenuW(menu, 0, identifier, title)
                        point = wintypes.POINT()
                        user.GetCursorPos(ctypes.byref(point))
                        user.SetForegroundWindow(hwnd)
                        selected = user.TrackPopupMenu(
                            menu, 0x0100 | 0x0002, point.x, point.y, 0, hwnd, None
                        )
                        user.PostMessageW(hwnd, 0, 0, 0)
                        for identifier, action, title in MENU:
                            if selected == identifier:
                                self.dispatch(action)
                    finally:
                        user.DestroyMenu(menu)
                return 0
            if message == taskbar_created and data is not None:
                self.available = bool(shell.Shell_NotifyIconW(0, ctypes.byref(data)))
                return 0
            if message == 0x0010:
                user.DestroyWindow(hwnd)
                return 0
            if message == 0x0002:
                self.hwnd = None
                if data is not None:
                    shell.Shell_NotifyIconW(2, ctypes.byref(data))
                user.PostQuitMessage(0)
                return 0
            return user.DefWindowProcW(hwnd, message, wparam, lparam)

        try:
            wc = WNDCLASS()
            wc.lpfnWndProc = procedure
            wc.hInstance = instance
            wc.lpszClassName = classname
            if not user.RegisterClassW(ctypes.byref(wc)):
                return
            self.hwnd = user.CreateWindowExW(
                0,
                classname,
                "2GIS Business Parser tray",
                0,
                0,
                0,
                0,
                0,
                None,
                None,
                instance,
                None,
            )
            if not self.hwnd:
                return
            self.window_created = True
            pixels, mask = icon_pixels()
            pixel_buffer = ctypes.create_string_buffer(pixels)
            mask_buffer = ctypes.create_string_buffer(mask)
            icon = user.CreateIcon(instance, 32, 32, 1, 32, mask_buffer, pixel_buffer)
            if not icon:
                return
            data = NOTIFYICONDATA()
            data.cbSize = ctypes.sizeof(data)
            data.hWnd = self.hwnd
            data.uID = 1
            data.uFlags = 1 | 2 | 4
            data.uCallbackMessage = callback_message
            data.hIcon = icon
            data.szTip = "2GIS Business Parser — двойной щелчок: открыть"
            self.available = bool(shell.Shell_NotifyIconW(0, ctypes.byref(data)))
            self._ready.set()
            message = wintypes.MSG()
            while user.GetMessageW(ctypes.byref(message), None, 0, 0) > 0:
                user.TranslateMessage(ctypes.byref(message))
                user.DispatchMessageW(ctypes.byref(message))
        finally:
            self._ready.set()
            if data is not None:
                shell.Shell_NotifyIconW(2, ctypes.byref(data))
            if icon:
                user.DestroyIcon(icon)
            if self.hwnd:
                user.DestroyWindow(self.hwnd)
            self.hwnd = None
            self.available = False
            user.UnregisterClassW(classname, instance)
