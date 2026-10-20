"""Small helpers with no GUI dependencies (easy to unit test)."""
from __future__ import annotations

import ctypes
import subprocess
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


def clamp_to_screen(
    x: int, y: int, width: int, height: int, screen_rect: tuple[int, int, int, int]
) -> tuple[int, int]:
    """Clamp (x, y) so a bounding box of (width, height) stays entirely within screen_rect (left, top, w, h)."""
    left, top, sw, sh = screen_rect
    max_x = left + max(0, sw - width)
    max_y = top + max(0, sh - height)
    clamped_x = max(left, min(x, max_x))
    clamped_y = max(top, min(y, max_y))
    return clamped_x, clamped_y


def _is_down(vk: int) -> bool:
    """True while a key / mouse button is physically held (Win32 GetAsyncKeyState)."""
    if sys.platform != "win32":
        return False
    return bool(ctypes.windll.user32.GetAsyncKeyState(vk) & 0x8000)


def is_left_mouse_down() -> bool:
    return _is_down(VK_LBUTTON)


def is_shift_down() -> bool:
    return _is_down(VK_SHIFT)


def reveal_in_explorer(path: Path | str) -> None:
    """Open Windows Explorer with `path` selected (or parent directory if path is not found)."""
    p = Path(path).resolve()
    if sys.platform != "win32":
        return
    if p.exists():
        subprocess.Popen(["explorer", f"/select,{p}"])
    elif p.parent.exists():
        subprocess.Popen(["explorer", str(p.parent)])