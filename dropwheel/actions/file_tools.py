"""General file quick tools: View Properties / Metadata."""
from __future__ import annotations

from pathlib import Path

from dropwheel.actions.registry import register_action
from dropwheel.utils import open_file_properties


def _always_applicable(paths: list[Path]) -> bool:
    return bool(paths) and all(p.exists() for p in paths)


@register_action(
    id="file_properties",
    label="METADATA",
    title="Open File Properties & Metadata",
    is_applicable=_always_applicable,
)
def view_file_properties(paths: list[Path]) -> None:
    """Open Windows native file properties dialog for the selected file(s)."""
    for p in paths:
        open_file_properties(p)
    return None
