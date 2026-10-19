"""Tokens de diseño, hoja de estilos y utilidades de ventana/animación."""
from string import Template

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QGuiApplication, QPalette

from ..utils import IS_WIN

# --- Tokens ---

DARK = dict(
    name="dark",
    bg="#0F1013", surface="#16181D", surface2="#1C1F25", elevated="#21242B",
    hover="#272A32", pressed="#2E323B", border="#262930", border_strong="#353943",
    text="#F3F4F6", text2="#AEB3BE", text3="#868C99",
    accent="#FF7A45", accent_hover="#FF8D5E", accent_press="#F06A35", accent_text="#FF8D5E",
    on_accent="#1B0D06", accent_soft="#33211A", focus="#FFB089",
    success="#3DD68C", danger="#FF6B6B", warning="#F7C548", shadow_alpha=150,
)
LIGHT = dict(
    name="light",
    bg="#F5F5F3", surface="#FFFFFF", surface2="#F2F2EF", elevated="#FFFFFF",
    hover="#EDEDE9", pressed="#E4E4DF", border="#E6E6E1", border_strong="#D3D3CD",
    text="#16171A", text2="#4F545E", text3="#6A707C",
    accent="#E85A26", accent_hover="#F06A38", accent_press="#D24C1B", accent_text="#C94A1C",
    on_accent="#1B0D06", accent_soft="#FCE7DD", focus="#E85A26",
    success="#13A866", danger="#D93B3B", warning="#B7860B", shadow_alpha=45,
)

GROUPS = {
    "image":   ("Imágenes", "image", "#FFA24C", "#C8640F"),
    "audio":   ("Audio", "music", "#B794FF", "#7B4FD6"),
    "video":   ("Vídeo", "video", "#FF7070", "#CC3B3B"),
    "doc":     ("Documentos", "doc", "#6AA7FF", "#2F6FD0"),
    "pdf":     ("PDF", "pdf", "#F7739A", "#C9356A"),
    "sheet":   ("Hojas de cálculo", "sheet", "#45D892", "#14935A"),
    "slides":  ("Presentaciones", "slides", "#F8CB4F", "#A97A00"),
    "archive": ("Comprimidos", "archive", "#D2A877", "#8C6232"),
    "action":  ("Acciones", "bolt", "#9DB0C6", "#566A80"),
    "file":    ("Archivo", "file", "#9DB0C6", "#566A80"),
    "folder":  ("Carpeta", "folder", "#9DB0C6", "#566A80"),
}

FONT_TEXT = ["Segoe UI Variable Text", "Segoe UI", "Inter", "Helvetica Neue", "Arial"]
FONT_DISPLAY = ["Segoe UI Variable Display", "Segoe UI", "Inter Display", "Inter", "Arial"]

T = dict(DARK)
_mode = "system"


def group_color(group: str, theme=None) -> QColor:
    meta = GROUPS.get(group, GROUPS["file"])
    t = theme or T
    return QColor(meta[2] if t["name"] == "dark" else meta[3])


def group_icon(group: str) -> str:
    return GROUPS.get(group, GROUPS["file"])[1]


def font(size: float, weight=QFont.Weight.Normal, display=False) -> QFont:
    f = QFont()
    f.setFamilies(FONT_DISPLAY if display else FONT_TEXT)
    f.setPointSizeF(size)
    f.setWeight(weight)
    if display and size >= 14:
        f.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 98)
    f.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
    return f


def c(key: str, alpha: int = None) -> QColor:
    col = QColor(T[key])
    if alpha is not None:
        col.setAlpha(alpha)
    return col


# --- Hoja de estilos ---

