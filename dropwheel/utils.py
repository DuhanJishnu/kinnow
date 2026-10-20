"""Small helpers with no GUI dependencies (easy to unit test)."""
from __future__ import annotations

import ctypes
import io
import math
import os
from pathlib import Path
import re
import struct
import subprocess
import sys
import wave

_TICK_WAV_CACHE: bytes | None = None


def _get_tick_wav() -> bytes:
    global _TICK_WAV_CACHE
    if _TICK_WAV_CACHE is not None:
        return _TICK_WAV_CACHE

    buf = io.BytesIO()
    # 44.1 kHz, 16-bit mono, 7ms subtle mechanical tick
    num_samples = int(44100 * 0.007)
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(44100)
        data = bytearray()
        for i in range(num_samples):
            envelope = math.exp(-i / (num_samples * 0.18))
            sample = int(12000 * envelope * math.sin(2 * math.pi * 2400 * i / 44100))
            data.extend(struct.pack("<h", sample))
        w.writeframes(data)

    _TICK_WAV_CACHE = buf.getvalue()
    return _TICK_WAV_CACHE


def play_tick_sound() -> None:
    """Play a subtle mechanical tick sound asynchronously (0ms latency, non-blocking)."""
    if sys.platform != "win32":
        return
    try:
        wav_bytes = _get_tick_wav()
        SND_ASYNC = 0x0001
        SND_NODEFAULT = 0x0002
        SND_MEMORY = 0x0004
        ctypes.windll.winmm.PlaySoundW(wav_bytes, None, SND_MEMORY | SND_ASYNC | SND_NODEFAULT)
    except Exception:
        pass


def acquire_single_instance_mutex(
    mutex_name: str = "KinnowSingleInstanceMutex_5E28B146",
) -> tuple[int | None, bool]:
    """Try to acquire a named Windows Mutex. Returns (handle, is_already_running)."""
    if sys.platform != "win32":
        return None, False

    ERROR_ALREADY_EXISTS = 183
    handle = ctypes.windll.kernel32.CreateMutexW(None, True, mutex_name)
    last_error = ctypes.windll.kernel32.GetLastError()
    if last_error == ERROR_ALREADY_EXISTS:
        return handle, True
    return handle, False


def release_single_instance_mutex(handle: int | None) -> None:
    """Release and close the named mutex handle on exit."""
    if sys.platform != "win32" or not handle:
        return
    try:
        ctypes.windll.kernel32.ReleaseMutex(handle)
        ctypes.windll.kernel32.CloseHandle(handle)
    except Exception:
        pass

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


def open_file_properties(path: Path | str) -> bool:
    """Open the native Windows Explorer File Properties dialog for `path`."""
    p = Path(path).resolve()
    if not p.exists() or sys.platform != "win32":
        return False

    from ctypes import wintypes

    class SHELLEXECUTEINFOW(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.DWORD),
            ("fMask", wintypes.ULONG),
            ("hwnd", wintypes.HWND),
            ("lpVerb", wintypes.LPCWSTR),
            ("lpFile", wintypes.LPCWSTR),
            ("lpParameters", wintypes.LPCWSTR),
            ("lpDirectory", wintypes.LPCWSTR),
            ("nShow", ctypes.c_int),
            ("hInstApp", wintypes.HINSTANCE),
            ("lpIDList", ctypes.c_void_p),
            ("lpClass", wintypes.LPCWSTR),
            ("hkeyClass", wintypes.HKEY),
            ("dwHotKey", wintypes.DWORD),
            ("hIconOrMonitor", wintypes.HANDLE),
            ("hProcess", wintypes.HANDLE),
        ]

    SEE_MASK_INVOKEIDLIST = 0x0000000C
    SW_SHOW = 5

    sei = SHELLEXECUTEINFOW()
    sei.cbSize = ctypes.sizeof(SHELLEXECUTEINFOW)
    sei.fMask = SEE_MASK_INVOKEIDLIST
    sei.hwnd = None
    sei.lpVerb = "properties"
    sei.lpFile = str(p)
    sei.lpParameters = None
    sei.lpDirectory = None
    sei.nShow = SW_SHOW

    try:
        res = ctypes.windll.shell32.ShellExecuteExW(ctypes.byref(sei))
        return bool(res)
    except Exception:
        return False



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