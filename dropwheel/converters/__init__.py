"""Converters register themselves with `registry` when their module is imported."""


def load_all() -> None:
    """Import every converter module so its @register decorators run."""
    from . import images, markdown, media, pdf, text  # noqa: F401
