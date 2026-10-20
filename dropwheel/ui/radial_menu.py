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
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QRadialGradient,
)
from PySide6.QtWidgets import QWidget

from dropwheel.converters import registry
from dropwheel.utils import is_left_mouse_down

log = logging.getLogger(__name__)

SIZE = 380
OUTER_R = 165
INNER_R = 82
HOVER_EXPAND = 8.0   # Maximum outward pixel expansion at full hover (t = 1.0)
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
    chosen = Signal(list, str)  # (list of Paths, target extension)

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
    def show_at_cursor(self) -> None:
        if self.isVisible() or self._locked:
            return  # key auto-repeat calls this many times; ignore repeats
        self._paths, self._targets, self._hover = [], [], None
        self._open_progress = 0.0
        self._init_slice_animations(0)
        self._message = "Drag a file\nonto the wheel"
        pos = QCursor.pos()
        self.move(pos.x() - SIZE // 2, pos.y() - SIZE // 2)
        self.show()
        self.raise_()
        log.info("overlay shown (armed) at (%d,%d)", pos.x(), pos.y())

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
        ccw_deg = math.degrees(math.atan2(-dy, dx)) % 360  # 0 = east, counter-clockwise
        clockwise_from_top = (90 - ccw_deg) % 360
        return int(clockwise_from_top // (360 / n))

    def _slice_path(self, i: int, n: int, hover_t: float = 0.0) -> QPainterPath:
        c = self._c
        r_out = OUTER_R + HOVER_EXPAND * hover_t
        r_in = INNER_R

        if n == 1:
            path = QPainterPath()
            path.addEllipse(c, r_out, r_out)
            path.addEllipse(c, r_in, r_in)
            return path

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
        self._targets = registry.common_targets(paths)
        self._init_slice_animations(len(self._targets))

        if not self._targets:
            self._message = "No conversions\nfor this file"
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
        log.info("drop on slice %s", idx)
        if idx is not None:
            event.setDropAction(Qt.CopyAction)  # copy, so Explorer never deletes the original
            event.accept()
            self.chosen.emit(self._paths, self._targets[idx])
        else:
            event.ignore()
        self.hide()

    # ---------- liquid crystal painting helpers ----------
    def _draw_ambient_backdrop(self, p: QPainter, c: QPointF) -> None:
        aura = QRadialGradient(c, OUTER_R + 22)
        aura.setColorAt(0.0, QColor(10, 15, 30, 0))
        aura.setColorAt(INNER_R / (OUTER_R + 22), QColor(8, 12, 24, 95))
        aura.setColorAt(0.85, QColor(8, 12, 24, 75))
        aura.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setPen(Qt.NoPen)
        p.setBrush(aura)
        p.drawEllipse(c, OUTER_R + 22, OUTER_R + 22)

    def _draw_crystal_slice(
        self, p: QPainter, path: QPainterPath, i: int, n: int, t: float
    ) -> None:
        c = self._c
        bounds = path.boundingRect()

        # 1. Soft drop shadow per wedge (deepens with hover progress t)
        p.save()
        p.translate(0, _lerp(2.5, 4.5, t))
        p.fillPath(path, QColor(0, 0, 0, int(_lerp(55, 90, t))))
        p.restore()

        # 2. Liquid Crystal Base Fill (smoothly blends slate glass -> electric cyan)
        base_grad = QLinearGradient(bounds.topLeft(), bounds.bottomRight())
        base_grad.setColorAt(
            0.0, _lerp_color(QColor(48, 56, 74, 195), QColor(56, 189, 248, 238), t)
        )
        base_grad.setColorAt(
            0.5, _lerp_color(QColor(28, 33, 46, 180), QColor(14, 165, 233, 222), t)
        )
        base_grad.setColorAt(
            1.0, _lerp_color(QColor(18, 22, 32, 205), QColor(37, 99, 235, 238), t)
        )
        p.fillPath(path, base_grad)

        # 3. Internal Liquid Caustic / Glass Sheen
        sheen = QLinearGradient(bounds.topLeft(), bounds.bottomLeft())
        sheen.setColorAt(
            0.0, _lerp_color(QColor(255, 255, 255, 50), QColor(255, 255, 255, 120), t)
        )
        sheen.setColorAt(
            0.4, _lerp_color(QColor(255, 255, 255, 8), QColor(255, 255, 255, 22), t)
        )
        sheen.setColorAt(
            1.0, _lerp_color(QColor(120, 180, 255, 18), QColor(186, 230, 253, 60), t)
        )
        p.fillPath(path, sheen)

        # 4. Specular Rim Border
        rim = QLinearGradient(
            QPointF(c.x() - OUTER_R, c.y() - OUTER_R),
            QPointF(c.x() + OUTER_R, c.y() + OUTER_R),
        )
        rim.setColorAt(
            0.0, _lerp_color(QColor(255, 255, 255, 130), QColor(255, 255, 255, 245), t)
        )
        rim.setColorAt(
            0.48, _lerp_color(QColor(255, 255, 255, 38), QColor(186, 230, 253, 180), t)
        )
        rim.setColorAt(
            1.0, _lerp_color(QColor(148, 163, 184, 65), QColor(56, 189, 248, 145), t)
        )

        p.setPen(QPen(rim, _lerp(1.2, 1.85, t)))
        p.setBrush(Qt.NoBrush)
        p.drawPath(path)

        # 5. Crisp Label with smooth radial & font scaling
        mid_rad = math.radians(90 - (i + 0.5) * 360 / n)
        r_text = (INNER_R + OUTER_R + HOVER_EXPAND * t) / 2
        tx = c.x() + r_text * math.cos(mid_rad)
        ty = c.y() - r_text * math.sin(mid_rad)
        text_rect = QRectF(tx - 44, ty - 14, 88, 28)

        font = QFont("Segoe UI")
        font.setPointSizeF(_lerp(10.0, 11.2, t))
        font.setWeight(QFont.Bold)
        font.setLetterSpacing(QFont.AbsoluteSpacing, 0.8)
        p.setFont(font)

        ext_label = self._targets[i].upper()
        p.setPen(QColor(0, 0, 0, 120))
        p.drawText(text_rect.translated(0, 1.5), Qt.AlignCenter, ext_label)

        p.setPen(QColor(255, 255, 255, int(_lerp(220, 255, t))))
        p.drawText(text_rect, Qt.AlignCenter, ext_label)

    def _draw_center_orb(self, p: QPainter, c: QPointF, n: int) -> None:
        orb_r = INNER_R - 11
        max_t = max(self._hover_progress, default=0.0)

        # Outer shadow around the center lens
        shadow = QRadialGradient(QPointF(c.x(), c.y() + 3), orb_r + 6)
        shadow.setColorAt(0.75, QColor(0, 0, 0, 110))
        shadow.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setPen(Qt.NoPen)
        p.setBrush(shadow)
        p.drawEllipse(QPointF(c.x(), c.y() + 3), orb_r + 6, orb_r + 6)

        # Deep frosted jewel body (smoothly tints toward azure when any slice is hovered)
        orb_grad = QRadialGradient(
            QPointF(c.x() - orb_r * 0.3, c.y() - orb_r * 0.3), orb_r * 1.35
        )
        orb_grad.setColorAt(
            0.0, _lerp_color(QColor(42, 48, 62, 225), QColor(35, 52, 78, 235), max_t)
        )
        orb_grad.setColorAt(
            0.62, _lerp_color(QColor(22, 26, 36, 230), QColor(20, 27, 42, 235), max_t)
        )
        orb_grad.setColorAt(
            1.0, _lerp_color(QColor(14, 17, 24, 240), QColor(12, 16, 26, 245), max_t)
        )

        p.setBrush(orb_grad)
        p.drawEllipse(c, orb_r, orb_r)

        # Top liquid lens reflection
        lens_rect = QRectF(
            c.x() - orb_r * 0.72,
            c.y() - orb_r * 0.86,
            orb_r * 1.44,
            orb_r * 0.95,
        )
        lens_grad = QLinearGradient(lens_rect.topLeft(), lens_rect.bottomLeft())
        lens_grad.setColorAt(0.0, QColor(255, 255, 255, 70))
        lens_grad.setColorAt(0.6, QColor(255, 255, 255, 10))
        lens_grad.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.setBrush(lens_grad)
        p.drawEllipse(lens_rect)

        # Specular rim around the center orb
        orb_rim = QLinearGradient(
            QPointF(c.x() - orb_r, c.y() - orb_r),
            QPointF(c.x() + orb_r, c.y() + orb_r),
        )
        orb_rim.setColorAt(
            0.0, _lerp_color(QColor(255, 255, 255, 140), QColor(125, 211, 252, 215), max_t)
        )
        orb_rim.setColorAt(0.5, QColor(255, 255, 255, 40))
        orb_rim.setColorAt(
            1.0, _lerp_color(QColor(148, 163, 184, 50), QColor(56, 189, 248, 125), max_t)
        )

        p.setPen(QPen(orb_rim, 1.3))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(c, orb_r, orb_r)

        # Center typography
        if self._hover is not None:
            sub_font = QFont("Segoe UI", 8, QFont.Medium)
            sub_font.setLetterSpacing(QFont.AbsoluteSpacing, 1.2)
            p.setFont(sub_font)
            p.setPen(QColor(148, 163, 184, 220))
            p.drawText(
                QRectF(c.x() - 55, c.y() - 24, 110, 18),
                Qt.AlignCenter,
                "CONVERT TO",
            )

            main_font = QFont("Segoe UI", 13, QFont.Bold)
            p.setFont(main_font)
            p.setPen(QColor(125, 211, 252))
            p.drawText(
                QRectF(c.x() - 55, c.y() - 6, 110, 30),
                Qt.AlignCenter,
                f".{self._targets[self._hover].upper()}",
            )
        elif n:
            count = len(self._paths)
            main_font = QFont("Segoe UI", 14, QFont.Bold)
            p.setFont(main_font)
            p.setPen(QColor(255, 255, 255, 240))
            p.drawText(
                QRectF(c.x() - 55, c.y() - 22, 110, 26),
                Qt.AlignCenter,
                str(count),
            )

            sub_font = QFont("Segoe UI", 8, QFont.Medium)
            sub_font.setLetterSpacing(QFont.AbsoluteSpacing, 0.8)
            p.setFont(sub_font)
            p.setPen(QColor(148, 163, 184, 210))
            p.drawText(
                QRectF(c.x() - 55, c.y() + 2, 110, 20),
                Qt.AlignCenter,
                "FILE" if count == 1 else "FILES",
            )
        else:
            p.setFont(QFont("Segoe UI", 9, QFont.Medium))
            p.setPen(QColor(226, 232, 240, 215))
            p.drawText(
                QRectF(c.x() - 58, c.y() - 30, 116, 60),
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
        p.restore()