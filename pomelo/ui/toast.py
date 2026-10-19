"""Notificaciones propias en la esquina inferior derecha."""
from PySide6.QtCore import QEasingCurve, QPoint, QPropertyAnimation, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QFontMetrics, QGuiApplication, QPainter, QPen
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from . import icons, theme
from .theme import T, c
from .widgets import IconButton

SHADOW = 16
WIDTH = 372
GAP = 10
MARGIN = 16


class Toast(QWidget):
    closed = Signal(object)

    def __init__(self, kind, title, body, action_label=None, action=None, timeout=5000):
        super().__init__(None, Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
                         | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.WindowDoesNotAcceptFocus
                         | Qt.WindowType.NoDropShadowWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.kind = kind
        self.action = action
        self.setFixedWidth(WIDTH + 2 * SHADOW)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(SHADOW + 14, SHADOW + 12, SHADOW + 8, SHADOW + 12)
        lay.setSpacing(12)
        badge = QWidget()
        badge.setFixedSize(32, 32)
        badge.paintEvent = lambda _e, w=badge: self._paint_badge(w)
        lay.addWidget(badge, 0, Qt.AlignmentFlag.AlignTop)

        col = QVBoxLayout()
        col.setSpacing(2)
        t = QLabel(title)
        t.setFont(theme.font(10, QFont.Weight.DemiBold))
        b = QLabel(QFontMetrics(theme.font(9)).elidedText(body, Qt.TextElideMode.ElideMiddle, WIDTH - 130))
        b.setProperty("role", "muted")
        b.setFont(theme.font(9))
        col.addWidget(t)
        col.addWidget(b)
        if action_label and action:
            btn = QPushButton(action_label)
            btn.setProperty("variant", "link")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(self._run_action)
            row = QHBoxLayout()
            row.setContentsMargins(0, 4, 0, 0)
            row.addWidget(btn)
            row.addStretch()
            col.addLayout(row)
        lay.addLayout(col, 1)
        close = IconButton("x", "Cerrar", 28, 14)
        close.clicked.connect(self.dismiss)
        lay.addWidget(close, 0, Qt.AlignmentFlag.AlignTop)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(timeout)
        self._timer.timeout.connect(self.dismiss)
        self._anims = []
        self._closing = False

    def _paint_badge(self, w):
        p = QPainter(w)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        col = c("success") if self.kind == "success" else c("danger")
        bg = QColor(col)
        bg.setAlpha(40)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(bg)
        p.drawEllipse(QRectF(0, 0, 32, 32))
        icons.draw(p, "check" if self.kind == "success" else "alert", QRectF(7, 7, 18, 18), col, 2.2)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        card = QRectF(self.rect()).adjusted(SHADOW, SHADOW, -SHADOW, -SHADOW)
        for i in range(SHADOW, 0, -2):
            a = int(T["shadow_alpha"] * (1 - i / SHADOW) ** 2 * 0.25)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(0, 0, 0, a))
            p.drawRoundedRect(card.adjusted(-i, -i + 5, i, i + 5), 16 + i, 16 + i)
        p.setPen(QPen(c("border_strong"), 1))
        p.setBrush(c("elevated"))
        p.drawRoundedRect(card, 14, 14)

    def _run_action(self):
        if self.action:
            self.action()
        self.dismiss()

    def enterEvent(self, _e):
        self._timer.stop()

    def leaveEvent(self, _e):
        if not self._closing:
            self._timer.start()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton and self.action:
            self._run_action()

    def _animate(self, prop, start, end, duration, curve, done=None):
        a = QPropertyAnimation(self, prop, self)
        a.setDuration(theme.ms(duration))
        a.setEasingCurve(curve)
        a.setStartValue(start)
        a.setEndValue(end)
        if done:
            a.finished.connect(done)
        a.start()
        self._anims.append(a)

    def present(self, target: QPoint):
        self.adjustSize()
        self.setWindowOpacity(0.0)
        self.move(target + QPoint(28, 0))
        self.show()
        self._animate(b"windowOpacity", 0.0, 1.0, 220, QEasingCurve.Type.OutCubic)
        self._animate(b"pos", target + QPoint(28, 0), target, 260, QEasingCurve.Type.OutQuint)
        self._timer.start()

    def slide_to(self, target: QPoint):
        self._animate(b"pos", self.pos(), target, 200, QEasingCurve.Type.OutCubic)

    def dismiss(self):
        if self._closing:
            return
        self._closing = True
        self._timer.stop()
        self._animate(b"windowOpacity", self.windowOpacity(), 0.0, 150, QEasingCurve.Type.OutCubic, self._finish)
        self._animate(b"pos", self.pos(), self.pos() + QPoint(16, 0), 150, QEasingCurve.Type.OutCubic)
        if not theme.ms(1):
            self._finish()

    def _finish(self):
        self.hide()
        self.closed.emit(self)
        self.deleteLater()


class ToastManager:
    MAX = 4

    def __init__(self):
        self.toasts = []

    def show(self, kind, title, body, action_label=None, action=None):
        toast = Toast(kind, title, body, action_label, action)
        toast.closed.connect(self._remove)
        self.toasts.insert(0, toast)
        while len(self.toasts) > self.MAX:
            self.toasts[-1].dismiss()
            self.toasts.pop()
        toast.adjustSize()
        positions = self._positions()
        toast.present(positions[0])
        for t, pos in zip(self.toasts[1:], positions[1:]):
            t.slide_to(pos)

    def _positions(self):
        geo = QGuiApplication.primaryScreen().availableGeometry()
        y = geo.bottom() - MARGIN + SHADOW
        out = []
        for t in self.toasts:
            y -= t.height() - 2 * SHADOW
            out.append(QPoint(geo.right() - MARGIN - t.width() + SHADOW, y - SHADOW))
            y -= GAP
        return out

    def _remove(self, toast):
        if toast in self.toasts:
            self.toasts.remove(toast)
            for t, pos in zip(self.toasts, self._positions()):
                t.slide_to(pos)
