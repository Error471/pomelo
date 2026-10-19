import io

from PIL import Image, ImageOps, features

from ..registry import register
from ..utils import all_ext, ext, stem, unique_path

try:
    import pillow_heif
    pillow_heif.register_heif_opener()
    HAS_HEIF = True
except Exception:
    HAS_HEIF = False


def _avif_supported() -> bool:
    try:
        if features.check("avif"):
            return True
    except Exception:
        pass
    try:
        pillow_heif.register_avif_opener()
        return True
    except Exception:
        return False


HAS_AVIF = _avif_supported()

RASTER_IN = {"jpg", "jpeg", "jfif", "png", "webp", "bmp", "tif", "tiff", "gif", "ico"}
if HAS_HEIF:
    RASTER_IN |= {"heic", "heif"}
if HAS_AVIF:
    RASTER_IN.add("avif")
IMAGE_IN = RASTER_IN | {"svg"}

PIL_FORMAT = {"jpg": "JPEG", "png": "PNG", "webp": "WEBP", "avif": "AVIF", "heic": "HEIF",
              "bmp": "BMP", "tiff": "TIFF", "gif": "GIF", "ico": "ICO", "pdf": "PDF"}
CANON = {"jpeg": "jpg", "jfif": "jpg", "tif": "tiff", "heif": "heic"}
ALLOWED_MODES = {
    "png": {"RGB", "RGBA", "L", "LA", "P", "1", "I;16"},
    "webp": {"RGB", "RGBA"}, "avif": {"RGB", "RGBA"}, "heic": {"RGB", "RGBA"},
    "bmp": {"RGB", "RGBA", "L", "P", "1"}, "tiff": {"RGB", "RGBA", "L", "LA", "P", "1", "CMYK"},
    "gif": {"RGB", "RGBA", "L", "P"}, "ico": {"RGBA"},
}


# --- Carga y guardado ---

def _load_svg(path, min_side=1024):
    from PySide6.QtCore import QBuffer, QIODevice, Qt
    from PySide6.QtGui import QImage, QPainter
    from PySide6.QtSvg import QSvgRenderer

    renderer = QSvgRenderer(str(path))
    if not renderer.isValid():
        raise RuntimeError("SVG no válido")
    size = renderer.defaultSize()
    w, h = max(size.width(), 1), max(size.height(), 1)
    scale = max(1.0, min_side / max(w, h))
    qimg = QImage(int(w * scale), int(h * scale), QImage.Format.Format_ARGB32)
    qimg.fill(Qt.GlobalColor.transparent)
    painter = QPainter(qimg)
    renderer.render(painter)
    painter.end()
    buf = QBuffer()
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    qimg.save(buf, "PNG")
    return Image.open(io.BytesIO(bytes(buf.data())))


def load(path):
    if ext(path) == "svg":
        return _load_svg(path)
    img = Image.open(path)
    if getattr(img, "n_frames", 1) > 1:
        return img
    return ImageOps.exif_transpose(img)


def has_alpha(img) -> bool:
    return img.mode in ("RGBA", "LA", "PA") or (img.mode == "P" and "transparency" in img.info)


def flatten(img, bg=(255, 255, 255)):
    if has_alpha(img):
        rgba = img.convert("RGBA")
        base = Image.new("RGB", rgba.size, bg)
        base.paste(rgba, mask=rgba.getchannel("A"))
        return base
    return img if img.mode == "RGB" else img.convert("RGB")


def save(img, out, target, ctx, quality=None):
    fmt = PIL_FORMAT[target]
    q = quality or ctx.quality
    kw = {}
    if getattr(img, "n_frames", 1) > 1:
        if target in ("gif", "webp", "png"):
            kw.update(save_all=True, loop=img.info.get("loop", 0), duration=img.info.get("duration", 100))
            if target == "webp":
                kw["quality"] = q
            img.save(out, fmt, **kw)
            return out
        img.seek(0)
        img = img.convert("RGBA")

    icc = img.info.get("icc_profile")
    if target in ("jpg", "pdf"):
        img = flatten(img)
    elif img.mode not in ALLOWED_MODES.get(target, {img.mode}):
        img = img.convert("RGBA" if has_alpha(img) or target == "ico" else "RGB")

    if target == "jpg":
        kw.update(quality=q, optimize=True, progressive=True)
    elif target in ("webp", "avif", "heic"):
        kw["quality"] = q
    elif target == "png":
        kw["optimize"] = True
    elif target == "tiff":
        kw["compression"] = "tiff_lzw"
    elif target == "ico":
        side = max(img.size)
        kw["sizes"] = [(s, s) for s in (16, 24, 32, 48, 64, 128, 256) if s <= side] or [(16, 16)]
    elif target == "pdf":
        kw["resolution"] = 150
    if icc and target in ("jpg", "png", "webp", "tiff"):
        kw["icc_profile"] = icc
    img.save(out, fmt, **kw)
    return out


