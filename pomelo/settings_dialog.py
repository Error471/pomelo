from PySide6.QtCore import QRectF, QSize, Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QFont, QPainter
from PySide6.QtWidgets import (QDialog, QFileDialog, QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget,
                               QListWidgetItem, QMessageBox, QPushButton, QSlider, QStackedWidget, QVBoxLayout,
                               QWidget)

from . import __version__, config as cfgmod
from .ui import icons, theme
from .ui.theme import c
from .ui.widgets import Divider, Logo, Segmented, Toggle
from .utils import IS_WIN, ffmpeg_exe, has_module, soffice_exe

KEYS = [("shift", "⇧ Mayús"), ("ctrl", "Ctrl"), ("alt", "Alt")]
PAGES = [("general", "General", "sliders"), ("wheel", "Rueda", "wheel"), ("output", "Archivos", "folder"),
         ("components", "Componentes", "box"), ("about", "Acerca de", "info")]


# --- Piezas de página ---

class Row(QWidget):
    """Fila de ajuste: título + descripción a la izquierda, control a la derecha."""

    def __init__(self, title, description="", control=None, parent=None, below=None):
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(18, 14, 18, 14)
        outer.setSpacing(12)
        lay = QHBoxLayout()
        lay.setSpacing(16)
        outer.addLayout(lay)
        if below is not None:
            outer.addLayout(below)
        text = QVBoxLayout()
        text.setSpacing(2)
        t = QLabel(title)
        t.setFont(theme.font(10, QFont.Weight.DemiBold))
        text.addWidget(t)
        if description:
            d = QLabel(description)
            d.setProperty("role", "muted")
            d.setWordWrap(True)
            d.setFont(theme.font(9))
            text.addWidget(d)
        lay.addLayout(text, 1)
        if control is not None:
            if isinstance(control, QWidget):
                lay.addWidget(control, 0, Qt.AlignmentFlag.AlignVCenter)
            else:
                lay.addLayout(control)


class Section(QFrame):
    def __init__(self, rows, parent=None):
        super().__init__(parent)
        self.setProperty("card", True)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 2, 0, 2)
        lay.setSpacing(0)
        for i, row in enumerate(rows):
            if i:
                d = Divider()
                d.setContentsMargins(18, 0, 18, 0)
                wrap = QHBoxLayout()
                wrap.setContentsMargins(18, 0, 18, 0)
                wrap.addWidget(d)
                lay.addLayout(wrap)
            lay.addWidget(row)


class StatusPill(QWidget):
    def __init__(self, ok, parent=None):
        super().__init__(parent)
        self.ok = ok
        self.setFixedSize(QSize(104, 26))

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        col = c("success") if self.ok else c("text3")
        bg = c("success", 32) if self.ok else c("surface2")
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(bg)
        p.drawRoundedRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), 13, 13)
        icons.draw(p, "check" if self.ok else "x", QRectF(10, 6, 14, 14), col, 2.2)
        p.setPen(col)
        p.setFont(theme.font(9, QFont.Weight.DemiBold))
        p.drawText(QRectF(28, 0, 70, 26), Qt.AlignmentFlag.AlignVCenter, "Instalado" if self.ok else "No instalado")


def page(title, subtitle, *sections):
    w = QWidget()
    lay = QVBoxLayout(w)
    lay.setContentsMargins(32, 28, 32, 28)
    lay.setSpacing(14)
    t = QLabel(title)
    t.setFont(theme.font(17, QFont.Weight.DemiBold, display=True))
    lay.addWidget(t)
    if subtitle:
        s = QLabel(subtitle)
        s.setProperty("role", "muted")
        s.setWordWrap(True)
        lay.addWidget(s)
    lay.addSpacing(6)
    for sec in sections:
        if isinstance(sec, str):
            lbl = QLabel(sec.upper())
            lbl.setProperty("role", "overline")
            lay.addSpacing(6)
            lay.addWidget(lbl)
        else:
            lay.addWidget(sec)
    lay.addStretch()
    return w


# --- Diálogo ---

