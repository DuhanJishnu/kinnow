"""Run conversions on a thread pool so the UI never freezes."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, Signal

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
