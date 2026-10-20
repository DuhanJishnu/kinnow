"""The transparent, always-on-top radial overlay that receives the dropped file."""
from __future__ import annotations

import logging
import math
from pathlib import Path

from PySide6.QtCore import (
    QEasingCurve,
    QPointF,
    QRectF,
    Qt,
    QTimer,
    QVariantAnimation,
    Signal,
)
from PySide6.QtGui import (
    QColor,
    QCursor,
    QFont,
    QGuiApplication,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QRadialGradient,
)
from PySide6.QtWidgets import QWidget

from dropwheel.actions import registry as actions_registry
from dropwheel.converters import registry
from dropwheel.utils import clamp_to_screen, is_left_mouse_down

log = logging.getLogger(__name__)

SIZE = 400
OUTER_R = 162
INNER_R = 80
HOVER_EXPAND = 7.0   # Maximum outward pixel expansion at full hover (t = 1.0)
GAP_PX = 7.0         # Constant linear pixel gap between slices
CORNER_R = 10.0      # Corner rounding radius for each wedge


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _lerp_color(c1: QColor, c2: QColor, t: float) -> QColor:
    t = max(0.0, min(1.0, t))
    return QColor(
        int(c1.red() + (c2.red() - c1.red()) * t),
        int(c1.green() + (c2.green() - c1.green()) * t),
        int(c1.blue() + (c2.blue() - c1.blue()) * t),
        int(c1.alpha() + (c2.alpha() - c1.alpha()) * t),
    )


