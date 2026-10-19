import getpass
from pathlib import Path

from PySide6.QtCore import QObject, QPoint, QTimer
from PySide6.QtGui import QAction, QCursor, QGuiApplication, QIcon
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from . import APP_NAME, config as cfgmod, registry
from .jobs import JobManager
from .overlay import WheelOverlay
from .settings_dialog import PAGES, SettingsDialog
from .trigger import DragTrigger
from .ui import icons, theme
from .ui.picker import ActionPicker
from .ui.toast import ToastManager
from .utils import IS_WIN, reveal_in_explorer, resource_path, set_custom_soffice
from .window import MainWindow

SERVER_NAME = f"{APP_NAME}-{getpass.getuser()}"


def make_icon() -> QIcon:
    ico = resource_path("assets/pomelo.ico")
    return QIcon(str(ico)) if ico.exists() else icons.logo_icon()


# --- Instancia única ---

def send_to_running_instance(paths) -> bool:
    sock = QLocalSocket()
    sock.connectToServer(SERVER_NAME)
    if not sock.waitForConnected(300):
        return False
    sock.write(("\n".join(str(p) for p in paths) or "\x00show").encode("utf-8"))
    sock.flush()
    sock.waitForBytesWritten(1000)
    sock.disconnectFromServer()
    return True


class PomeloApp(QObject):
    def __init__(self, qapp: QApplication, start_in_tray=False, files=None):
        super().__init__()
        self.qapp = qapp
        self.config = cfgmod.load()
        theme.apply(qapp, self.config.get("theme", "system"))
        self._watch_system_theme()
        set_custom_soffice(self.config.get("soffice_path", ""))
        self.ctx = registry.Context(self.config)
        registry.load_all()
        self.icon = make_icon()
        qapp.setWindowIcon(self.icon)
        self.toasts = ToastManager()
        self.settings = None
        self.picker = None

        self.jobs = JobManager(self.ctx, self)
        self.jobs.done.connect(self._on_done)

        self.window = MainWindow(self.icon, self.config)
        self.window.run_requested.connect(self.jobs.submit)
        self.window.settings_requested.connect(self.open_settings)
        self.window.picker_requested.connect(self.show_picker)
        self.jobs.started.connect(self.window.job_started)
        self.jobs.done.connect(self.window.job_finished)
        self.jobs.busy_changed.connect(self.window.set_busy)
        self.jobs.busy_changed.connect(self._on_busy)

        self.overlay = WheelOverlay(self.config)
        self.overlay.triggered.connect(self.jobs.submit)
        self.trigger = DragTrigger(self.config, self)
        self.trigger.activated.connect(self.overlay.popup)
        self.trigger.mode_changed.connect(self.overlay.set_mode)
        self.trigger.released.connect(lambda: QTimer.singleShot(400, self.overlay.dismiss))
        self.trigger.cancelled.connect(self.overlay.dismiss)

        self._build_tray()
        self._start_server()

        if files:
            QTimer.singleShot(200, lambda: self.handle_files(files))
        elif not start_in_tray:
            self.window.show()

    # --- Tema ---

    def _watch_system_theme(self):
        try:
            QGuiApplication.styleHints().colorSchemeChanged.connect(self._system_theme_changed)
        except AttributeError:
            pass

    def _system_theme_changed(self, *_):
        if self.config.get("theme", "system") == "system":
            self._reapply_theme()

    def _reapply_theme(self):
        theme.apply(self.qapp, self.config.get("theme", "system"))
        for w in (self.window, self.settings):
            if w is not None:
                theme.style_window(w)
                for child in w.findChildren(QObject):
                    if hasattr(child, "update"):
                        child.update()

    # --- Bandeja ---

    def _build_tray(self):
        self.tray = QSystemTrayIcon(self.icon, self)
        self.tray.setToolTip(APP_NAME)
        menu = theme.style_menu(QMenu())
        menu.addAction("Abrir Pomelo", self.window.bring_to_front)
        self.toggle_action = QAction("Rueda activada", menu, checkable=True)
        self.toggle_action.setChecked(self.config.get("wheel_enabled", True))
        self.toggle_action.setEnabled(IS_WIN)
        self.toggle_action.toggled.connect(self._toggle_wheel)
        menu.addAction(self.toggle_action)
        menu.addAction("Ajustes…", self.open_settings)
        menu.addSeparator()
        menu.addAction("Salir", self.qapp.quit)
        self.tray_menu = menu
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(
            lambda reason: self.window.bring_to_front()
            if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick)
            else None)
        self.tray.show()

    def _toggle_wheel(self, on):
        self.config["wheel_enabled"] = on
        cfgmod.save(self.config)

    def open_settings(self, page=""):
        page = page if isinstance(page, str) else ""
        if self.settings is None:
            self.settings = SettingsDialog(self.config, self.window if self.window.isVisible() else None, page)
            self.settings.changed.connect(self._settings_changed)
            self.settings.finished.connect(self._settings_closed)
        elif page:
            self.settings.nav.setCurrentRow([k for k, _, _ in PAGES].index(page))
        self.settings.show()
        self.settings.raise_()
        self.settings.activateWindow()

    def _settings_closed(self, *_):
        self.settings.deleteLater()
        self.settings = None

    def _settings_changed(self):
        self.toggle_action.setChecked(self.config.get("wheel_enabled", True))
        if theme.current_mode() != self.config.get("theme", "system"):
            self._reapply_theme()
        self.window.zone.hints.update()
        self.window.status.refresh_deps()

    # --- Selector y archivos recibidos ---

    def show_picker(self, files, global_pos: QPoint = None):
        self.window.status.refresh_deps()
        files = [Path(f) for f in files if Path(f).exists()]
        if not files:
            return
        if self.picker is not None:
            self.picker.close()
        self.picker = ActionPicker(files)
        self.picker.chosen.connect(self.jobs.submit)
        self.picker.destroyed.connect(lambda *_: setattr(self, "picker", None))
        self.picker.popup_at(global_pos or QCursor.pos())

    def _start_server(self):
        QLocalServer.removeServer(SERVER_NAME)
        self.server = QLocalServer(self)
        self.server.newConnection.connect(self._on_connection)
        self.server.listen(SERVER_NAME)

    def _on_connection(self):
        sock = self.server.nextPendingConnection()

        def read():
            data = bytes(sock.readAll()).decode("utf-8", "replace")
            paths = [Path(line) for line in data.splitlines() if line and line != "\x00show"]
            if paths:
                self.handle_files(paths)
            else:
                self.window.bring_to_front()
        sock.readyRead.connect(read)
        sock.disconnected.connect(sock.deleteLater)

    def handle_files(self, files):
        self.window.bring_to_front()
        QTimer.singleShot(120, lambda: self.show_picker(files, self.window.geometry().center()))

    # --- Resultados ---

    def _on_busy(self, n):
        self.tray.setToolTip(f"{APP_NAME} · procesando {n} tarea(s)…" if n else APP_NAME)

    def _on_done(self, _job_id, op, outputs, errors):
        if not self.config.get("notifications", True):
            return
        if errors:
            src, msg = errors[0]
            name = Path(src).name if src else op.label
            self.toasts.show("error", f"No se pudo completar «{op.label}»",
                             f"{name}: {msg.splitlines()[0] if msg else 'error desconocido'}")
        elif outputs and op.notify:
            last = outputs[-1]
            text = Path(outputs[0]).name if len(outputs) == 1 else f"{len(outputs)} archivos creados"
            self.toasts.show("success", f"{op.label} · listo", text, "Mostrar en la carpeta",
                             lambda p=last: reveal_in_explorer(p) if Path(p).exists() else None)
