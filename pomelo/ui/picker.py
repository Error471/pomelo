"""Selector emergente de operaciones (tras soltar archivos en la ventana o usar «Enviar a»)."""
from pathlib import Path

from PySide6.QtCore import QEasingCurve, QPoint, QPropertyAnimation, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QFontMetrics, QGuiApplication, QPainter, QPen
from PySide6.QtWidgets import QAbstractButton, QGridLayout, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from .. import kinds
from ..registry import MODE_LABELS, MODES, operations_for
from . import theme
from .theme import T, c
from .widgets import IconButton, Segmented, paint_tile

SHADOW = 18
COLS = 3

HINTS = {
    "jpg": "Fotos, ligero", "png": "Sin pérdida", "webp": "Web, muy ligero", "avif": "Muy comprimido",
    "heic": "Formato iPhone", "bmp": "Sin comprimir", "tiff": "Impresión", "gif": "Animación",
    "ico": "Icono de Windows", "pdf": "Documento", "mp3": "Compatible con todo", "m4a": "AAC, buena calidad",
    "wav": "Sin comprimir", "flac": "Sin pérdida", "ogg": "Formato abierto", "opus": "Voz y streaming",
    "aiff": "Sin comprimir", "wma": "Windows Media", "mp4": "Compatible con todo", "mov": "QuickTime",
    "mkv": "Contenedor flexible", "webm": "Web, VP9", "avi": "Clásico", "wmv": "Windows Media",
    "docx": "Word", "odt": "LibreOffice", "rtf": "Texto enriquecido", "txt": "Solo texto", "html": "Página web",
    "md": "Markdown", "xlsx": "Excel", "csv": "Valores separados", "tsv": "Separado por tabs",
    "ods": "LibreOffice Calc", "pptx": "PowerPoint", "odp": "Impress", "zip": "Universal", "7z": "Más compresión",
    "gz": "Linux y macOS", "extract": "En una carpeta", "srt": "Subtítulos", "vtt": "Subtítulos web",
    "img.compress": "Calidad 60", "img.half": "Mitad de tamaño", "img.rotate": "Sentido horario",
    "img.strip": "Sin EXIF ni GPS", "img.topdf": "Un PDF con todas", "pdf.merge": "En un solo PDF",
    "pdf.split": "Un PDF por página", "pdf.compress": "Menos peso", "pdf.rotate": "Todas las páginas",
    "video.compress": "H.264 hasta 1080p", "video.720": "H.264 720p", "video.mute": "Sin recodificar",
    "audio.normalize": "Volumen estándar", "audio.mono": "Un canal", "audio.compress": "MP3 128 kbps",
    "arch.packzip": "Archivo ZIP", "arch.pack7z": "Archivo 7Z", "act.copypath": "Al portapapeles",
    "act.copyto": "Elegir carpeta", "act.moveto": "Elegir carpeta", "act.reveal": "En el Explorador",
    "act.terminal": "PowerShell / Terminal", "act.rename": "Cambiar nombre",
}


def hint_for(op):
    return HINTS.get(op.id) or HINTS.get(op.id.rsplit(".", 1)[-1], "")


