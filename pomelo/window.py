import time
from pathlib import Path

from PySide6.QtCore import QEasingCurve, QPoint, QPointF, QRectF, QSize, Qt, QTimer, QVariantAnimation, Signal
from PySide6.QtGui import QColor, QFont, QFontMetrics, QLinearGradient, QPainter, QPen, QRadialGradient
from PySide6.QtWidgets import (QFileDialog, QGraphicsOpacityEffect, QHBoxLayout, QLabel, QMainWindow,
                               QPushButton, QScrollArea, QVBoxLayout, QWidget)

from . import APP_NAME, kinds
from .ui import icons, theme
from .ui.theme import T, c
from .ui.widgets import IconButton, Logo, Spinner, paint_tile
from .utils import ffmpeg_exe, reveal_in_explorer, soffice_exe


# --- Zona de soltar ---

class DropBadge(QWidget):
    def __init__(self, zone):
        super().__init__(zone)
        self.zone = zone
        self.setFixedSize(76, 76)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        t = self.zone.t
        center = QPointF(38, 38)
        glow = QRadialGradient(center, 38)
        glow.setColorAt(0, c("accent", int(70 * t)))
        glow.setColorAt(1, c("accent", 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(glow)
        p.drawEllipse(center, 38, 38)
        r = 26 + 3 * t
        p.setBrush(c("accent_soft"))
        p.setPen(QPen(c("accent", int(60 + 120 * t)), 1))
        p.drawEllipse(center, r, r)
        s = 24 + 2 * t
        lift = -3 * t
        icons.draw(p, "upload", QRectF(38 - s / 2, 38 - s / 2 + lift, s, s), c("accent_text"), 2.0)


class KeyHints(QWidget):
    ITEMS = (("⇧", "Convertir"), ("Ctrl", "Herramientas"), ("Alt", "Acciones"))

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.setFixedHeight(28)
        self._kf = theme.font(8.5, QFont.Weight.DemiBold)
        self._lf = theme.font(9)

    def _items(self):
        names = {"shift": "⇧ Mayús", "ctrl": "Ctrl", "alt": "Alt"}
        keys = self.config.get("keys", {})
        return [(names.get(keys.get(m, ""), "?"), lbl) for m, lbl in
                zip(("convert", "tools", "actions"), ("Convertir", "Herramientas", "Acciones"))]

    def sizeHint(self):
        fk, fl = QFontMetrics(self._kf), QFontMetrics(self._lf)
        return QSize(sum(fk.horizontalAdvance(k) + 16 + 6 + fl.horizontalAdvance(l) + 18 for k, l in self._items()), 28)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        fk, fl = QFontMetrics(self._kf), QFontMetrics(self._lf)
        x = (self.width() - self.sizeHint().width() + 18) / 2
        for key, label in self._items():
            kw = fk.horizontalAdvance(key) + 16
            icons.draw_keycap(p, QRectF(x, 3, kw, 22), key, c("text"), c("surface2"), c("border_strong"), self._kf)
            x += kw + 6
            p.setFont(self._lf)
            p.setPen(c("text2"))
            lw = fl.horizontalAdvance(label)
            p.drawText(QRectF(x, 3, lw + 2, 22), Qt.AlignmentFlag.AlignVCenter, label)
            x += lw + 18


class DropZone(QWidget):
    files_dropped = Signal(list, QPoint)
    pick_requested = Signal()

    def __init__(self, config):
        super().__init__()
        self.setAcceptDrops(True)
        self.setMinimumHeight(290)
        self.t = 0.0
        self._a = QVariantAnimation(self)
        self._a.setDuration(theme.ms(180))
        self._a.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._a.valueChanged.connect(self._set_t)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 28, 24, 26)
        lay.setSpacing(0)
        lay.addStretch()
        self.badge = DropBadge(self)
        lay.addWidget(self.badge, 0, Qt.AlignmentFlag.AlignHCenter)
        lay.addSpacing(12)
        title = QLabel("Suelta aquí tus archivos")
        title.setFont(theme.font(15, QFont.Weight.DemiBold, display=True))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(title)
        lay.addSpacing(4)
        sub = QLabel("o arrástralos a cualquier sitio manteniendo una tecla")
        sub.setProperty("role", "muted")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(sub)
        lay.addSpacing(14)
        self.hints = KeyHints(config)
        lay.addWidget(self.hints, 0, Qt.AlignmentFlag.AlignHCenter)
        lay.addSpacing(20)
        btn = QPushButton("Elegir archivos")
        btn.setProperty("variant", "primary")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setMinimumWidth(168)
        btn.setFixedHeight(40)
        btn.clicked.connect(self.pick_requested)
        lay.addWidget(btn, 0, Qt.AlignmentFlag.AlignHCenter)
        lay.addStretch()

    def _set_t(self, v):
        self.t = float(v)
        self.update()
        self.badge.update()

    def _hover(self, on):
        self._a.stop()
        self._a.setStartValue(self.t)
        self._a.setEndValue(1.0 if on else 0.0)
        self._a.start()

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.setDropAction(Qt.DropAction.CopyAction)
            e.accept()
            self._hover(True)

    def dragMoveEvent(self, e):
        e.setDropAction(Qt.DropAction.CopyAction)
        e.accept()

    def dragLeaveEvent(self, _e):
        self._hover(False)

    def dropEvent(self, e):
        self._hover(False)
        files = [Path(u.toLocalFile()) for u in e.mimeData().urls() if u.isLocalFile()]
        if files:
            e.setDropAction(Qt.DropAction.CopyAction)
            e.accept()
            self.files_dropped.emit(files, self.mapToGlobal(e.position().toPoint()))

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        bg = QLinearGradient(r.topLeft(), r.bottomLeft())
        bg.setColorAt(0, c("surface"))
        bg.setColorAt(1, c("surface2") if T["name"] == "dark" else c("surface"))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(bg)
        p.drawRoundedRect(r, 20, 20)

        glow = QRadialGradient(QPointF(r.center().x(), r.top() + 60), r.width() * 0.55)
        glow.setColorAt(0, c("accent", int(16 + 34 * self.t)))
        glow.setColorAt(1, c("accent", 0))
        p.setBrush(glow)
        p.drawRoundedRect(r, 20, 20)

        if self.t > 0.01:
            p.setPen(QPen(c("accent", int(255 * self.t)), 1.5))
        else:
            pen = QPen(c("border_strong"), 1.3, Qt.PenStyle.CustomDashLine)
            pen.setDashPattern([4, 4])
            p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(r.adjusted(0.5, 0.5, -0.5, -0.5), 20, 20)


# --- Tira de formatos ---

class FormatStrip(QWidget):
    GROUPS = ("image", "audio", "video", "pdf", "doc", "sheet", "archive")
    SHORT = {"doc": "Texto", "sheet": "Hojas", "archive": "ZIP / 7Z"}

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(24)
        self._f = theme.font(9)

    def _labels(self):
        return [(g, self.SHORT.get(g, theme.GROUPS[g][0])) for g in self.GROUPS]

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setFont(self._f)
        fm = QFontMetrics(self._f)
        items = self._labels()
        total = sum(fm.horizontalAdvance(l) + 12 for _, l in items) + 14 * (len(items) - 1)
        x = (self.width() - total) / 2
        for g, label in items:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(theme.group_color(g))
            p.drawEllipse(QPointF(x + 3, 12), 3, 3)
            p.setPen(c("text3"))
            w = fm.horizontalAdvance(label)
            p.drawText(QRectF(x + 12, 0, w + 2, 24), Qt.AlignmentFlag.AlignVCenter, label)
            x += w + 12 + 14


# --- Actividad ---

def _ago(ts):
    s = int(time.time() - ts)
    if s < 45:
        return "ahora"
    if s < 3600:
        return f"hace {max(1, s // 60)} min"
    if s < 86400:
        return f"hace {s // 3600} h"
    return time.strftime("%d/%m %H:%M", time.localtime(ts))


class ActivityRow(QWidget):
    def __init__(self, op, files, parent=None):
        super().__init__(parent)
        self.op, self.files = op, [Path(f) for f in files]
        self.state = "running"
        self.outputs, self.errors = [], []
        self.ts = time.time()
        self.group = op.group if op.group != "action" else kinds.group_for_files(self.files)
        self.setFixedHeight(62)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._hover = False

        self.spinner = Spinner(18, self)
        self.open_btn = IconButton("external", "Mostrar en la carpeta", 32, 16, self)
        self.open_btn.clicked.connect(self.reveal)
        self.open_btn.hide()

    def finish(self, outputs, errors):
        self.outputs, self.errors = outputs, errors
        self.state = "done" if outputs or not errors else "error"
        self.ts = time.time()
        self.spinner.hide()
        self._layout_children()
        self.update()

    def resizeEvent(self, _e):
        self._layout_children()

    def _layout_children(self):
        self.spinner.move(self.width() - 34, (self.height() - 18) // 2)
        self.open_btn.move(self.width() - 42, (self.height() - 32) // 2)
        self.open_btn.setVisible(self._hover and self.state == "done" and bool(self.outputs))

    def enterEvent(self, _e):
        self._hover = True
        self._layout_children()
        self.update()

    def leaveEvent(self, _e):
        self._hover = False
        self._layout_children()
        self.update()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.reveal()

    def reveal(self):
        target = next((o for o in self.outputs if Path(o).exists()), None)
        if target:
            reveal_in_explorer(target)

    def _title(self):
        if self.outputs:
            first = Path(self.outputs[0]).name
            return first if len(self.outputs) == 1 else f"{first}  +{len(self.outputs) - 1}"
        return self.files[0].name if len(self.files) == 1 else f"{len(self.files)} elementos"

    def _subtitle(self):
        if self.state == "running":
            return f"{self.op.label} · procesando…"
        if self.state == "error":
            msg = self.errors[0][1].splitlines()[0] if self.errors and self.errors[0][1] else "Error"
            return msg
        verb = {"convert": "Convertido a"}.get(self.op.mode, "")
        return f"{verb + ' ' if verb else ''}{self.op.label} · {_ago(self.ts)}"

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(0, 2, 0, -2)
        if self._hover:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(c("hover"))
            p.drawRoundedRect(r, 12, 12)
        tile = QRectF(12, r.center().y() - 19, 38, 38)
        paint_tile(p, tile, self.group, 10)
        x = tile.right() + 14
        right_pad = 52
        avail = self.width() - x - right_pad
        p.setFont(theme.font(10, QFont.Weight.DemiBold))
        fm = QFontMetrics(p.font())
        p.setPen(c("text"))
        p.drawText(QRectF(x, r.top() + 10, avail, 20), Qt.AlignmentFlag.AlignVCenter,
                   fm.elidedText(self._title(), Qt.TextElideMode.ElideMiddle, int(avail)))
        p.setFont(theme.font(9))
        fm = QFontMetrics(p.font())
        p.setPen(c("danger") if self.state == "error" else c("text2"))
        p.drawText(QRectF(x, r.top() + 31, avail, 18), Qt.AlignmentFlag.AlignVCenter,
                   fm.elidedText(self._subtitle(), Qt.TextElideMode.ElideRight, int(avail)))
        if self.state != "running" and not self.open_btn.isVisible():
            col = c("success") if self.state == "done" else c("danger")
            bg = QColor(col)
            bg.setAlpha(36)
            cx = self.width() - 26
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(bg)
            p.drawEllipse(QPointF(cx, r.center().y()), 11, 11)
            icons.draw(p, "check" if self.state == "done" else "x", QRectF(cx - 7, r.center().y() - 7, 14, 14), col, 2.2)


class EmptyState(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(120)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        cx = self.width() / 2
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(c("surface2"))
        p.drawRoundedRect(QRectF(cx - 22, 14, 44, 44), 12, 12)
        icons.draw(p, "clock", QRectF(cx - 11, 25, 22, 22), c("text3"), 1.8)
        p.setFont(theme.font(10, QFont.Weight.DemiBold))
        p.setPen(c("text2"))
        p.drawText(QRectF(0, 66, self.width(), 20), Qt.AlignmentFlag.AlignHCenter, "Aún no hay actividad")
        p.setFont(theme.font(9))
        p.setPen(c("text3"))
        p.drawText(QRectF(0, 86, self.width(), 18), Qt.AlignmentFlag.AlignHCenter,
                   "Lo que conviertas aparecerá aquí")


# --- Barra inferior ---

class StatusBar(QWidget):
    components_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(40)
        self.busy = 0
        self._pulse = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(33)
        self._timer.timeout.connect(self._tick)
        self.deps = [("FFmpeg", ffmpeg_exe() is not None), ("LibreOffice", soffice_exe() is not None)]
        self.setCursor(Qt.CursorShape.ArrowCursor)

    def set_busy(self, n):
        self.busy = n
        if n and theme.ms(1):
            self._timer.start()
        else:
            self._timer.stop()
        self.update()

    def _tick(self):
        self._pulse = (self._pulse + 0.04) % 1.0
        self.update()

    def mouseReleaseEvent(self, e):
        if e.position().x() > self.width() / 2:
            self.components_clicked.emit()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(QRectF(0, 0, self.width(), 1), c("border"))
        cy = self.height() / 2 + 0.5
        col = c("accent") if self.busy else c("success")
        if self.busy:
            halo = QColor(col)
            halo.setAlpha(int(110 * (1 - self._pulse)))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(halo)
            p.drawEllipse(QPointF(26, cy), 4 + 6 * self._pulse, 4 + 6 * self._pulse)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(col)
        p.drawEllipse(QPointF(26, cy), 4, 4)
        p.setFont(theme.font(9))
        p.setPen(c("text2"))
        text = f"Procesando {self.busy} {'tarea' if self.busy == 1 else 'tareas'}…" if self.busy else "Listo"
        p.drawText(QRectF(38, 0, 200, self.height()), Qt.AlignmentFlag.AlignVCenter, text)

        fm = QFontMetrics(p.font())
        x = self.width() - 20
        for name, ok in reversed(self.deps):
            w = fm.horizontalAdvance(name)
            x -= w
            p.setPen(c("text3"))
            p.drawText(QRectF(x, 0, w + 2, self.height()), Qt.AlignmentFlag.AlignVCenter, name)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(c("success") if ok else c("text3"))
            p.drawEllipse(QPointF(x - 9, cy), 3, 3)
            x -= 30


# --- Ventana principal ---

class MainWindow(QMainWindow):
    run_requested = Signal(object, list)
    settings_requested = Signal(str)
    picker_requested = Signal(list, QPoint)

    def __init__(self, icon, config):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(icon)
        self.resize(560, 720)
        self.setMinimumSize(480, 600)
        self.rows = {}

        root = QWidget()
        root.setObjectName("Root")
        root.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        body = QVBoxLayout()
        body.setContentsMargins(24, 20, 24, 12)
        body.setSpacing(16)

        # Cabecera
        head = QHBoxLayout()
        head.setSpacing(12)
        head.addWidget(Logo(38))
        titles = QVBoxLayout()
        titles.setSpacing(0)
        name = QLabel(APP_NAME)
        name.setFont(theme.font(15, QFont.Weight.DemiBold, display=True))
        tag = QLabel("Conversor local · tus archivos no salen de este equipo")
        tag.setProperty("role", "caption")
        titles.addWidget(name)
        titles.addWidget(tag)
        head.addLayout(titles, 1)
        settings = IconButton("sliders", "Ajustes", 36, 18)
        settings.clicked.connect(lambda: self.settings_requested.emit(""))
        head.addWidget(settings)
        body.addLayout(head)

        # Zona de soltar
        self.zone = DropZone(config)
        self.zone.files_dropped.connect(self.picker_requested)
        self.zone.pick_requested.connect(self._pick_files)
        body.addWidget(self.zone, 5)
        body.addWidget(FormatStrip())

        # Actividad
        act_head = QHBoxLayout()
        lbl = QLabel("ACTIVIDAD")
        lbl.setProperty("role", "overline")
        act_head.addWidget(lbl)
        act_head.addStretch()
        self.clear_btn = QPushButton("Limpiar")
        self.clear_btn.setProperty("variant", "ghost")
        self.clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_btn.clicked.connect(self.clear_history)
        self.clear_btn.hide()
        act_head.addWidget(self.clear_btn)
        body.addLayout(act_head)

        self.list_host = QWidget()
        self.list_lay = QVBoxLayout(self.list_host)
        self.list_lay.setContentsMargins(0, 0, 4, 0)
        self.list_lay.setSpacing(0)
        self.empty = EmptyState()
        self.list_lay.addWidget(self.empty)
        self.list_lay.addStretch()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(self.list_host)
        body.addWidget(scroll, 4)

        outer.addLayout(body, 1)
        self.status = StatusBar()
        self.status.components_clicked.connect(lambda: self.settings_requested.emit("components"))
        outer.addWidget(self.status)
        self.setCentralWidget(root)

        self._refresh = QTimer(self)
        self._refresh.setInterval(30000)
        self._refresh.timeout.connect(lambda: [r.update() for r in self.rows.values()])
        self._refresh.start()

    def showEvent(self, e):
        super().showEvent(e)
        theme.style_window(self)
        self.centralWidget().setFocus()

    def _pick_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Elegir archivos")
        if files:
            self.picker_requested.emit([Path(f) for f in files],
                                       self.zone.mapToGlobal(self.zone.rect().center()))

    # --- Historial ---

    def job_started(self, job_id, op, files):
        row = ActivityRow(op, files)
        self.rows[job_id] = row
        self.empty.hide()
        self.clear_btn.show()
        self.list_lay.insertWidget(0, row)
        effect = QGraphicsOpacityEffect(row)
        row.setGraphicsEffect(effect)
        anim = QVariantAnimation(row)
        anim.setDuration(theme.ms(220))
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.valueChanged.connect(effect.setOpacity)
        anim.finished.connect(lambda: row.setGraphicsEffect(None))
        anim.start()

    def job_finished(self, job_id, op, outputs, errors):
        row = self.rows.get(job_id)
        if row is None:
            return
        if not outputs and not errors and op.mode == "actions":
            row.deleteLater()
            del self.rows[job_id]
            self._check_empty()
            return
        row.finish(outputs, errors)

    def clear_history(self):
        for jid, row in list(self.rows.items()):
            if row.state != "running":
                row.deleteLater()
                del self.rows[jid]
        self._check_empty()

    def _check_empty(self):
        has = bool(self.rows)
        self.empty.setVisible(not has)
        self.clear_btn.setVisible(has)

    def set_busy(self, n):
        self.status.set_busy(n)

    def bring_to_front(self):
        self.show()
        self.setWindowState(self.windowState() & ~Qt.WindowState.WindowMinimized)
        self.raise_()
        self.activateWindow()
