import gzip
import os
import shutil
import tarfile
import tempfile
import zipfile
from pathlib import Path

from ..registry import register
from ..utils import all_ext, ext, stem, unique_path

ARCH_IN = {"zip", "tar", "tar.gz", "tgz", "tar.bz2", "tar.xz", "7z", "gz"}
TAR_MODES = {"tar": "r:", "tar.gz": "r:gz", "tgz": "r:gz", "tar.bz2": "r:bz2", "tar.xz": "r:xz"}


# --- Extracción ---

def _inside(base: Path, target: Path) -> bool:
    try:
        target.resolve().relative_to(base.resolve())
        return True
    except ValueError:
        return False


def extract(src, dest: Path):
    e = ext(src)
    if e == "zip":
        with zipfile.ZipFile(src) as z:
            for name in z.namelist():
                if not _inside(dest, dest / name):
                    raise RuntimeError(f"Ruta insegura en el ZIP: {name}")
            z.extractall(dest)
    elif e in TAR_MODES:
        with tarfile.open(src, TAR_MODES[e]) as t:
            try:
                t.extractall(dest, filter="data")
            except TypeError:
                for m in t.getmembers():
                    if not _inside(dest, dest / m.name) or m.issym() or m.islnk():
                        raise RuntimeError(f"Ruta insegura en el TAR: {m.name}")
                t.extractall(dest)
    elif e == "7z":
        import py7zr
        with py7zr.SevenZipFile(src, "r") as z:
            for name in z.getnames():
                if not _inside(dest, dest / name):
                    raise RuntimeError(f"Ruta insegura en el 7Z: {name}")
            z.extractall(dest)
    elif e == "gz":
        with gzip.open(src, "rb") as g, open(dest / stem(src), "wb") as o:
            shutil.copyfileobj(g, o)
    else:
        raise RuntimeError("Formato no soportado")


def extract_here(src, ctx):
    dest = unique_path(ctx.folder_for(src) / stem(src), is_dir=True)
    dest.mkdir(parents=True)
    try:
        extract(src, dest)
    except Exception:
        shutil.rmtree(dest, ignore_errors=True)
        raise
    return dest


# --- Empaquetado ---

def _walk(items):
    for item in items:
        item = Path(item)
        if item.is_dir():
            yield item, item.name
            for root, _dirs, names in os.walk(item):
                for n in names:
                    p = Path(root) / n
                    yield p, str(Path(item.name) / p.relative_to(item))
        else:
            yield item, item.name


def pack(items, out: Path, fmt: str):
    if fmt == "zip":
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
            for path, arc in _walk(items):
                if path.is_file():
                    z.write(path, arc)
    elif fmt == "tar.gz":
        with tarfile.open(out, "w:gz") as t:
            for item in items:
                t.add(item, arcname=Path(item).name)
    elif fmt == "7z":
        import py7zr
        with py7zr.SevenZipFile(out, "w") as z:
            for item in items:
                item = Path(item)
                if item.is_dir():
                    z.writeall(item, item.name)
                else:
                    z.write(item, item.name)
    return out


def repack(src, ctx, fmt):
    with tempfile.TemporaryDirectory() as tmp:
        extract(src, Path(tmp))
        return pack(sorted(Path(tmp).iterdir()), ctx.out(src, fmt), fmt)


def pack_items(files, ctx, fmt):
    files = [Path(f) for f in files]
    if len(files) == 1:
        name = files[0].name if files[0].is_dir() else stem(files[0])
    else:
        name = files[0].parent.name or "Archivos"
    out = unique_path(ctx.folder_for(files[0]) / f"{name}.{fmt}")
    return pack(files, out, fmt)


# --- Registro ---

_arch = lambda f: all_ext(f, ARCH_IN)  # noqa: E731
_exists = lambda f: bool(f) and all(Path(x).exists() for x in f)  # noqa: E731
_SAME = {"zip": {"zip"}, "tar.gz": {"tar.gz", "tgz"}, "7z": {"7z"}}

register(id="arch.extract", label="Extraer aquí", mode="convert", group="archive",
         accepts=_arch, func=extract_here)
for _fmt, _label in (("zip", "ZIP"), ("tar.gz", "TAR.GZ"), ("7z", "7Z")):
    register(id=f"arch.{_fmt}", label=_label, mode="convert", group="archive",
             requires=("py:py7zr",) if _fmt == "7z" else (),
             accepts=lambda f, s=_SAME[_fmt]: all_ext(f, ARCH_IN - {"gz"}) and not all(ext(x) in s for x in f),
             func=lambda s, c, fm=_fmt: repack(s, c, fm))

register(id="arch.packzip", label="Comprimir en ZIP", mode="tools", group="archive", per_file=False,
         accepts=_exists, func=lambda f, c: pack_items(f, c, "zip"))
register(id="arch.pack7z", label="Comprimir en 7Z", mode="tools", group="archive", per_file=False,
         requires=("py:py7zr",), accepts=_exists, func=lambda f, c: pack_items(f, c, "7z"))