class OptionTile(QAbstractButton):
    def __init__(self, op, parent=None):
        super().__init__(parent)
        self.op = op
        self.missing = op.missing()
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor if not self.missing else Qt.CursorShape.ForbiddenCursor)
        self.setFixedHeight(56)
        self.setAccessibleName(op.label)
        if self.missing:
            self.setToolTip(f"Requiere {', '.join(self.missing)}")
        self._hover = False

    def enterEvent(self, _e):
        self._hover = True
        self.update()

    def leaveEvent(self, _e):
        self._hover = False
        self.update()

    def sizeHint(self):
        return QSize(128, 56)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        active = (self._hover or self.hasFocus()) and not self.missing
        col = theme.group_color(self.op.group)
        if active:
            bg = QColor(col)
            bg.setAlpha(34 if T["name"] == "dark" else 22)
            p.setBrush(bg)
            p.setPen(QPen(col, 1.5 if self.hasFocus() else 1))
        else:
            p.setBrush(c("surface2"))
            p.setPen(QPen(c("border"), 1))
        if self.isDown() and active:
            r = r.adjusted(1.5, 1.5, -1.5, -1.5)
        p.drawRoundedRect(r, 11, 11)

        tile = QRectF(r.left() + 10, r.center().y() - 15, 30, 30)
        if self.missing:
            p.setOpacity(0.45)
        paint_tile(p, tile, self.op.group, 8, "lock" if self.missing else None)
        p.setOpacity(1)
        tx = tile.right() + 10
        avail = r.right() - tx - 8
        p.setFont(theme.font(10, QFont.Weight.DemiBold))
        fm = QFontMetrics(p.font())
        p.setPen(c("text3") if self.missing else c("text"))
        if self.missing:
            p.drawText(QRectF(tx, r.top() + 9, avail, 20), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                       fm.elidedText(self.op.label, Qt.TextElideMode.ElideRight, int(avail)))
            p.setFont(theme.font(8.5))
            fm2 = QFontMetrics(p.font())
            p.drawText(QRectF(tx, r.top() + 27, avail, 18), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                       fm2.elidedText(f"Requiere {self.missing[0]}", Qt.TextElideMode.ElideRight, int(avail)))
        else:
            hint = hint_for(self.op)
            top = r.top() + 9 if hint else r.top() + 18
            p.drawText(QRectF(tx, top, avail, 20), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                       fm.elidedText(self.op.label, Qt.TextElideMode.ElideRight, int(avail)))
            if hint:
                p.setFont(theme.font(8.5))
                p.setPen(c("text2"))
                fm2 = QFontMetrics(p.font())
                p.drawText(QRectF(tx, r.top() + 27, avail, 18), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                           fm2.elidedText(hint, Qt.TextElideMode.ElideRight, int(avail)))