QSS = Template("""
* { color: $text; }
QDialog, QMainWindow, QWidget#Root { background: $bg; }
QToolTip { background: $elevated; color: $text; border: 1px solid $border_strong; border-radius: 6px; padding: 6px 8px; }

QPushButton { background: $surface2; border: 1px solid $border; border-radius: 10px; padding: 8px 16px;
              font-weight: 600; min-height: 18px; }
QPushButton:hover { background: $hover; border-color: $border_strong; }
QPushButton:pressed { background: $pressed; }
QPushButton:focus { border: 2px solid $focus; padding: 7px 15px; }
QPushButton:disabled { color: $text3; background: $surface2; border-color: $border; }
QPushButton[variant="primary"] { background: $accent; color: $on_accent; border: 1px solid $accent_press; }
QPushButton[variant="primary"]:hover { background: $accent_hover; }
QPushButton[variant="primary"]:pressed { background: $accent_press; }
QPushButton[variant="primary"]:focus { border: 2px solid $focus; }
QPushButton[variant="ghost"] { background: transparent; border: 1px solid transparent; color: $text2; padding: 6px 10px; }
QPushButton[variant="ghost"]:hover { background: $hover; color: $text; }
QPushButton[variant="link"] { background: transparent; border: none; color: $accent_text; padding: 4px 6px; }
QPushButton[variant="link"]:hover { text-decoration: underline; }

QLineEdit { background: $surface2; border: 1px solid $border; border-radius: 10px; padding: 8px 12px;
            selection-background-color: $accent; selection-color: $on_accent; }
QLineEdit:focus { border: 1px solid $accent; }
QLineEdit:read-only { color: $text2; }

QSlider { min-height: 22px; }
QSlider::groove:horizontal { height: 4px; background: $border_strong; border-radius: 2px; }
QSlider::sub-page:horizontal { background: $accent; border-radius: 2px; }
QSlider::handle:horizontal { background: $surface; border: 3px solid $accent; width: 12px; height: 12px;
                             margin: -7px 0; border-radius: 9px; }
QSlider::handle:horizontal:hover { background: $accent_soft; }

QScrollArea, QScrollArea > QWidget > QWidget { background: transparent; border: none; }
QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar::handle:vertical { background: $border_strong; border-radius: 3px; min-height: 32px; margin: 0 2px; }
QScrollBar::handle:vertical:hover { background: $text3; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }

QMenu { background: $elevated; border: 1px solid $border_strong; border-radius: 12px; padding: 6px; }
QMenu::item { padding: 8px 28px 8px 12px; border-radius: 7px; color: $text; }
QMenu::item:selected { background: $hover; }
QMenu::item:disabled { color: $text3; }
QMenu::separator { height: 1px; background: $border; margin: 6px 8px; }

QLabel { background: transparent; }
QLabel[role="muted"] { color: $text2; }
QLabel[role="caption"] { color: $text3; font-size: 9pt; }
QLabel[role="overline"] { color: $text3; font-size: 8.5pt; font-weight: 600; letter-spacing: 0.6px; }

QListWidget#Nav { background: transparent; border: none; outline: 0; }
QListWidget#Nav::item { padding: 9px 10px; border-radius: 8px; color: $text2; margin: 1px 0; }
QListWidget#Nav::item:hover { background: $hover; color: $text; }
QListWidget#Nav::item:selected { background: $accent_soft; color: $text; }

QFrame#Sidebar { background: $surface; border-right: 1px solid $border; }
QFrame[card="true"] { background: $surface; border: 1px solid $border; border-radius: 14px; }
QFrame[divider="true"] { background: $border; max-height: 1px; min-height: 1px; border: none; }
""")


# --- Aplicación del tema ---

def system_is_dark() -> bool:
    hints = QGuiApplication.styleHints()
    try:
        scheme = hints.colorScheme()
        if scheme == Qt.ColorScheme.Dark:
            return True
        if scheme == Qt.ColorScheme.Light:
            return False
    except AttributeError:
        pass
    return QGuiApplication.palette().window().color().lightness() < 128


def resolve(mode: str) -> dict:
    if mode == "light":
        return LIGHT
    if mode == "dark":
        return DARK
    return DARK if system_is_dark() else LIGHT


def apply(app, mode: str = "system"):
    global _mode
    _mode = mode
    T.clear()
    T.update(resolve(mode))
    app.setStyle("Fusion")
    pal = QPalette()
    for role, key in ((QPalette.ColorRole.Window, "bg"), (QPalette.ColorRole.Base, "surface2"),
                      (QPalette.ColorRole.AlternateBase, "surface"), (QPalette.ColorRole.Text, "text"),
                      (QPalette.ColorRole.WindowText, "text"), (QPalette.ColorRole.ButtonText, "text"),
                      (QPalette.ColorRole.Button, "surface2"), (QPalette.ColorRole.Highlight, "accent"),
                      (QPalette.ColorRole.HighlightedText, "on_accent"), (QPalette.ColorRole.ToolTipBase, "elevated"),
                      (QPalette.ColorRole.ToolTipText, "text"), (QPalette.ColorRole.PlaceholderText, "text3"),
                      (QPalette.ColorRole.Link, "accent_text")):
        pal.setColor(role, QColor(T[key]))
    pal.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(T["text3"]))
    pal.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, QColor(T["text3"]))
    app.setPalette(pal)
    app.setFont(font(10))
    app.setStyleSheet(QSS.substitute({k: v for k, v in T.items() if isinstance(v, str)}))
    for w in app.topLevelWidgets():
        if w.isWindow() and w.isVisible():
            style_window(w)
        w.update()


def current_mode() -> str:
    return _mode


# --- Ventanas (Windows 10/11) ---

def style_window(widget):
    """Barra de título oscura/clara y color de borde a juego (DWM)."""
    if not IS_WIN:
        return
    try:
        import ctypes
        hwnd = int(widget.winId())
        dwm = ctypes.windll.dwmapi
        dark = ctypes.c_int(1 if T["name"] == "dark" else 0)
        dwm.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(dark), 4)

        def colorref(hex_):
            q = QColor(hex_)
            return ctypes.c_int(q.red() | (q.green() << 8) | (q.blue() << 16))
        dwm.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(colorref(T["bg"])), 4)
        dwm.DwmSetWindowAttribute(hwnd, 34, ctypes.byref(colorref(T["border"])), 4)
        dwm.DwmSetWindowAttribute(hwnd, 36, ctypes.byref(colorref(T["text"])), 4)
    except Exception:
        pass


def style_menu(menu):
    menu.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
    menu.setWindowFlag(Qt.WindowType.NoDropShadowWindowHint, True)
    menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
    return menu


# --- Movimiento ---

def motion_enabled() -> bool:
    if not IS_WIN:
        return True
    try:
        import ctypes
        value = ctypes.c_int(1)
        ctypes.windll.user32.SystemParametersInfoW(0x1042, 0, ctypes.byref(value), 0)
        return bool(value.value)
    except Exception:
        return True


_MOTION = None


def ms(duration: int) -> int:
    global _MOTION
    if _MOTION is None:
        _MOTION = motion_enabled()
    return duration if _MOTION else 0
