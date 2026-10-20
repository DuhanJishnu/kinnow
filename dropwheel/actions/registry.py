"""Registry for quick tool actions (Compress, Merge, Split, etc.)."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable


@dataclass
class Action:
    id: str
    label: str               # Short uppercase name for slice (e.g. 'COMPRESS', 'MERGE')
    title: str               # User-friendly description (e.g. 'Compress PDF size')
    is_applicable: Callable[[list[Path]], bool]
    execute: Callable[[list[Path]], Path]


_ACTIONS: dict[str, Action] = {}


def register_action(
    id: str,
    label: str,
    title: str,
    is_applicable: Callable[[list[Path]], bool],
) -> Callable[[Callable[[list[Path]], Path]], Callable[[list[Path]], Path]]:
    """Decorator to register a tool action."""

    def decorator(func: Callable[[list[Path]], Path]) -> Callable[[list[Path]], Path]:
        _ACTIONS[id] = Action(
            id=id,
            label=label,
            title=title,
            is_applicable=is_applicable,
            execute=func,
        )
        return func

    return decorator


def get_action(action_id: str) -> Action | None:
    return _ACTIONS.get(action_id)


def applicable_actions(paths: list[Path]) -> list[Action]:
    """Return all actions applicable to the given files in registration order."""
    if not paths:
        return []
    result = []
    for action in _ACTIONS.values():
        try:
            if action.is_applicable(paths):
                result.append(action)
        except Exception:
            pass
    return result


def execute_action(action_id: str, paths: list[Path]) -> Path:
    action = _ACTIONS.get(action_id)
    if not action:
        raise ValueError(f"Unknown action: {action_id}")
    return action.execute(paths)
