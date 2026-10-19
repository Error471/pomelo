"""Controles propios: interruptor, control segmentado, botón de icono, indicador de carga y teselas."""
from PySide6.QtCore import (QEasingCurve, QPointF, QRectF, QSize, Qt, QTimer, QVariantAnimation, Signal)
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QAbstractButton, QSizePolicy, QWidget

from . import icons, theme
from .theme import T, c


def _anim(owner, duration, on_value, curve=QEasingCurve.Type.OutCubic):
    a = QVariantAnimation(owner)
    a.setDuration(theme.ms(duration))
    a.setEasingCurve(curve)
    a.valueChanged.connect(on_value)
    return a


# --- Interruptor ---

class Toggle(QAbstractButton):
    def __init__(self, checked=False, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setChecked(checked)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self.setFixedSize(44, 26)
        self._t = 1.0 if checked else 0.0
        self._a = _anim(self, 180, self._set_t)
        self.toggled.connect(self._animate)

    def _set_t(self, v):
        self._t = float(v)
        self.update()

    def _animate(self, on):
        self._a.stop()
        self._a.setStartValue(self._t)
        self._a.setEndValue(1.0 if on else 0.0)
        self._a.start()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(2, 3, 40, 20)
        off, on = c("border_strong"), c("accent")
        track = QColor(
            int(off.red() + (on.red() - off.red()) * self._t),
            int(off.green() + (on.green() - off.green()) * self._t),
            int(off.blue() + (on.blue() - off.blue()) * self._t))
        if not self.isEnabled():
            track.setAlpha(110)
        if self.hasFocus():
            p.setPen(QPen(c("focus"), 2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(r.adjusted(-2, -2, 2, 2), 12, 12)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(track)
        p.drawRoundedRect(r, 10, 10)
        knob_x = r.left() + 10 + (r.width() - 20) * self._t
        p.setBrush(QColor(0, 0, 0, 40))
        p.drawEllipse(QPointF(knob_x, r.center().y() + 1), 8, 8)
        p.setBrush(QColor("#FFFFFF"))
        p.drawEllipse(QPointF(knob_x, r.center().y()), 8, 8)

    def sizeHint(self):
        return QSize(44, 26)


# --- Control segmentado ---

class Segmented(QWidget):
    changed = Signal(object)

    def __init__(self, options, value=None, parent=None, min_item=64):
        super().__init__(parent)
        self.options = list(options)
        self.index = next((i for i, (v, _) in enumerate(self.options) if v == value), 0)
        self.min_item = min_item
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(34)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._font = theme.font(9.5, QFont.Weight.DemiBold)
        self._hover = -1
        self._pill = None
        self._a = _anim(self, 200, self._set_pill)
        self.setMouseTracking(True)
        self.setFixedWidth(self.sizeHint().width())

    def value(self):
        return self.options[self.index][0]

    def set_value(self, value, animate=True):
        for i, (v, _) in enumerate(self.options):
            if v == value:
                self._select(i, emit=False, animate=animate)

    def _item_w(self):
        from PySide6.QtGui import QFontMetrics
        fm = QFontMetrics(self._font)
        return max(self.min_item, max(fm.horizontalAdvance(lbl) for _, lbl in self.options) + 28)

    def sizeHint(self):
        return QSize(self._item_w() * len(self.options) + 8, 34)

    def _rect_for(self, i):
        w = self._item_w()
        return QRectF(4 + i * w, 4, w, 26)

    def _set_pill(self, r):
        self._pill = r
        self.update()

    def _select(self, i, emit=True, animate=True):
        if i == self.index and self._pill is not None:
            return
        start = self._pill or self._rect_for(self.index)
        self.index = i
        self._a.stop()
        if animate:
            self._a.setStartValue(start)
            self._a.setEndValue(self._rect_for(i))
            self._a.start()
        else:
            self._pill = self._rect_for(i)
        self.update()
        if emit:
            self.changed.emit(self.value())

    def mousePressEvent(self, e):
        i = int((e.position().x() - 4) // self._item_w())
        if 0 <= i < len(self.options):
            self._select(i)

    def mouseMoveEvent(self, e):
        i = int((e.position().x() - 4) // self._item_w())
        if i != self._hover:
            self._hover = i
            self.update()

    def leaveEvent(self, _e):
        self._hover = -1
        self.update()

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key.Key_Left, Qt.Key.Key_Up):
            self._select(max(0, self.index - 1))
        elif e.key() in (Qt.Key.Key_Right, Qt.Key.Key_Down):
            self._select(min(len(self.options) - 1, self.index + 1))
        else:
            super().keyPressEvent(e)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        outer = QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        p.setPen(QPen(c("focus") if self.hasFocus() else c("border"), 1.5 if self.hasFocus() else 1))
        p.setBrush(c("surface2"))
        p.drawRoundedRect(outer, 10, 10)
        pill = self._pill or self._rect_for(self.index)
        p.setPen(QPen(c("border_strong"), 1))
        p.setBrush(c("elevated") if T["name"] == "dark" else c("surface"))
        p.drawRoundedRect(pill, 7, 7)
        p.setFont(self._font)
        for i, (_, label) in enumerate(self.options):
            r = self._rect_for(i)
            if i != self.index and i == self._hover:
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(c("hover"))
                p.drawRoundedRect(r, 7, 7)
            p.setPen(c("text") if i == self.index else c("text2"))
            p.drawText(r, Qt.AlignmentFlag.AlignCenter, label)


# --- Botón de icono ---

class IconButton(QAbstractButton):
    def __init__(self, name, tooltip="", size=34, icon_size=18, parent=None):
        super().__init__(parent)
        self.name, self.icon_px = name, icon_size
        self.setToolTip(tooltip)
        self.setAccessibleName(tooltip)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self.setFixedSize(size, size)
        self._hover = False

    def enterEvent(self, _e):
        self._hover = True
        self.update()

    def leaveEvent(self, _e):
        self._hover = False
        self.update()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        if self.isDown():
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(c("pressed"))
            p.drawRoundedRect(r, 9, 9)
        elif self._hover:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(c("hover"))
            p.drawRoundedRect(r, 9, 9)
        if self.hasFocus():
            p.setPen(QPen(c("focus"), 2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(r, 9, 9)
        s = self.icon_px * (0.94 if self.isDown() else 1.0)
        ir = QRectF((self.width() - s) / 2, (self.height() - s) / 2, s, s)
        icons.draw(p, self.name, ir, c("text") if self._hover else c("text2"))


# --- Indicador de carga ---

class Spinner(QWidget):
    def __init__(self, size=18, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self._angle = 0
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)

    def showEvent(self, _e):
        self._timer.start()

    def hideEvent(self, _e):
        self._timer.stop()

    def _tick(self):
        self._angle = (self._angle + 7) % 360
        self.update()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(2, 2, -2, -2)
        p.setPen(QPen(c("border_strong"), 2))
        p.drawEllipse(r)
        p.setPen(QPen(c("accent"), 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawArc(r, int(-self._angle * 16), int(100 * 16))


# --- Tesela con icono de tipo de archivo ---

def paint_tile(p: QPainter, rect: QRectF, group: str, radius=10, icon_name=None):
    col = theme.group_color(group)
    bg = QColor(col)
    bg.setAlpha(38 if T["name"] == "dark" else 30)
    p.save()
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QPen(QColor(col.red(), col.green(), col.blue(), 60), 1))
    p.setBrush(bg)
    p.drawRoundedRect(rect, radius, radius)
    s = rect.width() * 0.52
    icons.draw(p, icon_name or theme.group_icon(group),
               QRectF(rect.center().x() - s / 2, rect.center().y() - s / 2, s, s), col, 1.9)
    p.restore()


class Logo(QWidget):
    def __init__(self, size=36, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)

    def paintEvent(self, _e):
        p = QPainter(self)
        icons.draw_logo(p, QRectF(self.rect()).adjusted(1, 1, -1, -1))


class Divider(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(1)

    def paintEvent(self, _e):
        QPainter(self).fillRect(self.rect(), c("border"))
