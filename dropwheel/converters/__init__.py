"""Converters register themselves with `registry` when their module is imported."""


def load_all() -> None:
    """Import every converter module so its @register decorators run."""
    from . import (  # noqa: F401
        documents,
        images,
        markdown,
        media,
        pdf,
        spreadsheets,
        text,
    )
