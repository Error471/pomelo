import importlib.util
import os
import shutil
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

IS_WIN = sys.platform == "win32"
CREATE_NO_WINDOW = 0x08000000 if IS_WIN else 0
MULTI_EXT = ("tar.gz", "tar.bz2", "tar.xz")


# --- Nombres y rutas ---

def ext(p) -> str:
    name = Path(p).name.lower()
    for m in MULTI_EXT:
        if name.endswith("." + m):
            return m
    return Path(p).suffix.lower().lstrip(".")


def stem(p) -> str:
    p = Path(p)
    if p.is_dir():
        return p.name
    e = ext(p)
    return p.name[: -(len(e) + 1)] if e else p.name


def unique_path(path, is_dir: bool = False) -> Path:
    path = Path(path)
    if not path.exists():
        return path
    if is_dir:
        base, suf = path.name, ""
    else:
        e = ext(path)
        base, suf = (path.name[: -(len(e) + 1)], f".{e}") if e else (path.name, "")
    i = 1
    while True:
        cand = path.with_name(f"{base} ({i}){suf}")
        if not cand.exists():
            return cand
        i += 1


def all_ext(files, exts) -> bool:
    return bool(files) and all(f.is_file() and ext(f) in exts for f in files)


# --- Procesos externos ---

def run_cmd(cmd, cwd=None):
    r = subprocess.run(
        [str(c) for c in cmd], cwd=cwd, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=CREATE_NO_WINDOW,
    )
    if r.returncode != 0:
        lines = r.stderr.decode("utf-8", "replace").strip().splitlines()
        raise RuntimeError("\n".join(lines[-4:]) or f"El proceso terminó con código {r.returncode}")
    return r


@lru_cache(maxsize=1)
def ffmpeg_exe():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return shutil.which("ffmpeg")


@lru_cache(maxsize=1)
def soffice_exe():
    found = shutil.which("soffice") or shutil.which("libreoffice")
    if found:
        return found
    if IS_WIN:
        for env in ("ProgramFiles", "ProgramFiles(x86)", "ProgramW6432"):
            base = os.environ.get(env)
            if base:
                cand = Path(base) / "LibreOffice" / "program" / "soffice.exe"
                if cand.exists():
                    return str(cand)
    return None


def has_module(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except Exception:
        return False


REQUIREMENT_LABELS = {"ffmpeg": "FFmpeg", "libreoffice": "LibreOffice"}


def requirement_ok(req: str) -> bool:
    if req == "ffmpeg":
        return ffmpeg_exe() is not None
    if req == "libreoffice":
        return soffice_exe() is not None
    if req.startswith("py:"):
        return has_module(req[3:])
    return True


def requirement_label(req: str) -> str:
    return REQUIREMENT_LABELS.get(req, req[3:] if req.startswith("py:") else req)


# --- Sistema ---

def reveal_in_explorer(path):
    path = Path(path)
    if IS_WIN:
        subprocess.Popen(f'explorer /select,"{path}"')
    else:
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path.parent if path.is_file() else path)))


def resource_path(rel: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return base / rel
