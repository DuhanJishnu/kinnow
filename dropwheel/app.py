"""Wires everything together: tray icon, hotkey, overlay and worker pool."""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from PySide6.QtCore import QThreadPool
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from dropwheel.actions import load_all_actions
from dropwheel.converters import load_all
from dropwheel.hotkey import HotkeyListener
from dropwheel.ui.radial_menu import RadialMenu
from dropwheel.utils import (
    create_shortcut,
    get_app_executable,
    get_desktop_shortcut_path,
    get_start_menu_shortcut_path,
    is_startup_enabled,
    reveal_in_explorer,
    toggle_startup,
)
from dropwheel.worker import ConvertJob, JobSignals, ToolJob


def get_icon() -> QIcon:
    """Load the Kinnow app icon from bundled assets, with fallback."""
    candidates = []
    if hasattr(sys, "_MEIPASS"):
        candidates.append(Path(sys._MEIPASS) / "assets" / "kinnow.png")
        candidates.append(Path(sys._MEIPASS) / "assets" / "kinnow.ico")
    candidates.append(Path(sys.executable).parent / "_internal" / "assets" / "kinnow.png")
    candidates.append(Path(sys.executable).parent / "assets" / "kinnow.png")
    candidates.append(Path(__file__).resolve().parents[1] / "assets" / "kinnow.png")
    candidates.append(Path(__file__).resolve().parents[1] / "assets" / "kinnow.ico")

    for c in candidates:
        if c.is_file():
            return QIcon(str(c))

    # Fallback to drawn icon if asset is somehow missing
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
        load_all_actions()
        self.qt = QApplication(sys.argv)
        self.qt.setApplicationName("Kinnow")
        self.qt.setApplicationDisplayName("Kinnow")
        self.qt.setQuitOnLastWindowClosed(False)  # live in the tray, not in a window

        self.pool = QThreadPool.globalInstance()
        self.signals = JobSignals()
        self.signals.done.connect(self._on_done)
        self.signals.failed.connect(self._on_failed)

        self.menu = RadialMenu()
        self.menu.chosen.connect(self._on_chosen)
        self.menu.action_chosen.connect(self._on_action_chosen)

        self.hotkey = HotkeyListener()
        self.hotkey.triggered.connect(self.menu.show_at_cursor)

        icon = get_icon()
        self.qt.setWindowIcon(icon)
        self.tray = QSystemTrayIcon(icon)
        self.tray.setToolTip("Kinnow - Shift to Convert, Tab for Tools")
        self.tray.messageClicked.connect(self._on_message_clicked)

        tray_menu = QMenu()
        self._reveal_action = QAction("Reveal in Explorer", tray_menu)
        self._reveal_action.setEnabled(False)
        self._reveal_action.triggered.connect(self._on_message_clicked)
        tray_menu.addAction(self._reveal_action)
        tray_menu.addSeparator()

        desktop_action = QAction("Add to Desktop", tray_menu)
        desktop_action.triggered.connect(self._add_desktop_shortcut)
        tray_menu.addAction(desktop_action)

        start_menu_action = QAction("Add to Start Menu", tray_menu)
        start_menu_action.triggered.connect(self._add_start_menu_shortcut)
        tray_menu.addAction(start_menu_action)

        self._startup_action = QAction("Start with Windows", tray_menu)
        self._startup_action.setCheckable(True)
        self._startup_action.setChecked(is_startup_enabled())
        self._startup_action.toggled.connect(self._toggle_startup)
        tray_menu.addAction(self._startup_action)
        tray_menu.addSeparator()

        quit_action = QAction("Quit")
        quit_action.triggered.connect(self.qt.quit)
        tray_menu.addAction(quit_action)
        self.tray.setContextMenu(tray_menu)
        self._tray_menu = tray_menu  # keep references alive
        self._quit_action = quit_action
        self._last_converted: Path | None = None
        self.tray.show()

    def _add_desktop_shortcut(self) -> None:
        exe = get_app_executable()
        lnk = get_desktop_shortcut_path()
        if create_shortcut(exe, lnk):
            self.tray.showMessage(
                "Desktop Shortcut Created",
                "Kinnow shortcut has been added to your Desktop.",
                QSystemTrayIcon.Information,
                3000,
            )
        else:
            self.tray.showMessage(
                "Shortcut Failed",
                "Could not create Desktop shortcut.",
                QSystemTrayIcon.Warning,
                3000,
            )

    def _add_start_menu_shortcut(self) -> None:
        exe = get_app_executable()
        lnk = get_start_menu_shortcut_path()
        if create_shortcut(exe, lnk):
            self.tray.showMessage(
                "Start Menu Shortcut Created",
                "Kinnow has been added to your Windows Start Menu.",
                QSystemTrayIcon.Information,
                3000,
            )
        else:
            self.tray.showMessage(
                "Shortcut Failed",
                "Could not create Start Menu shortcut.",
                QSystemTrayIcon.Warning,
                3000,
            )

    def _toggle_startup(self, checked: bool) -> None:
        toggle_startup(checked)
        status = "enabled" if checked else "disabled"
        self.tray.showMessage(
            "Startup Setting Updated",
            f"Kinnow start with Windows is now {status}.",
            QSystemTrayIcon.Information,
            3000,
        )

    def _on_chosen(self, paths: list, ext: str) -> None:
        for path in paths:
            self.pool.start(ConvertJob(Path(path), ext, self.signals))

    def _on_action_chosen(self, action_id: str, paths: list) -> None:
        self.pool.start(ToolJob(action_id, [Path(p) for p in paths], self.signals))

    def _on_done(self, out: str) -> None:
        self._last_converted = Path(out)
        self._reveal_action.setText(f"Reveal '{self._last_converted.name}' in Explorer")
        self._reveal_action.setEnabled(True)
        self.tray.showMessage(
            "Finished (click to reveal)",
            self._last_converted.name,
            QSystemTrayIcon.Information,
            4000,
        )

    def _on_message_clicked(self) -> None:
        if self._last_converted:
            reveal_in_explorer(self._last_converted)

    def _on_failed(self, name: str, error: str) -> None:
        logging.error("Conversion failed for %s: %s", name, error)
        if "ffmpeg" in error.lower() and ("missing" in error.lower() or "not found" in error.lower()):
            self.tray.showMessage(
                "FFmpeg is Missing",
                "FFmpeg is required for audio/video conversion. Run 'winget install Gyan.FFmpeg' or place ffmpeg.exe in vendor/.",
                QSystemTrayIcon.Warning,
                6000,
            )
        else:
            self.tray.showMessage(f"Failed: {name}", error, QSystemTrayIcon.Warning, 5000)

    def run(self) -> int:
        self.hotkey.start()
        code = self.qt.exec()
        self.hotkey.stop()
        return code


KinnowApp = DropWheelApp


def setup_logging() -> Path | None:
    """Configure logging: WARNING to console (terminal not noisy) and INFO to a log file."""
    log_dir = Path(os.environ.get("LOCALAPPDATA", Path.home() / ".kinnow")) / "Kinnow"
    log_file: Path | None = None
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "kinnow.log"
    except Exception:
        pass

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()

    # Terminal output: WARNING and ERROR only, keeping console quiet
    console = logging.StreamHandler(sys.stderr)
    console.setLevel(logging.WARNING)
    console.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    root.addHandler(console)

    if log_file:
        try:
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setLevel(logging.INFO)
            file_handler.setFormatter(
                logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
            )
            root.addHandler(file_handler)
        except Exception:
            pass

    return log_file


def main() -> None:
    setup_logging()
    sys.exit(DropWheelApp().run())