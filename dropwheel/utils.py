"""Small helpers with no GUI dependencies (easy to unit test)."""
from __future__ import annotations

import ctypes
import sys
from pathlib import Path

VK_LBUTTON = 0x01
VK_SHIFT = 0x10


def unique_path(path: Path) -> Path:
    """Return `path`, or `name (1).ext`, `name (2).ext`... if it already exists."""
    if not path.exists():
        return path
    n = 1
    while True:
        candidate = path.with_name(f"{path.stem} ({n}){path.suffix}")
        if not candidate.exists():
            return candidate
        n += 1


def _is_down(vk: int) -> bool:
    """True while a key / mouse button is physically held (Win32 GetAsyncKeyState)."""
    if sys.platform != "win32":
        return False
    return bool(ctypes.windll.user32.GetAsyncKeyState(vk) & 0x8000)


def is_left_mouse_down() -> bool:
    return _is_down(VK_LBUTTON)


def is_shift_down() -> bool:
    return _is_down(VK_SHIFT)