class SettingsDialog(QDialog):
    changed = Signal()

    def __init__(self, config, parent=None, start_page=""):
        super().__init__(parent)
        self.setWindowTitle("Ajustes · Pomelo")
        self.config = config
        self.resize(800, 580)
        self.setMinimumSize(720, 520)

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        side = QFrame()
        side.setObjectName("Sidebar")
        side.setFixedWidth(212)
        sl = QVBoxLayout(side)
        sl.setContentsMargins(14, 20, 14, 16)
        sl.setSpacing(14)
        brand = QHBoxLayout()
        brand.setSpacing(10)
        brand.addWidget(Logo(28))
        bt = QLabel("Ajustes")
        bt.setFont(theme.font(12, QFont.Weight.DemiBold, display=True))
        brand.addWidget(bt)
        brand.addStretch()
        sl.addLayout(brand)
        self.nav = QListWidget()
        self.nav.setObjectName("Nav")
        self.nav.setIconSize(QSize(18, 18))
        for key, label, icon_name in PAGES:
            item = QListWidgetItem(icons.icon(icon_name, theme.T["text2"], 18), label)
            item.setData(Qt.ItemDataRole.UserRole, key)
            item.setSizeHint(QSize(0, 38))
            self.nav.addItem(item)
        sl.addWidget(self.nav, 1)
        root.addWidget(side)

        self.stack = QStackedWidget()
        root.addWidget(self.stack, 1)
        builders = {"general": self._general, "wheel": self._wheel, "output": self._output,
                    "components": self._components, "about": self._about}
        for key, _, _ in PAGES:
            self.stack.addWidget(builders[key]())
        self.nav.currentRowChanged.connect(self.stack.setCurrentIndex)
        keys = [k for k, _, _ in PAGES]
        self.nav.setCurrentRow(keys.index(start_page) if start_page in keys else 0)

    def showEvent(self, e):
        super().showEvent(e)
        theme.style_window(self)

    def _save(self):
        cfgmod.save(self.config)
        self.changed.emit()

    def _set(self, key, value):
        self.config[key] = value
        self._save()

    # --- Páginas ---

    def _general(self):
        theme_seg = Segmented([("system", "Sistema"), ("light", "Claro"), ("dark", "Oscuro")],
                              self.config.get("theme", "system"))
        theme_seg.changed.connect(lambda v: self._set("theme", v))
        notify = Toggle(self.config.get("notifications", True))
        notify.toggled.connect(lambda v: self._set("notifications", v))
        auto = Toggle(self.config.get("autostart", False))
        auto.setEnabled(IS_WIN)
        auto.toggled.connect(self._autostart)
        send_btn = QPushButton("Añadir")
        send_btn.setEnabled(IS_WIN)
        send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        send_btn.clicked.connect(self._send_to)
        return page("General", "",
                    "Apariencia",
                    Section([Row("Tema", "Sigue el modo de Windows o fija uno.", theme_seg)]),
                    "Sistema",
                    Section([Row("Notificaciones", "Aviso discreto al terminar cada tarea.", notify),
                             Row("Iniciar con Windows", "Pomelo arranca en la bandeja al encender el equipo.", auto),
                             Row("Menú «Enviar a»", "Clic derecho en el Explorador → Enviar a → Pomelo.", send_btn)]))

    def _wheel(self):
        on = Toggle(self.config.get("wheel_enabled", True))
        on.setEnabled(IS_WIN)
        on.toggled.connect(lambda v: self._set("wheel_enabled", v))
        self.key_segs = {}
        rows = [Row("Rueda activada", "Mantén la tecla mientras arrastras un archivo y suéltalo sobre una opción.", on)]
        for mode, title, desc in (("convert", "Convertir", "Cambia el formato del archivo."),
                                  ("tools", "Herramientas", "Comprimir, reducir, rotar, unir PDF…"),
                                  ("actions", "Acciones", "Copiar ruta, mover, abrir terminal…")):
            seg = Segmented(KEYS, self.config["keys"].get(mode), min_item=74)
            seg.changed.connect(lambda v, m=mode: self._set_key(m, v))
            self.key_segs[mode] = seg
            rows.append(Row(title, desc, seg))
        return page("Rueda", "La rueda aparece bajo el cursor cuando arrastras archivos con una tecla pulsada. "
                             "Suelta en el centro o pulsa Esc para cancelar.",
                    Section(rows[:1]), "Teclas", Section(rows[1:]))

    def _set_key(self, mode, key):
        keys = self.config["keys"]
        other = next((m for m, k in keys.items() if k == key and m != mode), None)
        if other:
            keys[other] = keys[mode]
            self.key_segs[other].set_value(keys[other])
        keys[mode] = key
        self._save()

    def _output(self):
        self.out_dir = QLineEdit(self.config.get("output_dir", ""))
        self.out_dir.setPlaceholderText("Junto al archivo original")
        self.out_dir.setReadOnly(True)
        change =QPushButton("Cambiar…")
        change.setCursor(Qt.CursorShape.PointingHandCursor)
        change.clicked.connect(self._browse)
        reset = QPushButton("Restablecer")
        reset.setProperty("variant", "ghost")
        reset.setCursor(Qt.CursorShape.PointingHandCursor)
        reset.clicked.connect(lambda: (self.out_dir.setText(""), self._set("output_dir", "")))
        folder = QHBoxLayout()
        folder.setSpacing(8)
        folder.addWidget(self.out_dir)
        folder.addWidget(change)
        folder.addWidget(reset)

        quality = QSlider(Qt.Orientation.Horizontal)
        quality.setRange(40, 100)
        quality.setValue(int(self.config.get("image_quality", 90)))
        quality.setFixedWidth(180)
        q_label = QLabel(f"{quality.value()}")
        q_label.setFixedWidth(28)
        q_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        q_label.setFont(theme.font(10, QFont.Weight.DemiBold))
        quality.valueChanged.connect(lambda v: q_label.setText(str(v)))
        quality.sliderReleased.connect(lambda: self._set("image_quality", quality.value()))
        quality.valueChanged.connect(lambda v: None if quality.isSliderDown() else self._set("image_quality", v))
        q_box = QHBoxLayout()
        q_box.setSpacing(10)
        q_box.addWidget(quality)
        q_box.addWidget(q_label)

        dpi = Segmented([(96, "96"), (150, "150"), (300, "300")], int(self.config.get("pdf_dpi", 150)), min_item=56)
        dpi.changed.connect(lambda v: self._set("pdf_dpi", v))
        sep = Segmented([(";", "Punto y coma"), (",", "Coma")], self.config.get("csv_separator", ";"))
        sep.changed.connect(lambda v: self._set("csv_separator", v))

        return page("Archivos", "Los archivos nuevos nunca sobrescriben a los existentes.",
                    "Destino",
                    Section([Row("Carpeta de salida", "Si no eliges ninguna, se usa la del archivo original.",
                                 below=folder)]),
                    "Calidad",
                    Section([Row("Calidad de imagen", "JPG, WebP, AVIF y HEIC. Más alto = más peso.", q_box),
                             Row("PDF → imagen", "Resolución en puntos por pulgada.", dpi),
                             Row("Separador CSV", "Punto y coma abre directamente en Excel en español.", sep)]))

    def _components(self):
        lo_ok = soffice_exe() is not None
        get_lo = QPushButton("Descargar")
        get_lo.setProperty("variant", "primary")
        get_lo.setCursor(Qt.CursorShape.PointingHandCursor)
        get_lo.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://es.libreoffice.org/descarga/")))
        lo_ctrl = QHBoxLayout()
        lo_ctrl.setSpacing(10)
        if not lo_ok:
            lo_ctrl.addWidget(get_lo)
        lo_ctrl.addWidget(StatusPill(lo_ok))
        rows = [
            Row("FFmpeg", "Audio y vídeo. Incluido con Pomelo.", StatusPill(ffmpeg_exe() is not None)),
            Row("LibreOffice", "Word, Excel y PowerPoint. Gratuito; tras instalarlo, reinicia Pomelo.", lo_ctrl),
            Row("PyMuPDF", "Lectura y edición de PDF.", StatusPill(has_module("fitz") or has_module("pymupdf"))),
            Row("pillow-heif", "Fotos HEIC y AVIF del iPhone.", StatusPill(has_module("pillow_heif"))),
        ]
        return page("Componentes", "Pomelo usa estos motores para convertir. Todo funciona sin conexión.",
                    Section(rows))

    def _about(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(32, 48, 32, 28)
        lay.setSpacing(10)
        lay.addWidget(Logo(72), 0, Qt.AlignmentFlag.AlignHCenter)
        name = QLabel("Pomelo")
        name.setFont(theme.font(20, QFont.Weight.DemiBold, display=True))
        name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(name)
        ver = QLabel(f"Versión {__version__}")
        ver.setProperty("role", "muted")
        ver.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(ver)
        lay.addSpacing(8)
        txt = QLabel("Convierte imágenes, audio, vídeo, documentos y comprimidos\nsin subir nada a internet.")
        txt.setProperty("role", "muted")
        txt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(txt)
        cfg = QPushButton("Abrir carpeta de configuración")
        cfg.setProperty("variant", "link")
        cfg.setCursor(Qt.CursorShape.PointingHandCursor)
        cfg.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(cfgmod.config_dir()))))
        lay.addWidget(cfg, 0, Qt.AlignmentFlag.AlignHCenter)
        lay.addStretch()
        return w

    # --- Acciones ---

    def _browse(self):
        d = QFileDialog.getExistingDirectory(self, "Carpeta de salida")
        if d:
            self.out_dir.setText(d)
            self._set("output_dir", d)

    def _autostart(self, on):
        try:
            cfgmod.set_autostart(on)
        except OSError:
            pass
        self._set("autostart", on)

    def _send_to(self):
        try:
            lnk = cfgmod.install_send_to()
            QMessageBox.information(self, "Pomelo", f"Listo. Ya aparece en «Enviar a».\n{lnk}")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Pomelo", f"No se pudo crear el acceso:\n{exc}")
