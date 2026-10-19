"""Detecta, de forma global, un arrastre con una tecla modificadora pulsada (solo Windows)."""
from PySide6.QtCore import QObject, QPoint, QTimer, Signal
from PySide6.QtGui import QCursor

from .utils import IS_WIN

VK = {"shift": 0x10, "ctrl": 0x11, "alt": 0x12}
VK_LBUTTON, VK_RBUTTON, VK_ESCAPE = 0x01, 0x02, 0x1B
DRAG_THRESHOLD = 12

if IS_WIN:
    import ctypes
    _user32 = ctypes.windll.user32

    def _pressed(vk: int) -> bool:
        return bool(_user32.GetAsyncKeyState(vk) & 0x8000)

    def _primary_button() -> int:
        return VK_RBUTTON if _user32.GetSystemMetrics(23) else VK_LBUTTON  # SM_SWAPBUTTON
else:
    def _pressed(vk: int) -> bool:
        return False

    def _primary_button() -> int:
        return VK_LBUTTON


class DragTrigger(QObject):
    activated = Signal(QPoint, str)
    mode_changed = Signal(str)
    released = Signal()
    cancelled = Signal()

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.enabled = IS_WIN
        self._down = False
        self._active = False
        self._mode = None
        self._start = QPoint()
        self._button = _primary_button()
        self._timer = QTimer(self)
        self._timer.setInterval(25)
        self._timer.timeout.connect(self._poll)
        if IS_WIN:
            self._timer.start()

    def _current_mode(self):
        keys = self.config.get("keys", {})
        for mode in ("convert", "tools", "actions"):
            vk = VK.get(keys.get(mode, ""))
            if vk and _pressed(vk):
                return mode
        return None

    def _poll(self):
        if not self.enabled or not self.config.get("wheel_enabled", True):
            if self._active:
                self._active = False
                self.cancelled.emit()
            return
        down = _pressed(self._button)
        pos = QCursor.pos()
        if down and not self._down:
            self._down, self._active, self._start = True, False, pos
        elif not down and self._down:
            self._down = False
            if self._active:
                self._active = False
                self.released.emit()
            return
        if not self._down:
            return
        mode = self._current_mode()
        if not self._active:
            if mode and (pos - self._start).manhattanLength() > DRAG_THRESHOLD:
                self._active, self._mode = True, mode
                self.activated.emit(pos, mode)
        else:
            if mode and mode != self._mode:
                self._mode = mode
                self.mode_changed.emit(mode)
            if _pressed(VK_ESCAPE):
                self._active = False
                self.cancelled.emit()
