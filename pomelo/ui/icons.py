"""Iconos vectoriales dibujados con QPainter (rejilla de 24 unidades, trazo redondeado) y logotipo."""
import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QBrush, QColor, QFont, QIcon, QPainter, QPainterPath, QPen, QPixmap,
                           QRadialGradient, QLinearGradient)


def _poly(path, *pts, close=False):
    path.moveTo(*pts[0])
    for p in pts[1:]:
        path.lineTo(*p)
    if close:
        path.closeSubpath()


def _circle(path, cx, cy, r):
    path.addEllipse(QPointF(cx, cy), r, r)


def _page(path):
    _poly(path, (6, 3), (14, 3), (19, 8), (19, 21), (6, 21), close=True)
    _poly(path, (14, 3), (14, 8), (19, 8))


def _build(name: str):
    """Devuelve (trazo, relleno) en coordenadas 24×24."""
    s, f = QPainterPath(), QPainterPath()
    if name == "upload":
        _poly(s, (12, 15), (12, 4)); _poly(s, (7, 9), (12, 4), (17, 9)); _poly(s, (4, 14), (4, 19.5), (20, 19.5), (20, 14))
    elif name == "sliders":
        _poly(s, (4, 7), (6.5, 7)); _circle(s, 9, 7, 2.5); _poly(s, (11.5, 7), (20, 7))
        _poly(s, (4, 17), (12.5, 17)); _circle(s, 15, 17, 2.5); _poly(s, (17.5, 17), (20, 17))
    elif name == "folder":
        _poly(s, (3, 18.5), (3, 6), (9, 6), (11, 8.5), (21, 8.5), (21, 18.5), close=True)
    elif name == "external":
        _poly(s, (14, 4), (20, 4), (20, 10)); _poly(s, (20, 4), (11, 13))
        _poly(s, (18, 14), (18, 20), (4, 20), (4, 6), (10, 6))
    elif name == "check":
        _poly(s, (5, 12.5), (10, 17), (19, 7))
    elif name == "x":
        _poly(s, (6.5, 6.5), (17.5, 17.5)); _poly(s, (17.5, 6.5), (6.5, 17.5))
    elif name == "alert":
        _circle(s, 12, 12, 9); _poly(s, (12, 7.5), (12, 12.8)); _circle(f, 12, 16.3, 1.15)
    elif name == "image":
        s.addRoundedRect(QRectF(3, 4, 18, 16), 3, 3); _circle(s, 9, 9.5, 1.8)
        _poly(s, (3.5, 17), (9, 12), (13, 15.5), (16, 13), (20.5, 17))
    elif name == "music":
        _circle(s, 8.4, 17.6, 2.6); _poly(s, (11, 17.6), (11, 5.2), (19, 3.6), (19, 15.6)); _circle(s, 16.4, 15.6, 2.6)
    elif name == "video":
        s.addRoundedRect(QRectF(2.5, 6, 13, 12), 3, 3); _poly(s, (15.5, 10.2), (21.5, 7), (21.5, 17), (15.5, 13.8), close=True)
    elif name == "doc":
        _page(s); _poly(s, (9, 13), (16, 13)); _poly(s, (9, 17), (14, 17))
    elif name == "pdf":
        _page(s); f.addRoundedRect(QRectF(3, 12.5, 12.5, 6.5), 1.6, 1.6)
    elif name == "sheet":
        s.addRoundedRect(QRectF(3.5, 4, 17, 16), 2.5, 2.5)
        _poly(s, (3.5, 9.5), (20.5, 9.5)); _poly(s, (3.5, 15), (20.5, 15)); _poly(s, (9.5, 9.5), (9.5, 20))
    elif name == "slides":
        s.addRoundedRect(QRectF(3, 4, 18, 12), 2, 2); _poly(s, (12, 16), (12, 20)); _poly(s, (8, 20), (16, 20))
        _poly(s, (10.5, 8), (14, 10), (10.5, 12), close=True)
    elif name == "archive":
        s.addRoundedRect(QRectF(3.5, 4, 17, 5), 1.5, 1.5); _poly(s, (5, 9), (5, 20), (19, 20), (19, 9))
        _poly(s, (10, 13), (14, 13))
    elif name == "bolt":
        _poly(s, (13, 2.5), (5, 13.5), (11.5, 13.5), (10.5, 21.5), (19, 10), (12.5, 10), close=True)
    elif name == "convert":
        _poly(s, (4, 8.5), (18, 8.5)); _poly(s, (14.5, 5), (18, 8.5), (14.5, 12))
        _poly(s, (20, 15.5), (6, 15.5)); _poly(s, (9.5, 12), (6, 15.5), (9.5, 19))
    elif name == "wand":
        _poly(s, (4, 20), (14, 10))
        for cx, cy in ((17.5, 5), (19.5, 11.5), (11.5, 4.5)):
            _poly(s, (cx, cy - 2), (cx, cy + 2)); _poly(s, (cx - 2, cy), (cx + 2, cy))
    elif name == "file":
        _page(s)
    elif name == "lock":
        s.addRoundedRect(QRectF(6, 11, 12, 9), 2, 2)
        s.moveTo(8.5, 11); s.lineTo(8.5, 8); s.arcTo(QRectF(8.5, 4.5, 7, 7), 180, -180); s.lineTo(15.5, 11)
    elif name == "trash":
        _poly(s, (4, 7), (20, 7)); _poly(s, (9, 7), (9, 4.5), (15, 4.5), (15, 7)); _poly(s, (6, 7), (7, 20), (17, 20), (18, 7))
    elif name == "clock":
        _circle(s, 12, 12, 9); _poly(s, (12, 7), (12, 12), (15.5, 14))
    elif name == "shield":
        s.moveTo(12, 3); s.lineTo(19, 6); s.lineTo(19, 11.5); s.quadTo(19, 18, 12, 21); s.quadTo(5, 18, 5, 11.5)
        s.lineTo(5, 6); s.closeSubpath(); _poly(s, (9, 12), (11.3, 14.3), (15.2, 10.2))
    elif name == "chevron":
        _poly(s, (9, 6), (15, 12), (9, 18))
    elif name == "palette":
        _circle(s, 12, 12, 9); _circle(f, 8, 10, 1.3); _circle(f, 12, 7.5, 1.3); _circle(f, 16, 10, 1.3); _circle(f, 15, 15, 1.3)
    elif name == "box":
        _poly(s, (12, 3), (20, 7.5), (20, 16.5), (12, 21), (4, 16.5), (4, 7.5), close=True)
        _poly(s, (4, 7.5), (12, 12), (20, 7.5)); _poly(s, (12, 12), (12, 21))
    elif name == "info":
        _circle(s, 12, 12, 9); _poly(s, (12, 11), (12, 16.5)); _circle(f, 12, 7.7, 1.15)
    elif name == "wheel":
        _circle(s, 12, 12, 9); _circle(s, 12, 12, 3.5)
        for k in range(6):
            a = math.radians(k * 60 - 90)
            _poly(s, (12 + 3.5 * math.cos(a), 12 + 3.5 * math.sin(a)), (12 + 9 * math.cos(a), 12 + 9 * math.sin(a)))
    return s, f


