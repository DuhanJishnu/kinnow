"""Wires everything together: tray icon, hotkey, overlay and worker pool."""
from __future__ import annotations

import logging
import sys
from pathlib import Path

from PySide6.QtCore import QThreadPool
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from dropwheel.converters import load_all
from dropwheel.hotkey import HotkeyListener
from dropwheel.ui.radial_menu import RadialMenu
from dropwheel.worker import ConvertJob, JobSignals


def make_icon() -> QIcon:
    pm = QPixmap(64, 64)
    pm.fill(QColor(0, 0, 0, 0))
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setBrush(QColor(242, 112, 36))
    p.setPen(QColor(0, 0, 0, 0))
    p.drawEllipse(4, 4, 56, 56)
    p.end()
    return QIcon(pm)


class DropWheelApp:
    def __init__(self) -> None:
        load_all()
        self.qt = QApplication(sys.argv)
        self.qt.setQuitOnLastWindowClosed(False)  # live in the tray, not in a window

        self.pool = QThreadPool.globalInstance()
        self.signals = JobSignals()
        self.signals.done.connect(self._on_done)
        self.signals.failed.connect(self._on_failed)

        self.menu = RadialMenu()
        self.menu.chosen.connect(self._on_chosen)

        self.hotkey = HotkeyListener()
        self.hotkey.triggered.connect(self.menu.show_at_cursor)

        self.tray = QSystemTrayIcon(make_icon())
        self.tray.setToolTip("DropWheel - press Shift while dragging a file")
        tray_menu = QMenu()
        quit_action = QAction("Quit")
        quit_action.triggered.connect(self.qt.quit)
        tray_menu.addAction(quit_action)
        self.tray.setContextMenu(tray_menu)
        self._tray_menu = tray_menu  # keep references alive
        self._quit_action = quit_action
        self.tray.show()

    def _on_chosen(self, paths: list, ext: str) -> None:
        for path in paths:
            self.pool.start(ConvertJob(Path(path), ext, self.signals))

    def _on_done(self, out: str) -> None:
        self.tray.showMessage("Converted", Path(out).name, QSystemTrayIcon.Information, 3000)

    def _on_failed(self, name: str, error: str) -> None:
        logging.error("Conversion failed for %s: %s", name, error)
        self.tray.showMessage(f"Failed: {name}", error, QSystemTrayIcon.Warning, 5000)

    def run(self) -> int:
        self.hotkey.start()
        code = self.qt.exec()
        self.hotkey.stop()
        return code


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    sys.exit(DropWheelApp().run())