class ActionPicker(QWidget):
    chosen = Signal(object, list)

    def __init__(self, files, mode="convert", parent=None):
        super().__init__(parent, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint
                         | Qt.WindowType.NoDropShadowWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.files = [Path(f) for f in files]
        self.ops = {m: operations_for(m, self.files) for m in MODES}
        if not self.ops.get(mode):
            mode = next((m for m in MODES if self.ops[m]), mode)
        self.mode = mode
        self.tiles = []
        self.setFixedWidth(540 + 2 * SHADOW)

        root = QVBoxLayout(self)
        root.setContentsMargins(SHADOW + 16, SHADOW + 14, SHADOW + 16, SHADOW + 16)
        root.setSpacing(14)

        # Cabecera
        head = QHBoxLayout()
        head.setSpacing(12)
        self.group = kinds.group_for_files(self.files)
        badge = QWidget()
        badge.setFixedSize(40, 40)
        badge.paintEvent = lambda _e, w=badge: self._paint_badge(w)
        head.addWidget(badge)
        titles = QVBoxLayout()
        titles.setSpacing(1)
        name = self.files[0].name if len(self.files) == 1 else f"{len(self.files)} elementos"
        title = QLabel(QFontMetrics(theme.font(11, QFont.Weight.DemiBold)).elidedText(
            name, Qt.TextElideMode.ElideMiddle, 300))
        title.setFont(theme.font(11, QFont.Weight.DemiBold))
        sub = QLabel(self._subtitle())
        sub.setProperty("role", "caption")
        titles.addWidget(title)
        titles.addWidget(sub)
        head.addLayout(titles, 1)
        close = IconButton("x", "Cerrar (Esc)", 30, 16)
        close.clicked.connect(self.close)
        head.addWidget(close, 0, Qt.AlignmentFlag.AlignTop)
        root.addLayout(head)

        # Pestañas
        self.tabs = Segmented([(m, f"{MODE_LABELS[m]}  {len(self.ops[m])}") for m in MODES], self.mode, min_item=150)
        self.tabs.changed.connect(self._set_mode)
        root.addWidget(self.tabs, 0, Qt.AlignmentFlag.AlignLeft)

        # Rejilla
        self.grid_host = QWidget()
        self.grid = QGridLayout(self.grid_host)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setSpacing(8)
        root.addWidget(self.grid_host)

        hint = QLabel("Flechas para moverte · Intro para aplicar · Tab cambia de pestaña")
        hint.setProperty("role", "caption")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(hint)

        self._fill()
        self._anim = None

    # --- Contenido ---

    def _subtitle(self):
        try:
            desc = kinds.describe_files(self.files)
            return desc.split(" · ", 1)[1] if " · " in desc else theme.GROUPS[self.group][0]
        except OSError:
            return ""

    def _paint_badge(self, w):
        p = QPainter(w)
        paint_tile(p, QRectF(0, 0, 40, 40), self.group, 11)

    def _set_mode(self, mode):
        self.mode = mode
        self._fill()
        self.adjustSize()

    def _fill(self):
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.tiles = []
        ops = sorted(self.ops[self.mode], key=lambda o: bool(o.missing()))
        if not ops:
            empty = QLabel("No hay opciones de este tipo para estos archivos.")
            empty.setProperty("role", "muted")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setMinimumHeight(80)
            self.grid.addWidget(empty, 0, 0, 1, COLS)
            return
        for i, op in enumerate(ops):
            tile = OptionTile(op)
            tile.clicked.connect(lambda _=False, o=op: self._choose(o))
            self.grid.addWidget(tile, i // COLS, i % COLS)
            self.tiles.append(tile)
        for col in range(COLS):
            self.grid.setColumnStretch(col, 1)
        first = next((t for t in self.tiles if not t.missing), None)
        if first:
            first.setFocus(Qt.FocusReason.OtherFocusReason)

    def _choose(self, op):
        if op.missing():
            return
        files = list(self.files)
        self.close()
        self.chosen.emit(op, files)

    # --- Teclado ---

    def keyPressEvent(self, e):
        key = e.key()
        if key == Qt.Key.Key_Escape:
            self.close()
            return
        if key in (Qt.Key.Key_Tab, Qt.Key.Key_Backtab):
            idx = MODES.index(self.mode)
            idx = (idx + (-1 if key == Qt.Key.Key_Backtab else 1)) % len(MODES)
            self.tabs.set_value(MODES[idx])
            self._set_mode(MODES[idx])
            return
        if Qt.Key.Key_1 <= key <= Qt.Key.Key_3:
            m = MODES[key - Qt.Key.Key_1]
            self.tabs.set_value(m)
            self._set_mode(m)
            return
        focused = next((i for i, t in enumerate(self.tiles) if t.hasFocus()), None)
        if focused is not None:
            step = {Qt.Key.Key_Left: -1, Qt.Key.Key_Right: 1, Qt.Key.Key_Up: -COLS, Qt.Key.Key_Down: COLS}.get(key)
            if step:
                nxt = focused + step
                if 0 <= nxt < len(self.tiles):
                    self.tiles[nxt].setFocus(Qt.FocusReason.TabFocusReason)
                return
            if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
                self._choose(self.tiles[focused].op)
                return
        super().keyPressEvent(e)

    def focusNextPrevChild(self, _next):
        return False

    # --- Dibujo y aparición ---

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        card = QRectF(self.rect()).adjusted(SHADOW, SHADOW, -SHADOW, -SHADOW)
        base = T["shadow_alpha"]
        for i in range(SHADOW, 0, -2):
            a = int(base * (1 - i / SHADOW) ** 2 * 0.22)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(0, 0, 0, a))
            p.drawRoundedRect(card.adjusted(-i, -i + 6, i, i + 6), 18 + i, 18 + i)
        p.setPen(QPen(c("border_strong"), 1))
        p.setBrush(c("elevated"))
        p.drawRoundedRect(card, 16, 16)

    def popup_at(self, global_pos: QPoint):
        self.adjustSize()
        screen = QGuiApplication.screenAt(global_pos) or QGuiApplication.primaryScreen()
        geo = screen.availableGeometry()
        x = global_pos.x() - self.width() // 2
        y = global_pos.y() - SHADOW - 24
        x = max(geo.left(), min(x, geo.right() - self.width()))
        y = max(geo.top(), min(y, geo.bottom() - self.height()))
        target = QPoint(x, y)
        self.move(target + QPoint(0, 8))
        self.setWindowOpacity(0.0)
        self.show()
        self.activateWindow()
        group = []
        for prop, start, end in ((b"windowOpacity", 0.0, 1.0), (b"pos", target + QPoint(0, 8), target)):
            a = QPropertyAnimation(self, prop, self)
            a.setDuration(theme.ms(180))
            a.setEasingCurve(QEasingCurve.Type.OutCubic)
            a.setStartValue(start)
            a.setEndValue(end)
            a.start()
            group.append(a)
        self._anim = group
        if not theme.ms(1):
            self.setWindowOpacity(1.0)
            self.move(target)