_CACHE = {}


def draw(p: QPainter, name: str, rect: QRectF, color: QColor, stroke: float = 1.8):
    key = name
    if key not in _CACHE:
        _CACHE[key] = _build(name)
    s, f = _CACHE[key]
    p.save()
    p.translate(rect.x(), rect.y())
    p.scale(rect.width() / 24.0, rect.height() / 24.0)
    pen = QPen(color, stroke, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawPath(s)
    if not f.isEmpty():
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)
        p.drawPath(f)
        if name == "pdf":
            p.setPen(QPen(QColor(0, 0, 0, 0)))
    p.restore()


def icon(name: str, color, size: int = 20, stroke: float = 1.8) -> QIcon:
    pm = QPixmap(size * 2, size * 2)
    pm.setDevicePixelRatio(2.0)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    draw(p, name, QRectF(0, 0, size, size), QColor(color), stroke)
    p.end()
    return QIcon(pm)


# --- Logotipo: rodaja de pomelo ---

def draw_logo(p: QPainter, rect: QRectF, segments: int = 8):
    p.save()
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    c = rect.center()
    r = min(rect.width(), rect.height()) / 2

    rind = QLinearGradient(rect.topLeft(), rect.bottomRight())
    rind.setColorAt(0, QColor("#FFB45E"))
    rind.setColorAt(1, QColor("#FF5E3A"))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(rind))
    p.drawEllipse(c, r, r)

    p.setBrush(QColor("#FFF1E6"))
    p.drawEllipse(c, r * 0.86, r * 0.86)

    flesh = QRadialGradient(c, r * 0.8)
    flesh.setColorAt(0, QColor("#FFB49A"))
    flesh.setColorAt(1, QColor("#FF7A62"))
    inner, outer = r * 0.09, r * 0.79
    span = 360 / segments
    gap = 0.032 * r
    for k in range(segments):
        a0 = math.radians(-90 + k * span)
        a1 = math.radians(-90 + (k + 1) * span)
        mid = (a0 + a1) / 2
        off = QPointF(math.cos(mid) * gap * 0.55, math.sin(mid) * gap * 0.55)
        path = QPainterPath()
        path.moveTo(c + off + QPointF(inner * math.cos(mid), inner * math.sin(mid)))
        orect = QRectF(c.x() - outer, c.y() - outer, 2 * outer, 2 * outer).translated(off)
        sweep = span - math.degrees(gap / outer) * 2
        start = -math.degrees(a0) - math.degrees(gap / outer)
        path.arcTo(orect, start, -sweep)
        path.closeSubpath()
        p.setBrush(QBrush(flesh))
        p.drawPath(path)

    p.setBrush(QColor(255, 255, 255, 70))
    p.drawEllipse(QPointF(c.x() - r * 0.32, c.y() - r * 0.36), r * 0.16, r * 0.1)
    p.restore()


def logo_pixmap(size: int) -> QPixmap:
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    m = size * 0.04
    draw_logo(p, QRectF(m, m, size - 2 * m, size - 2 * m))
    p.end()
    return pm


def logo_icon() -> QIcon:
    ic = QIcon()
    for s in (16, 20, 24, 32, 40, 48, 64, 128, 256):
        ic.addPixmap(logo_pixmap(s))
    return ic


def draw_keycap(p: QPainter, rect: QRectF, text: str, fg: QColor, bg: QColor, border: QColor, fnt: QFont):
    p.save()
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QPen(border, 1))
    p.setBrush(bg)
    p.drawRoundedRect(rect, 6, 6)
    p.setPen(QPen(border.darker(115), 1))
    p.drawLine(QPointF(rect.left() + 5, rect.bottom() - 0.5), QPointF(rect.right() - 5, rect.bottom() - 0.5))
    p.setPen(fg)
    p.setFont(fnt)
    p.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)
    p.restore()
