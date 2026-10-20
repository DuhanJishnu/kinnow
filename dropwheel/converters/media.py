"""Audio/video conversions by calling the ffmpeg command-line tool."""
from __future__ import annotations

import shutil
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

from .registry import register

AUDIO = ["mp3", "wav", "ogg", "flac", "m4a"]
VIDEO = ["mp4", "mkv", "avi", "mov", "webm"]

# Extra ffmpeg flags per output format.
AUDIO_OUT = {
    "mp3": ["-vn", "-q:a", "2"],
    "wav": ["-vn"],
    "ogg": ["-vn"],
    "flac": ["-vn"],
}
VIDEO_OUT = {
    "mp4": [],
    "webm": [],
    "gif": ["-vf", "fps=12,scale=480:-1:flags=lanczos", "-an"],
}


class FFmpegNotFoundError(FileNotFoundError):
    """Raised when ffmpeg executable cannot be found."""
    pass


@lru_cache(maxsize=1)
def find_ffmpeg() -> str:
    """Look for a bundled ffmpeg.exe first, then fall back to PATH."""
    candidates = []
    if hasattr(sys, "_MEIPASS"):
        candidates.append(Path(sys._MEIPASS) / "vendor" / "ffmpeg.exe")
    candidates.append(Path(sys.executable).parent / "vendor" / "ffmpeg.exe")
    candidates.append(Path(__file__).resolve().parents[2] / "vendor" / "ffmpeg.exe")

    for bundled in candidates:
        if bundled.is_file():
            return str(bundled)

    found = shutil.which("ffmpeg")
    if found:
        return found
    raise FFmpegNotFoundError(
        "FFmpeg is missing. Install it (winget install Gyan.FFmpeg) or put ffmpeg.exe in vendor/."
    )


def is_ffmpeg_available() -> bool:
    try:
        find_ffmpeg()
        return True
    except FFmpegNotFoundError:
        return False


def run_ffmpeg(src: Path, dst: Path, extra: list[str]) -> None:
    ffmpeg_bin = find_ffmpeg()
    cmd = [ffmpeg_bin, "-y", "-loglevel", "error", "-i", str(src), *extra, str(dst)]
    flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0  # no console flash
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, creationflags=flags)
    except FileNotFoundError:
        raise FFmpegNotFoundError(
            "FFmpeg is missing. Install it (winget install Gyan.FFmpeg) or put ffmpeg.exe in vendor/."
        )
    if proc.returncode != 0:
        err = proc.stderr.strip().splitlines()[-1] if proc.stderr else f"ffmpeg failed with exit code {proc.returncode}"
        raise RuntimeError(err)


def _make_converter(extra: list[str]):
    def convert(src: Path, dst: Path) -> None:
        run_ffmpeg(src, dst, extra)

    return convert


for _ext, _extra in AUDIO_OUT.items():
    register(AUDIO + VIDEO, _ext)(_make_converter(_extra))  # video -> audio extraction too
for _ext, _extra in VIDEO_OUT.items():
    register(VIDEO, _ext)(_make_converter(_extra))