def is_images(files, exts=IMAGE_IN):
    return all_ext(files, exts)


def writable_target(path) -> str:
    e = CANON.get(ext(path), ext(path))
    return e if e in PIL_FORMAT and e != "pdf" else "png"


# --- Conversiones ---

TARGETS = [("jpg", "JPG"), ("png", "PNG"), ("webp", "WebP"), ("avif", "AVIF"), ("heic", "HEIC"),
           ("bmp", "BMP"), ("tiff", "TIFF"), ("gif", "GIF"), ("ico", "ICO"), ("pdf", "PDF")]


def convert(src, target, ctx):
    out = ctx.out(src, target)
    return save(load(src), out, target, ctx)


for _t, _label in TARGETS:
    if (_t == "avif" and not HAS_AVIF) or (_t == "heic" and not HAS_HEIF):
        continue
    _same = {k for k, v in CANON.items() if v == _t} | {_t}
    register(
        id=f"img.{_t}", label=_label, mode="convert", group="image",
        accepts=lambda files, s=_same: is_images(files) and not all(ext(f) in s for f in files),
        func=lambda src, ctx, t=_t: convert(src, t, ctx),
    )


# --- Herramientas ---

def compress(src, ctx):
    target = writable_target(src)
    img = load(src)
    if target == "png":
        if getattr(img, "n_frames", 1) > 1:
            img.seek(0)
        img = img.convert("RGBA").quantize(256, method=Image.Quantize.FASTOCTREE)
    out = ctx.out(src, target, " (comprimida)")
    return save(img, out, target, ctx, quality=60)


def resize_half(src, ctx):
    target = writable_target(src)
    img = load(src)
    if getattr(img, "n_frames", 1) > 1:
        img.seek(0)
        img = img.convert("RGBA")
    img = img.resize((max(1, img.width // 2), max(1, img.height // 2)), Image.Resampling.LANCZOS)
    return save(img, ctx.out(src, target, " (50%)"), target, ctx)


def rotate(src, ctx):
    target = writable_target(src)
    img = load(src)
    if getattr(img, "n_frames", 1) > 1:
        img.seek(0)
        img = img.convert("RGBA")
    return save(img.rotate(-90, expand=True), ctx.out(src, target, " (rotada)"), target, ctx)


def strip_metadata(src, ctx):
    target = writable_target(src)
    img = load(src)
    clean = img.copy()
    clean.info = {k: v for k, v in img.info.items() if k == "transparency"}
    return save(clean, ctx.out(src, target, " (sin metadatos)"), target, ctx, quality=95)


def images_to_pdf(files, ctx):
    files = sorted(files, key=lambda f: f.name.lower())
    pages = [flatten(load(f)) for f in files]
    name = stem(files[0]) if len(files) == 1 else f"{stem(files[0])} + {len(files) - 1}"
    out = unique_path(ctx.folder_for(files[0]) / f"{name}.pdf")
    pages[0].save(out, "PDF", save_all=True, append_images=pages[1:], resolution=150)
    return out


register(id="img.compress", label="Comprimir", mode="tools", group="image",
         accepts=lambda f: is_images(f, RASTER_IN - {"gif"}), func=compress)
register(id="img.half", label="Reducir 50%", mode="tools", group="image",
         accepts=lambda f: is_images(f, RASTER_IN), func=resize_half)
register(id="img.rotate", label="Rotar 90°", mode="tools", group="image",
         accepts=lambda f: is_images(f, RASTER_IN), func=rotate)
register(id="img.strip", label="Quitar metadatos", mode="tools", group="image",
         accepts=lambda f: is_images(f, RASTER_IN - {"gif", "ico"}), func=strip_metadata)
register(id="img.topdf", label="Unir en un PDF", mode="tools", group="pdf",
         accepts=lambda f: is_images(f) and len(f) > 1, func=images_to_pdf, per_file=False)
