"""The heart of the app: a lookup table  source-ext -> target-ext -> function.

Adding a new conversion = writing one function and decorating it with @register.
The UI never needs to change, because it only asks the registry what is possible.
"""
from __future__ import annotations

from collections.abc import Callable, Iterable
from pathlib import Path

from dropwheel.utils import unique_path

# A converter reads `src`, writes `dst`. It may return a different Path
# (e.g. a folder) if the result is not exactly `dst`.
Converter = Callable[[Path, Path], "Path | None"]

_REGISTRY: dict[str, dict[str, Converter]] = {}
_ALIASES = {"jpeg": "jpg", "tif": "tiff"}


class UnsupportedConversion(Exception):
    pass


def normalize(ext: str) -> str:
    ext = ext.lower().lstrip(".")
    return _ALIASES.get(ext, ext)


def ext_of(path: Path) -> str:
    return normalize(path.suffix)


def register(src_exts: Iterable[str], dst_ext: str) -> Callable[[Converter], Converter]:
    """Decorator: register `func` as converting each src ext -> dst_ext."""

    def decorator(func: Converter) -> Converter:
        dst = normalize(dst_ext)
        for src in src_exts:
            src = normalize(src)
            if src != dst:
                _REGISTRY.setdefault(src, {})[dst] = func
        return func

    return decorator


def targets_for(path: Path) -> list[str]:
    """Formats this file can be converted to (in registration order)."""
    return list(_REGISTRY.get(ext_of(path), {}))


def common_targets(paths: list[Path]) -> list[str]:
    """Formats that EVERY file in `paths` can be converted to."""
    if not paths:
        return []
    common = targets_for(paths[0])
    for p in paths[1:]:
        available = set(targets_for(p))
        common = [t for t in common if t in available]
    return common


def convert(src: Path, dst_ext: str) -> Path:
    """Convert `src` next to itself and return the output path."""
    dst_ext = normalize(dst_ext)
    func = _REGISTRY.get(ext_of(src), {}).get(dst_ext)
    if func is None:
        raise UnsupportedConversion(f"Cannot convert {src.suffix or 'this file'} to .{dst_ext}")
    dst = unique_path(src.with_suffix(f".{dst_ext}"))
    result = func(src, dst)
    return result if isinstance(result, Path) else dst
