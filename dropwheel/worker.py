"""Run conversions on a thread pool so the UI never freezes."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, Signal

from dropwheel.actions import registry as actions_registry
from dropwheel.converters import registry


class JobSignals(QObject):
    done = Signal(str)          # output path
    failed = Signal(str, str)   # input file name, error message


class ConvertJob(QRunnable):
    def __init__(self, src: Path, dst_ext: str, signals: JobSignals) -> None:
        super().__init__()
        self.src = src
        self.dst_ext = dst_ext
        self.signals = signals

    def run(self) -> None:  # executes on a pool thread
        try:
            out = registry.convert(self.src, self.dst_ext)
            self.signals.done.emit(str(out))
        except Exception as exc:  # show any failure to the user instead of crashing
            self.signals.failed.emit(self.src.name, str(exc))


class ToolJob(QRunnable):
    def __init__(self, action_id: str, paths: list[Path], signals: JobSignals) -> None:
        super().__init__()
        self.action_id = action_id
        self.paths = paths
        self.signals = signals

    def run(self) -> None:
        try:
            out = actions_registry.execute_action(self.action_id, self.paths)
            if out is not None and self.action_id != "file_properties":
                self.signals.done.emit(str(out))
        except Exception as exc:
            name = self.paths[0].name if self.paths else "Tool action"
            self.signals.failed.emit(name, str(exc))
