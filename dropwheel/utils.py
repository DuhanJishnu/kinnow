"""Small helpers with no GUI dependencies (easy to unit test)."""
from __future__ import annotations

import ctypes
import os
import re
import subprocess
import sys
from pathlib import Path

VK_LBUTTON = 0x01
VK_TAB = 0x09
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


def is_tab_down() -> bool:
    return _is_down(VK_TAB)


def natural_sort_key(path: Path | str) -> list[int | str]:
    """Sort key for human natural alphanumeric ordering (e.g. 1, 2, 10 instead of 1, 10, 2)."""
    name = Path(path).name
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r"(\d+)", name)]


def reveal_in_explorer(path: Path | str) -> None:
    """Open Windows Explorer with `path` selected (or parent directory if path is not found)."""
    p = Path(path).resolve()
    if sys.platform != "win32":
        return

    # Windows Explorer expects `/select,"<path>"` where only the path is quoted.
    # Wrapping `/select,` inside quotes (which Python list2cmdline does if the path contains spaces)
    # causes Explorer to fail switch parsing and default to opening the Documents folder.
    target_str = str(p)
    if p.exists():
        param = f'/select,"{target_str}"'
    elif p.parent.exists():
        param = f'"{p.parent}"'
    else:
        return

    try:
        ret = ctypes.windll.shell32.ShellExecuteW(None, "open", "explorer.exe", param, None, 1)
        if ret <= 32:  # ShellExecute error threshold
            subprocess.Popen(f"explorer.exe {param}")
    except Exception:
        subprocess.Popen(f"explorer.exe {param}")


def get_app_executable() -> Path:
    """Return the executable path for Kinnow."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve()
    return (Path(__file__).resolve().parents[1] / "run.py").resolve()


def get_desktop_shortcut_path() -> Path:
    desktop = Path(os.environ.get("USERPROFILE", Path.home())) / "Desktop"
    return desktop / "Kinnow.lnk"


def get_start_menu_shortcut_path() -> Path:
    appdata = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    return appdata / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Kinnow.lnk"


def get_startup_shortcut_path() -> Path:
    appdata = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    return appdata / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup" / "Kinnow.lnk"


def create_shortcut(target: Path, lnk_path: Path, description: str = "Kinnow") -> bool:
    """Create a Windows .lnk shortcut pointing to target."""
    if sys.platform != "win32":
        return False
    try:
        lnk_path = lnk_path.resolve()
        lnk_path.parent.mkdir(parents=True, exist_ok=True)
        target = target.resolve()
        ps_cmd = (
            f"$w = New-Object -ComObject WScript.Shell; "
            f"$s = $w.CreateShortcut('{lnk_path}'); "
            f"$s.TargetPath = '{target}'; "
            f"$s.WorkingDirectory = '{target.parent}'; "
            f"$s.IconLocation = '{target},0'; "
            f"$s.Description = '{description}'; "
            f"$s.Save()"
        )
        flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        subprocess.run(
            ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps_cmd],
            check=True,
            creationflags=flags,
            capture_output=True,
        )
        return lnk_path.exists()
    except Exception:
        return False


def is_startup_enabled() -> bool:
    return get_startup_shortcut_path().exists()


def toggle_startup(enable: bool) -> bool:
    lnk = get_startup_shortcut_path()
    if enable:
        return create_shortcut(get_app_executable(), lnk)
    else:
        if lnk.exists():
            lnk.unlink(missing_ok=True)
        return True