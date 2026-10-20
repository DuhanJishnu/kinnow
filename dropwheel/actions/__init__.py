"""Tool actions package: loads all action tools."""
from __future__ import annotations


def load_all_actions() -> None:
    """Import every action module so its @register_action decorators run."""
    from . import (  # noqa: F401
        archive_tools,
        file_tools,
        image_tools,
        markdown_tools,
        pdf_tools,
        video_tools,
    )
