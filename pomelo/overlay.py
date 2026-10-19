"""Rueda flotante que aparece bajo el cursor mientras se arrastra un archivo."""
import math
from dataclasses import dataclass, field
from pathlib import Path

from PySide6.QtCore import QEasingCurve, QPoint, QPointF, QRect, QRectF, Qt, QTimer, QVariantAnimation, Signal
from PySide6.QtGui import (QColor, QFont, QFontMetrics, QGuiApplication, QPainter, QPainterPath, QPen,
                           QRadialGradient)
from PySide6.QtWidgets import QWidget

from . import kinds
from .registry import MODE_LABELS, operations_for
from .ui import icons, theme
from .ui.theme import DARK

SIZE = 820
R0, RING_W, GAP = 80, 84, 6
RING_CAPS = (8, 14, 20)
MODE_ICONS = {"convert": "convert", "tools": "wand", "actions": "bolt"}
KEY_NAMES = {"shift": "⇧", "ctrl": "Ctrl", "alt": "Alt"}

# La rueda siempre usa el material oscuro, sea cual sea el tema
W = dict(
    glass_in=QColor(30, 32, 39, 238), glass_out=QColor(17, 18, 23, 242), rim=QColor(255, 255, 255, 26),
    seg=QColor(255, 255, 255, 9), seg_line=QColor(255, 255, 255, 16), text=QColor("#F3F4F6"),
    text2=QColor("#AEB3BE"), text3=QColor("#868C99"), hub=QColor(38, 41, 49, 250),
)


@dataclass
class Segment:
    op: object
    inner: float
    outer: float
    start: float
    span: float
    hv: float = 0.0
    color: QColor = field(default_factory=QColor)


def layout(n: int) -> list:
    """Reparte n opciones en anillos concéntricos."""
    if n == 0:
        return []
    rings, total = 0, 0
    while total < n and rings < len(RING_CAPS):
        total += RING_CAPS[rings]
        rings += 1
    caps = RING_CAPS[:rings]
    counts = [max(1, round(n * c / sum(caps))) for c in caps]
    counts[-1] = n - sum(counts[:-1])
    while counts[-1] <= 0 and len(counts) > 1:
        counts.pop()
        counts[-1] = n - sum(counts[:-1])
    result = []
    for ring, count in enumerate(counts):
        inner = R0 + ring * (RING_W + GAP)
        span = 360 / count
        offset = 0 if ring % 2 == 0 else span / 2
        for k in range(count):
            result.append((inner, inner + RING_W, -90 - span / 2 + offset + k * span, span))
    return result


