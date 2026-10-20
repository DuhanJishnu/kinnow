"""Trigger detection by polling the keyboard/mouse state ~50 times per second.

The wheel is requested only when ALL of these are true:
  * the left mouse button is held,
  * Shift is held,
  * the cursor has moved a few pixels since the button went down = a real drag has begun.

Usage: start dragging a file, then press Shift (same as the Mac app Tangerine).
Pressing Shift BEFORE clicking makes Explorer treat the click as "extend selection",
so no file drag would start - that is an Explorer behaviour, not something we can change.

Waiting for the drag matters: if the overlay appeared at mouse-DOWN it would interfere with
Explorer's own click handling (the file would not get selected). By the time we show it,
Explorer has already selected the file and started dragging it.
"""
from __future__ import annotations

import logging

from PySide6.QtCore import QObject, QPoint, QTimer, Signal
from PySide6.QtGui import QCursor

from dropwheel.utils import is_left_mouse_down, is_shift_down, is_tab_down

DRAG_THRESHOLD_PX = 8
log = logging.getLogger(__name__)


class HotkeyListener(QObject):
    # Emitted while dragging with Shift (convert mode) or Tab (tools mode).
    triggered = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._origin: QPoint | None = None
        self._fired = False
        self._timer = QTimer(self, interval=20)
        self._timer.timeout.connect(self._poll)

    def start(self) -> None:
        self._timer.start()

    def stop(self) -> None:
        self._timer.stop()

    def _poll(self) -> None:
        if not is_left_mouse_down():
            if self._origin is not None:
                log.info("mouse released")
            self._origin = None
            self._fired = False
            return
        pos = QCursor.pos()
        if self._origin is None:  # button just went down: remember where
            self._origin = pos
            log.info("mouse down at (%d,%d), shift=%s, tab=%s", pos.x(), pos.y(), is_shift_down(), is_tab_down())

        if (pos - self._origin).manhattanLength() >= DRAG_THRESHOLD_PX:
            mode: str | None = None
            if is_tab_down():
                mode = "tools"
            elif is_shift_down():
                mode = "convert"

            if mode:
                if not self._fired:
                    self._fired = True
                    log.info("trigger: drag detected with %s at (%d,%d)", mode, pos.x(), pos.y())
                self.triggered.emit(mode)