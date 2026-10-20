"""Video quick tools: Mute, Extract Audio, and Make GIF."""
from __future__ import annotations

from pathlib import Path

from dropwheel.actions.registry import register_action
from dropwheel.converters.media import run_ffmpeg
from dropwheel.utils import unique_path

VIDEO_EXTS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".m4v"}


def _is_all_videos(paths: list[Path]) -> bool:
    return bool(paths) and all(p.suffix.lower() in VIDEO_EXTS for p in paths)


@register_action(
    id="mute_video",
    label="MUTE",
    title="Mute Video (Strip Audio Track)",
    is_applicable=_is_all_videos,
)
def mute_video(paths: list[Path]) -> Path:
    """Strip audio tracks without re-encoding in under 1 second (-c:v copy -an)."""
    last_out = None
    for src in paths:
        dst = unique_path(src.with_name(f"{src.stem}_muted{src.suffix}"))
        run_ffmpeg(src, dst, ["-c:v", "copy", "-an"])
        last_out = dst
    return last_out or paths[0]


@register_action(
    id="extract_audio",
    label="AUDIO",
    title="Extract Audio to MP3",
    is_applicable=_is_all_videos,
)
def extract_audio(paths: list[Path]) -> Path:
    """Extract audio directly to high-quality MP3."""
    last_out = None
    for src in paths:
        dst = unique_path(src.with_suffix(".mp3"))
        run_ffmpeg(src, dst, ["-vn", "-q:a", "2"])
        last_out = dst
    return last_out or paths[0]


@register_action(
    id="make_gif",
    label="MAKE GIF",
    title="Convert Video to Animated GIF",
    is_applicable=_is_all_videos,
)
def make_gif(paths: list[Path]) -> Path:
    """Convert video clip to an optimized animated GIF."""
    last_out = None
    for src in paths:
        dst = unique_path(src.with_suffix(".gif"))
        run_ffmpeg(src, dst, ["-vf", "fps=12,scale=480:-1:flags=lanczos", "-an"])
        last_out = dst
    return last_out or paths[0]