class WheelOverlay(QWidget):
    triggered = Signal(object, list)

    def __init__(self, config):
        super().__init__(None, Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
                         | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.WindowDoesNotAcceptFocus
                         | Qt.WindowType.NoDropShadowWindowHint)
        self.config = config
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAcceptDrops(True)
        self.mode = "convert"
        self.files: list = []
        self.group = "file"
        self.segments: list = []
        self.hover = None
        self.center = QPointF(SIZE / 2, SIZE / 2)
        self.appear = 0.0
        self.mode_fade = 1.0

        self._appear_anim = QVariantAnimation(self)
        self._appear_anim.setEasingCurve(QEasingCurve.Type.OutQuint)
        self._appear_anim.valueChanged.connect(self._set_appear)
        self._mode_anim = QVariantAnimation(self)
        self._mode_anim.setDuration(theme.ms(140))
        self._mode_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._mode_anim.valueChanged.connect(self._set_mode_fade)
        self._hover_timer = QTimer(self)
        self._hover_timer.setInterval(16)
        self._hover_timer.timeout.connect(self._step_hover)

        self.f_label = theme.font(10, QFont.Weight.DemiBold)
        self.f_title = theme.font(10.5, QFont.Weight.DemiBold)
        self.f_small = theme.font(8)
        self.f_key = theme.font(7.5, QFont.Weight.DemiBold)

    # --- Ciclo de vida ---

    def popup(self, global_pos: QPoint, mode: str):
        screen = QGuiApplication.screenAt(global_pos) or QGuiApplication.primaryScreen()
        geo = screen.geometry()
        rect = QRect(0, 0, SIZE, SIZE)
        rect.moveCenter(global_pos)
        rect.moveLeft(max(geo.left(), min(rect.left(), geo.right() - SIZE + 1)))
        rect.moveTop(max(geo.top(), min(rect.top(), geo.bottom() - SIZE + 1)))
        self.setGeometry(rect)
        self.center = QPointF(global_pos - rect.topLeft())
        self.mode, self.files, self.segments, self.hover = mode, [], [], None
        self.appear = 0.0
        self.show()
        self.raise_()
        self.update()

    def set_mode(self, mode: str):
        if mode == self.mode:
            return
        self.mode = mode
        self.hover = None
        self._rebuild()
        self._mode_anim.stop()
        self._mode_anim.setStartValue(0.0)
        self._mode_anim.setEndValue(1.0)
        self._mode_anim.start()
        self.update()

    def dismiss(self):
        self._appear_anim.stop()
        self._hover_timer.stop()
        self.hide()
        self.files, self.segments, self.hover = [], [], None

    def show_for_files(self, files, mode, global_pos, animate=False):
        """Abre la rueda para archivos ya conocidos (vista previa / pruebas)."""
        self.popup(global_pos, mode)
        self._set_files([Path(f) for f in files], animate)

    def _set_files(self, files, animate=True):
        self.files = files
        self.group = kinds.group_for_files(files)
        self._rebuild()
        if animate and theme.ms(1):
            self._appear_anim.stop()
            self._appear_anim.setDuration(theme.ms(200))
            self._appear_anim.setStartValue(self.appear)
            self._appear_anim.setEndValue(1.0)
            self._appear_anim.start()
        else:
            self.appear = 1.0
        self._hover_timer.start()

    def _rebuild(self):
        ops = operations_for(self.mode, self.files) if self.files else []
        self.segments = []
        for op, geom in zip(ops, layout(len(ops))):
            seg = Segment(op, *geom)
            seg.color = theme.group_color(op.group, DARK)
            self.segments.append(seg)

    def _set_appear(self, v):
        self.appear = float(v)
        self.update()

    def _set_mode_fade(self, v):
        self.mode_fade = float(v)
        self.update()

    def _step_hover(self):
        changed = False
        for i, s in enumerate(self.segments):
            target = 1.0 if i == self.hover else 0.0
            if abs(s.hv - target) > 0.002:
                s.hv += (target - s.hv) * (0.38 if theme.ms(1) else 1.0)
                changed = True
            elif s.hv != target:
                s.hv = target
                changed = True
        if changed:
            self.update()

    # --- Arrastrar y soltar ---

    @staticmethod
    def _local_files(mime):
        if not mime.hasUrls():
            return []
        return [Path(u.toLocalFile()) for u in mime.urls() if u.isLocalFile()]

    def dragEnterEvent(self, e):
        files = self._local_files(e.mimeData())
        if not files:
            e.ignore()
            return
        self._set_files(files)
        e.setDropAction(Qt.DropAction.CopyAction)
        e.accept()

    def dragMoveEvent(self, e):
        idx = self.hit(e.position())
        if idx != self.hover:
            self.hover = idx
            self.update()
        if idx is not None and self.segments[idx].op.available:
            e.setDropAction(Qt.DropAction.CopyAction)
            e.accept()
        else:
            e.ignore()

    def dragLeaveEvent(self, _e):
        self.hover = None
        self.update()

    def dropEvent(self, e):
        idx = self.hit(e.position())
        files = list(self.files)
        if idx is None or not self.segments[idx].op.available:
            e.ignore()
            self.dismiss()
            return
        op = self.segments[idx].op
        e.setDropAction(Qt.DropAction.CopyAction)
        e.accept()
        self.dismiss()
        QTimer.singleShot(0, lambda: self.triggered.emit(op, files))

    def hit(self, pos):
        dx, dy = pos.x() - self.center.x(), pos.y() - self.center.y()
        r = math.hypot(dx, dy)
        if r < R0:
            return None
        ang = math.degrees(math.atan2(dy, dx))
        for i, s in enumerate(self.segments):
            if s.inner - GAP / 2 <= r <= s.outer + GAP / 2 + (8 if s.outer == self._outer() else 0) \
                    and (ang - s.start) % 360 < s.span:
                return i
        return None

    def _outer(self):
        return max((s.outer for s in self.segments), default=R0 + 30)

    # --- Dibujo ---

    def _sector(self, s: Segment, grow=0.0, pad_px=3.0) -> QPainterPath:
        c = self.center
        inner, outer = s.inner, s.outer + grow
        path = QPainterPath()
        o_pad = math.degrees(pad_px / outer)
        i_pad = math.degrees(pad_px / inner)
        orect = QRectF(c.x() - outer, c.y() - outer, 2 * outer, 2 * outer)
        irect = QRectF(c.x() - inner, c.y() - inner, 2 * inner, 2 * inner)
        a = math.radians(s.start + o_pad)
        path.moveTo(c.x() + outer * math.cos(a), c.y() + outer * math.sin(a))
        path.arcTo(orect, -(s.start + o_pad), -(s.span - 2 * o_pad))
        path.arcTo(irect, -(s.start + s.span - i_pad), s.span - 2 * i_pad)
        path.closeSubpath()
        return path

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        p.fillRect(self.rect(), QColor(0, 0, 0, 1))
        if not self.files or self.appear <= 0.001:
            return
        c = self.center
        t = self.appear
        p.setOpacity(min(1.0, t * 1.4))
        scale = 0.9 + 0.1 * t
        p.translate(c)
        p.scale(scale, scale)
        p.translate(-c)

        outer = self._outer()
        disc = outer + 12

        # Sombra y material
        shadow = QRadialGradient(QPointF(c.x(), c.y() + 14), disc + 46)
        shadow.setColorAt(0.0, QColor(0, 0, 0, 130))
        shadow.setColorAt(disc / (disc + 46), QColor(0, 0, 0, 70))
        shadow.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(shadow)
        p.drawEllipse(QPointF(c.x(), c.y() + 14), disc + 46, disc + 46)

        glass = QRadialGradient(QPointF(c.x(), c.y() - disc * 0.35), disc * 1.25)
        glass.setColorAt(0, W["glass_in"])
        glass.setColorAt(1, W["glass_out"])
        p.setBrush(glass)
        p.setPen(QPen(W["rim"], 1))
        p.drawEllipse(c, disc, disc)

        # Segmentos
        p.save()
        p.setOpacity(p.opacity() * (0.35 + 0.65 * self.mode_fade))
        for s in self.segments:
            self._paint_segment(p, s, outer)
        p.restore()

        self._paint_hub(p, c)

    def _paint_segment(self, p, s: Segment, outer):
        c = self.center
        hv = s.hv
        avail = s.op.available
        col = QColor(s.color) if avail else QColor(90, 94, 104)
        is_outer = s.outer >= outer
        grow = 6 * hv if is_outer else 0

        path = self._sector(s, grow)
        base = QRadialGradient(c, s.outer + grow)
        base.setColorAt(s.inner / (s.outer + grow), QColor(255, 255, 255, 5))
        base.setColorAt(1.0, QColor(255, 255, 255, 14))
        p.setPen(QPen(W["seg_line"], 1))
        p.setBrush(base)
        p.drawPath(path)
        if hv > 0.01:
            a = int(235 * hv)
            fill = QRadialGradient(c, s.outer + grow)
            lo, hi = col.darker(112), col.lighter(112)
            lo.setAlpha(a)
            hi.setAlpha(a)
            fill.setColorAt(s.inner / (s.outer + grow), lo)
            fill.setColorAt(1.0, hi)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(fill)
            p.drawPath(path)

        # Filete de color en el borde exterior
        edge_r = s.outer + grow - 4
        pad = math.degrees(9 / edge_r)
        pen = QPen(col, 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        pen.setColor(QColor(col.red(), col.green(), col.blue(), int((150 if avail else 60) * (1 - hv))))
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        er = QRectF(c.x() - edge_r, c.y() - edge_r, 2 * edge_r, 2 * edge_r)
        p.drawArc(er, int(-(s.start + pad) * 16), int(-(s.span - 2 * pad) * 16))

        # Etiqueta
        mid = math.radians(s.start + s.span / 2)
        r = (s.inner + s.outer + grow) / 2
        chord = 2 * r * math.sin(math.radians(min(s.span, 179)) / 2)
        box_w = max(56, min(chord * 0.78, 100))
        box = QRectF(0, 0, box_w, 44)
        box.moveCenter(QPointF(c.x() + r * math.cos(mid), c.y() + r * math.sin(mid)))
        dark_text = QColor(18, 18, 22)
        light = W["text"] if avail else W["text3"]
        txt = QColor(
            int(light.red() + (dark_text.red() - light.red()) * hv),
            int(light.green() + (dark_text.green() - light.green()) * hv),
            int(light.blue() + (dark_text.blue() - light.blue()) * hv))
        p.setPen(txt)
        p.setFont(self.f_label)
        if not avail:
            icons.draw(p, "lock", QRectF(box.center().x() - 6, box.top() + 2, 12, 12), W["text3"], 1.8)
            box = box.adjusted(0, 10, 0, 0)
        p.drawText(box, Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, s.op.label)

    def _paint_hub(self, p, c):
        hub_r = R0 - 8
        p.setPen(QPen(QColor(255, 255, 255, 30), 1))
        hub = QRadialGradient(QPointF(c.x(), c.y() - hub_r * 0.6), hub_r * 1.6)
        hub.setColorAt(0, QColor(52, 55, 64, 252))
        hub.setColorAt(1, W["hub"])
        p.setBrush(hub)
        p.drawEllipse(c, hub_r, hub_r)

        hovered = self.segments[self.hover] if self.hover is not None and self.hover < len(self.segments) else None
        if hovered:
            col = hovered.color if hovered.op.available else W["text3"]
            title = hovered.op.label
            sub = "Suelta para aplicar" if hovered.op.available else f"Requiere {', '.join(hovered.op.missing())}"
            icon_name = theme.group_icon(hovered.op.group) if hovered.op.available else "lock"
        else:
            col = theme.group_color(self.group, DARK)
            title = MODE_LABELS.get(self.mode, "")
            n = len(self.files)
            sub = (self.files[0].name if n == 1 else f"{n} archivos") if self.segments else "Sin opciones"
            icon_name = MODE_ICONS.get(self.mode, "convert")

        icons.draw(p, icon_name, QRectF(c.x() - 10, c.y() - 40, 20, 20), col, 1.9)
        p.setPen(W["text"])
        p.setFont(self.f_title)
        fm = QFontMetrics(self.f_title)
        p.drawText(QRectF(c.x() - 64, c.y() - 18, 128, 20), Qt.AlignmentFlag.AlignCenter,
                   fm.elidedText(title, Qt.TextElideMode.ElideRight, 124))
        p.setPen(W["text2"])
        p.setFont(self.f_small)
        fm = QFontMetrics(self.f_small)
        p.drawText(QRectF(c.x() - 60, c.y() + 2, 120, 14), Qt.AlignmentFlag.AlignCenter,
                   fm.elidedText(sub, Qt.TextElideMode.ElideMiddle, 116))

        # Teclas de modo
        keys = self.config.get("keys", {})
        fm = QFontMetrics(self.f_key)
        labels = [(m, KEY_NAMES.get(keys.get(m, ""), "?")) for m in ("convert", "tools", "actions")]
        widths = [max(20, fm.horizontalAdvance(k) + 10) for _, k in labels]
        x = c.x() - (sum(widths) + 4 * (len(widths) - 1)) / 2
        for (m, k), w in zip(labels, widths):
            r = QRectF(x, c.y() + 24, w, 17)
            active = m == self.mode
            p.setPen(QPen(QColor(255, 255, 255, 60 if active else 22), 1))
            p.setBrush(QColor(255, 122, 69, 230) if active else QColor(255, 255, 255, 10))
            p.drawRoundedRect(r, 4, 4)
            p.setPen(QColor(27, 13, 6) if active else W["text3"])
            p.setFont(self.f_key)
            p.drawText(r, Qt.AlignmentFlag.AlignCenter, k)
            x += w + 4