class RadialMenu(QWidget):
    chosen = Signal(list, str)          # (list of Paths, target extension)
    action_chosen = Signal(str, list)   # (action_id, list of Paths)

    def __init__(self) -> None:
        super().__init__()
        self.setWindowFlags(
            Qt.Tool                       # no taskbar button
            | Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.WindowDoesNotAcceptFocus  # don't steal focus from Explorer mid-drag
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAcceptDrops(True)
        self.setFixedSize(SIZE, SIZE)

        self._mode: str = "convert"     # "convert" (Shift) or "tools" (Tab)
        self._action_items: list = []
        self._paths: list[Path] = []
        self._targets: list[str] = []
        self._hover: int | None = None
        self._message = "Drag a file\nonto the wheel"

        # Animation state
        self._open_progress: float = 0.0
        self._hover_progress: list[float] = []
        self._hover_anims: list[QVariantAnimation] = []

        self._open_anim = QVariantAnimation(self)
        self._open_anim.setDuration(240)
        self._open_anim.setEasingCurve(QEasingCurve.OutBack)
        self._open_anim.valueChanged.connect(self._on_open_anim_step)

        # The overlay is "armed" (invisible) as soon as Shift is pressed during a drag,
        # but the wheel is only DRAWN once a file drag actually enters it.
        # _locked: after closing, ignore Shift until the mouse button is released,
        # so key auto-repeat can't re-open the wheel somewhere else mid-drag.
        self._locked = False
        self._watch = QTimer(self, interval=100)
        self._watch.timeout.connect(self._tick)
        self._watch.start()

    # ---------- animation controllers ----------
    def _on_open_anim_step(self, value: float) -> None:
        self._open_progress = float(value)
        self.update()

    def _init_slice_animations(self, n: int) -> None:
        for anim in self._hover_anims:
            anim.stop()
            anim.deleteLater()
        self._hover_anims.clear()
        self._hover_progress = [0.0] * n

        for idx in range(n):
            anim = QVariantAnimation(self)
            anim.setDuration(160)
            anim.setEasingCurve(QEasingCurve.OutCubic)
            anim.valueChanged.connect(
                lambda val, i=idx: self._on_hover_anim_step(i, float(val))
            )
            self._hover_anims.append(anim)

    def _on_hover_anim_step(self, idx: int, val: float) -> None:
        if idx < len(self._hover_progress):
            self._hover_progress[idx] = val
            self.update()

    def _set_hovered_slice(self, new_hover: int | None) -> None:
        if new_hover == self._hover:
            return
        self._hover = new_hover
        for i, anim in enumerate(self._hover_anims):
            target = 1.0 if i == new_hover else 0.0
            current = self._hover_progress[i]
            if math.isclose(current, target, abs_tol=1e-3):
                continue
            anim.stop()
            anim.setStartValue(current)
            anim.setEndValue(target)
            anim.start()

    # ---------- showing / hiding ----------
    def show_at_cursor(self, mode: str = "convert") -> None:
        if self.isVisible():
            if mode != self._mode:
                self.set_mode(mode)
            return  # key auto-repeat calls this many times; ignore repeats
        if self._locked:
            return
        self._mode = mode
        self._paths, self._targets, self._hover = [], [], None
        self._action_items = []
        self._open_progress = 0.0
        self._init_slice_animations(0)
        self._message = "Drag a file\nonto the wheel"
        pos = QCursor.pos()
        x = pos.x() - SIZE // 2
        y = pos.y() - SIZE // 2
        screen = QGuiApplication.screenAt(pos) or QGuiApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            x, y = clamp_to_screen(
                x, y, SIZE, SIZE, (geo.left(), geo.top(), geo.width(), geo.height())
            )
        self.move(x, y)
        self.show()
        self.raise_()
        log.info("overlay shown (armed) [%s] at (%d,%d)", mode, x, y)

    def set_mode(self, mode: str) -> None:
        if mode == self._mode:
            return
        self._mode = mode
        log.info("wheel mode switched to %s", mode)
        if self._paths:
            self._update_slices_for_current_mode()
            self.update()

    def _update_slices_for_current_mode(self) -> None:
        if self._mode == "tools":
            self._action_items = actions_registry.applicable_actions(self._paths)
            self._targets = [a.label for a in self._action_items]
            if not self._targets:
                self._message = "No tools\nfor this file"
        else:
            self._targets = registry.common_targets(self._paths)
            if not self._targets:
                self._message = "No common\nconversions" if len(self._paths) > 1 else "No conversions\nfor this file"
        self._hover = None
        self._init_slice_animations(len(self._targets))

    def hideEvent(self, event) -> None:
        log.info("overlay hidden")
        self._open_anim.stop()
        for anim in self._hover_anims:
            anim.stop()
        self._locked = True
        super().hideEvent(event)

    def _tick(self) -> None:
        if is_left_mouse_down():
            return
        if self.isVisible() and not self._paths:
            self.hide()  # armed but no file drag ever entered: it was just a click
        elif self._locked and not self.isVisible():
            self._locked = False

    # ---------- geometry helpers ----------
    @property
    def _c(self) -> QPointF:
        return QPointF(SIZE / 2, SIZE / 2)

    @staticmethod
    def _pt_on_circle(c: QPointF, r: float, angle_deg: float) -> QPointF:
        rad = math.radians(angle_deg)
        return QPointF(c.x() + r * math.cos(rad), c.y() - r * math.sin(rad))

    def _slice_at(self, p: QPointF) -> int | None:
        n = len(self._targets)
        if n == 0:
            return None
        dx, dy = p.x() - self._c.x(), p.y() - self._c.y()
        dist = math.hypot(dx, dy)
        if not (INNER_R <= dist <= OUTER_R + HOVER_EXPAND):
            return None
        if n == 1:
            return 0
        ccw_deg = math.degrees(math.atan2(-dy, dx)) % 360  # 0 = east, counter-clockwise
        clockwise_from_top = (90 - ccw_deg) % 360
        return int(clockwise_from_top // (360 / n))

    def _slice_path(self, i: int, n: int, hover_t: float = 0.0) -> QPainterPath:
        c = self._c
        r_out = OUTER_R + HOVER_EXPAND * hover_t
        r_in = INNER_R

        gap_out = math.degrees(math.asin(min(0.95, (GAP_PX / 2) / r_out)))
        gap_in = math.degrees(math.asin(min(0.95, (GAP_PX / 2) / r_in)))

        if n == 1:
            theta1 = -90.0
            theta2 = 270.0
        else:
            span = 360.0 / n
            theta1 = 90.0 - (i + 1) * span
            theta2 = 90.0 - i * span

        gap_out = math.degrees(math.asin(min(0.95, (GAP_PX / 2) / r_out)))
        gap_in = math.degrees(math.asin(min(0.95, (GAP_PX / 2) / r_in)))

        a_out_start = theta1 + gap_out
        a_out_end = theta2 - gap_out
        a_in_start = theta1 + gap_in
        a_in_end = theta2 - gap_in

        rc = min(CORNER_R, (r_out - r_in) / 3.0)
        d_out = math.degrees(math.asin(min(0.95, rc / r_out)))
        d_in = math.degrees(math.asin(min(0.95, rc / r_in)))

        out_arc_sweep = (a_out_end - d_out) - (a_out_start + d_out)
        in_arc_sweep = (a_in_end - d_in) - (a_in_start + d_in)

        outer_rect = QRectF(c.x() - r_out, c.y() - r_out, 2 * r_out, 2 * r_out)
        inner_rect = QRectF(c.x() - r_in, c.y() - r_in, 2 * r_in, 2 * r_in)

        if out_arc_sweep <= 0 or in_arc_sweep <= 0:
            path = QPainterPath()
            path.arcMoveTo(outer_rect, a_out_start)
            path.arcTo(outer_rect, a_out_start, max(0.1, a_out_end - a_out_start))
            path.arcTo(inner_rect, a_in_end, -max(0.1, a_in_end - a_in_start))
            path.closeSubpath()
            return path

        path = QPainterPath()

        # 1. Outer arc
        path.arcMoveTo(outer_rect, a_out_start + d_out)
        path.arcTo(outer_rect, a_out_start + d_out, out_arc_sweep)

        # 2. Outer-End rounded corner -> radial edge down to Inner-End
        ctrl_out_end = self._pt_on_circle(c, r_out, a_out_end)
        pt_rad_end_out = self._pt_on_circle(c, r_out - rc, a_out_end)
        path.quadTo(ctrl_out_end, pt_rad_end_out)

        pt_rad_end_in = self._pt_on_circle(c, r_in + rc, a_in_end)
        path.lineTo(pt_rad_end_in)

        # 3. Inner-End rounded corner -> Inner arc
        ctrl_in_end = self._pt_on_circle(c, r_in, a_in_end)
        pt_in_arc_end = self._pt_on_circle(c, r_in, a_in_end - d_in)
        path.quadTo(ctrl_in_end, pt_in_arc_end)

        path.arcTo(inner_rect, a_in_end - d_in, -in_arc_sweep)

        # 4. Inner-Start rounded corner -> radial edge up to Outer-Start
        ctrl_in_start = self._pt_on_circle(c, r_in, a_in_start)
        pt_rad_start_in = self._pt_on_circle(c, r_in + rc, a_in_start)
        path.quadTo(ctrl_in_start, pt_rad_start_in)

        pt_rad_start_out = self._pt_on_circle(c, r_out - rc, a_out_start)
        path.lineTo(pt_rad_start_out)

        # 5. Outer-Start rounded corner closing the loop
        ctrl_out_start = self._pt_on_circle(c, r_out, a_out_start)
        pt_out_arc_start = self._pt_on_circle(c, r_out, a_out_start + d_out)
        path.quadTo(ctrl_out_start, pt_out_arc_start)

        path.closeSubpath()
        return path

    # ---------- drag & drop ----------
    def dragEnterEvent(self, event) -> None:
        urls = event.mimeData().urls()
        paths = [Path(u.toLocalFile()) for u in urls if u.isLocalFile()]
        paths = [p for p in paths if p.is_file()]
        log.info("dragEnter: %d file(s) %s", len(paths), [p.suffix for p in paths])
        if not paths:
            event.ignore()
            return

        first_entry = not self._paths
        self._paths = paths
        self._update_slices_for_current_mode()

        if not self._targets:
            event.ignore()
        else:
            event.acceptProposedAction()

        if first_entry:
            self._open_anim.stop()
            self._open_anim.setStartValue(0.0)
            self._open_anim.setEndValue(1.0)
            self._open_anim.start()
        else:
            self.update()

    def dragMoveEvent(self, event) -> None:
        hover = self._slice_at(event.position())
        self._set_hovered_slice(hover)
        event.acceptProposedAction()

    def dragLeaveEvent(self, event) -> None:
        log.info("dragLeave")
        self.hide()

    def dropEvent(self, event) -> None:
        idx = self._slice_at(event.position())
        log.info("drop on slice %s (mode=%s)", idx, self._mode)
        if idx is not None:
            event.setDropAction(Qt.CopyAction)  # copy, so Explorer never deletes the original
            event.accept()
            if self._mode == "tools" and idx < len(self._action_items):
                self.action_chosen.emit(self._action_items[idx].id, self._paths)
            elif idx < len(self._targets):
                self.chosen.emit(self._paths, self._targets[idx])
        else:
            event.ignore()
        self.hide()

    # ---------- painting helpers ----------
    def _draw_ambient_backdrop(self, p: QPainter, c: QPointF) -> None:
        p.setPen(QPen(QColor(218, 224, 232, 180), 1.2))
        p.setBrush(QColor(245, 247, 250, 60))
        p.drawEllipse(c, OUTER_R + 6, OUTER_R + 6)

    def _draw_task_icon(
        self, p: QPainter, label: str, ix: float, iy: float, color: QColor
    ) -> bool:
        tag = label.upper().strip()
        p.save()
        p.setRenderHint(QPainter.Antialiasing)
        pen = QPen(color, 1.8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)

        if "COMPRESS" in tag:
            # Two diagonal arrows pointing inward towards center (as in screenshot)
            p.drawLine(QPointF(ix - 5.5, iy - 5.5), QPointF(ix - 1.2, iy - 1.2))
            p.drawLine(QPointF(ix - 4.2, iy - 1.2), QPointF(ix - 1.2, iy - 1.2))
            p.drawLine(QPointF(ix - 1.2, iy - 4.2), QPointF(ix - 1.2, iy - 1.2))

            p.drawLine(QPointF(ix + 5.5, iy + 5.5), QPointF(ix + 1.2, iy + 1.2))
            p.drawLine(QPointF(ix + 4.2, iy + 1.2), QPointF(ix + 1.2, iy + 1.2))
            p.drawLine(QPointF(ix + 1.2, iy + 4.2), QPointF(ix + 1.2, iy + 1.2))
            p.restore()
            return True

        if "EXTRACT" in tag:
            # Open box with arrow pointing up out of it (as in screenshot)
            path = QPainterPath()
            path.moveTo(ix - 6.5, iy - 0.5)
            path.lineTo(ix - 6.5, iy + 5.5)
            path.lineTo(ix + 6.5, iy + 5.5)
            path.lineTo(ix + 6.5, iy - 0.5)
            p.drawPath(path)
            p.drawLine(QPointF(ix - 7.5, iy - 1.0), QPointF(ix + 7.5, iy - 1.0))

            p.drawLine(QPointF(ix, iy + 3.0), QPointF(ix, iy - 5.5))
            p.drawLine(QPointF(ix - 3.0, iy - 3.0), QPointF(ix, iy - 5.8))
            p.drawLine(QPointF(ix + 3.0, iy - 3.0), QPointF(ix, iy - 5.8))
            p.restore()
            return True

        if "METADATA" in tag or "PROP" in tag or "INFO" in tag:
            # Angled tag with hole (as in screenshot)
            p.save()
            p.translate(ix, iy)
            p.rotate(-45)
            tag_path = QPainterPath()
            tag_path.moveTo(-5.5, -3.5)
            tag_path.lineTo(2.0, -3.5)
            tag_path.lineTo(6.0, 0.0)
            tag_path.lineTo(2.0, 3.5)
            tag_path.lineTo(-5.5, 3.5)
            tag_path.closeSubpath()
            p.drawPath(tag_path)
            p.setBrush(color)
            p.setPen(Qt.NoPen)
            p.drawEllipse(QPointF(-2.5, 0.0), 1.2, 1.2)
            p.restore()
            p.restore()
            return True

        if "SPLIT" in tag:
            # Two vertical document pills (as in screenshot)
            p.drawRoundedRect(QRectF(ix - 6.5, iy - 6.0, 5.0, 12.0), 2.0, 2.0)
            p.drawRoundedRect(QRectF(ix + 1.5, iy - 6.0, 5.0, 12.0), 2.0, 2.0)
            p.restore()
            return True

        if "MERGE" in tag or "ORGANIZE" in tag:
            # 4 squares in 2x2 grid (as in screenshot)
            p.drawRoundedRect(QRectF(ix - 6.5, iy - 6.5, 5.0, 5.0), 1.2, 1.2)
            p.drawRoundedRect(QRectF(ix + 1.5, iy - 6.5, 5.0, 5.0), 1.2, 1.2)
            p.drawRoundedRect(QRectF(ix - 6.5, iy + 1.5, 5.0, 5.0), 1.2, 1.2)
            p.drawRoundedRect(QRectF(ix + 1.5, iy + 1.5, 5.0, 5.0), 1.2, 1.2)
            p.restore()
            return True

        if "ZIP" in tag:
            # Archive box with horizontal band
            p.drawRoundedRect(QRectF(ix - 6.0, iy - 5.5, 12.0, 11.0), 2.0, 2.0)
            p.drawLine(QPointF(ix - 6.0, iy - 0.5), QPointF(ix + 6.0, iy - 0.5))
            p.drawLine(QPointF(ix - 1.5, iy - 3.5), QPointF(ix + 1.5, iy - 3.5))
            p.drawLine(QPointF(ix - 1.5, iy + 2.5), QPointF(ix + 1.5, iy + 2.5))
            p.restore()
            return True

        if "EXIF" in tag or "STRIP" in tag or "CLEAN" in tag:
            # Tag with clean slash /
            p.drawRoundedRect(QRectF(ix - 6.0, iy - 5.0, 12.0, 10.0), 2.0, 2.0)
            p.drawEllipse(QPointF(ix, iy), 2.0, 2.0)
            p.drawLine(QPointF(ix - 7.0, iy + 6.0), QPointF(ix + 7.0, iy - 6.0))
            p.restore()
            return True

        if "RESIZE" in tag or "50%" in tag:
            # Scaling frame
            p.drawRect(QRectF(ix - 6.0, iy - 6.0, 12.0, 12.0))
            p.drawRect(QRectF(ix - 6.0, iy, 6.0, 6.0))
            p.restore()
            return True

        if "GRAYSCALE" in tag or "B&W" in tag:
            # Half-filled contrast circle ◐
            p.drawEllipse(QPointF(ix, iy), 6.0, 6.0)
            p.setBrush(color)
            p.setPen(Qt.NoPen)
            p.drawPie(QRectF(ix - 6.0, iy - 6.0, 12.0, 12.0), 90 * 16, 180 * 16)
            p.restore()
            return True

        if "HTML" in tag:
            # < / > brackets
            p.drawLine(QPointF(ix - 3.0, iy - 4.5), QPointF(ix - 6.5, iy))
            p.drawLine(QPointF(ix - 6.5, iy), QPointF(ix - 3.0, iy + 4.5))
            p.drawLine(QPointF(ix - 1.0, iy + 4.5), QPointF(ix + 1.0, iy - 4.5))
            p.drawLine(QPointF(ix + 3.0, iy - 4.5), QPointF(ix + 6.5, iy))
            p.drawLine(QPointF(ix + 6.5, iy), QPointF(ix + 3.0, iy + 4.5))
            p.restore()
            return True

        if "PDF" in tag:
            # Document page with folded corner
            path = QPainterPath()
            path.moveTo(ix - 5.0, iy - 6.5)
            path.lineTo(ix + 1.5, iy - 6.5)
            path.lineTo(ix + 5.5, iy - 2.5)
            path.lineTo(ix + 5.5, iy + 6.5)
            path.lineTo(ix - 5.0, iy + 6.5)
            path.closeSubpath()
            p.drawPath(path)
            p.drawLine(QPointF(ix + 1.5, iy - 6.5), QPointF(ix + 1.5, iy - 2.5))
            p.drawLine(QPointF(ix + 1.5, iy - 2.5), QPointF(ix + 5.5, iy - 2.5))
            p.restore()
            return True

        p.restore()
        return False

    def _draw_crystal_slice(
        self, p: QPainter, path: QPainterPath, i: int, n: int, t: float
    ) -> None:
        c = self._c
        bounds = path.boundingRect()

        # 1. Soft drop shadow per wedge (deepens with hover progress t)
        p.save()
        p.translate(0, _lerp(2.0, 3.5, t))
        p.fillPath(path, QColor(0, 0, 0, int(_lerp(28, 55, t))))
        p.restore()

        # 2. Slice Base Fill: Clean off-white frosted glass -> Kinnow tangerine orange
        base_color = _lerp_color(QColor(240, 243, 247, 242), QColor(228, 88, 30, 248), t)
        p.fillPath(path, base_color)

        # 3. Subtle internal sheen (adds light depth)
        sheen = QLinearGradient(bounds.topLeft(), bounds.bottomLeft())
        sheen.setColorAt(0.0, _lerp_color(QColor(255, 255, 255, 110), QColor(255, 255, 255, 60), t))
        sheen.setColorAt(0.5, _lerp_color(QColor(255, 255, 255, 20), QColor(255, 255, 255, 0), t))
        sheen.setColorAt(1.0, _lerp_color(QColor(220, 226, 234, 50), QColor(198, 65, 15, 60), t))
        p.fillPath(path, sheen)

        # 4. Subtle Border Rim (crisp outline)
        rim_color = _lerp_color(QColor(218, 224, 232, 210), QColor(255, 145, 80, 220), t)
        p.setPen(QPen(rim_color, _lerp(1.2, 1.8, t)))
        p.setBrush(Qt.NoBrush)
        p.drawPath(path)

        # 5. Label and Icon Positioning
        mid_rad = math.radians(90.0 if n == 1 else (90 - (i + 0.5) * 360 / n))
        r_center = (INNER_R + OUTER_R + HOVER_EXPAND * t) / 2
        tx = c.x() + r_center * math.cos(mid_rad)
        ty = c.y() - r_center * math.sin(mid_rad)

        ext_label = self._targets[i].upper()
        glyph_color = _lerp_color(QColor(20, 23, 27, 235), QColor(255, 255, 255, 255), t)

        has_icon = self._draw_task_icon(p, ext_label, tx, ty - 8.5, glyph_color)
        if has_icon:
            text_y = ty + 9.5
            font = QFont("Segoe UI")
            font.setPointSizeF(_lerp(7.6, 8.2, t))
            font.setWeight(QFont.Bold)
            font.setLetterSpacing(QFont.AbsoluteSpacing, 0.4)
            p.setFont(font)

            text_rect = QRectF(tx - 46, text_y - 10, 92, 20)
            p.setPen(glyph_color)
            p.drawText(text_rect, Qt.AlignCenter, ext_label)
        else:
            # Format slice without icon: reduced, clean typography
            font = QFont("Segoe UI")
            font.setPointSizeF(_lerp(8.4, 9.0, t))
            font.setWeight(QFont.Bold)
            font.setLetterSpacing(QFont.AbsoluteSpacing, 0.6)
            p.setFont(font)

            text_rect = QRectF(tx - 44, ty - 12, 88, 24)
            p.setPen(glyph_color)
            p.drawText(text_rect, Qt.AlignCenter, ext_label)

    def _draw_center_orb(self, p: QPainter, c: QPointF, n: int) -> None:
        orb_r = INNER_R - 11

        # Soft drop shadow behind center orb
        shadow = QRadialGradient(QPointF(c.x(), c.y() + 2), orb_r + 6)
        shadow.setColorAt(0.70, QColor(0, 0, 0, 45))
        shadow.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setPen(Qt.NoPen)
        p.setBrush(shadow)
        p.drawEllipse(QPointF(c.x(), c.y() + 2), orb_r + 6, orb_r + 6)

        # Clean white orb button body
        p.setBrush(QColor(255, 255, 255, 252))
        p.setPen(QPen(QColor(228, 233, 240, 220), 1.5))
        p.drawEllipse(c, orb_r, orb_r)

        # Center typography
        if self._hover is not None:
            label = self._targets[self._hover]
            main_font = QFont("Segoe UI", 9.0, QFont.Bold)
            main_font.setLetterSpacing(QFont.AbsoluteSpacing, 0.6)
            p.setFont(main_font)
            p.setPen(QColor(18, 21, 26, 240))
            display_text = label if self._mode == "tools" else f".{label.upper()}"
            p.drawText(
                QRectF(c.x() - 52, c.y() - 14, 104, 28),
                Qt.AlignCenter,
                display_text,
            )
        elif n:
            count = len(self._paths)
            main_font = QFont("Segoe UI", 13, QFont.Bold)
            p.setFont(main_font)
            p.setPen(QColor(18, 21, 26, 240))
            p.drawText(
                QRectF(c.x() - 50, c.y() - 18, 100, 24),
                Qt.AlignCenter,
                str(count),
            )

            sub_font = QFont("Segoe UI", 7.5, QFont.DemiBold)
            sub_font.setLetterSpacing(QFont.AbsoluteSpacing, 0.8)
            p.setFont(sub_font)
            p.setPen(QColor(135, 145, 158, 230))
            mode_tag = "TOOLS" if self._mode == "tools" else ("FILE" if count == 1 else "FILES")
            p.drawText(
                QRectF(c.x() - 50, c.y() + 4, 100, 16),
                Qt.AlignCenter,
                mode_tag,
            )
        else:
            p.setFont(QFont("Segoe UI", 8.5, QFont.Medium))
            p.setPen(QColor(135, 145, 158, 230))
            p.drawText(
                QRectF(c.x() - 54, c.y() - 25, 108, 50),
                Qt.AlignCenter,
                self._message,
            )

    # ---------- painting ----------
    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        n = len(self._targets)
        c = self._c

        # Unscaled hit-test disc so Windows always registers drag events across the full area
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 0, 0, 3))
        p.drawEllipse(c, OUTER_R + 14, OUTER_R + 14)

        if not self._paths:  # armed but no file drag yet: draw nothing visible
            p.end()
            return

        # Apply spring pop-in scale & opacity transform around the center
        p.save()
        opacity = max(0.0, min(1.0, self._open_progress * 1.25))
        scale = _lerp(0.72, 1.0, self._open_progress)
        p.setOpacity(opacity)
        p.translate(c)
        p.scale(scale, scale)
        p.translate(-c)

        self._draw_ambient_backdrop(p, c)

        if n == 0:  # unsupported-file frosted glass ring
            ring = QPainterPath()
            ring.addEllipse(c, OUTER_R, OUTER_R)
            ring.addEllipse(c, INNER_R, INNER_R)

            grad = QLinearGradient(
                QPointF(c.x() - OUTER_R, c.y() - OUTER_R),
                QPointF(c.x() + OUTER_R, c.y() + OUTER_R),
            )
            grad.setColorAt(0.0, QColor(60, 40, 48, 180))
            grad.setColorAt(1.0, QColor(30, 22, 28, 195))
            p.fillPath(ring, grad)

            rim = QLinearGradient(
                QPointF(c.x() - OUTER_R, c.y() - OUTER_R),
                QPointF(c.x() + OUTER_R, c.y() + OUTER_R),
            )
            rim.setColorAt(0.0, QColor(255, 180, 180, 110))
            rim.setColorAt(1.0, QColor(255, 255, 255, 30))
            p.setPen(QPen(rim, 1.2))
            p.drawPath(ring)
        else:
            # Sort slices by hover progress so expanding slices always render on top
            order = sorted(
                range(n),
                key=lambda idx: self._hover_progress[idx]
                if idx < len(self._hover_progress)
                else 0.0,
            )
            for i in order:
                t = self._hover_progress[i] if i < len(self._hover_progress) else 0.0
                path = self._slice_path(i, n, hover_t=t)
                self._draw_crystal_slice(p, path, i, n, t=t)

        self._draw_center_orb(p, c, n)

        # Draw clean subtitle caption below the wheel (matches user's screenshot)
        if self._hover is not None and self._hover < len(self._targets):
            if self._mode == "tools" and self._hover < len(self._action_items):
                caption = self._action_items[self._hover].title
            else:
                target_str = self._targets[self._hover].upper()
                caption = f"Convert to {target_str}"

            p.setFont(QFont("Segoe UI", 9, QFont.Normal))
            p.setPen(QColor(130, 142, 156, 225))
            sub_rect = QRectF(c.x() - 130, c.y() + OUTER_R + 10, 260, 20)
            p.drawText(sub_rect, Qt.AlignCenter, caption)

        p.restore()