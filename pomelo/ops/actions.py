import os
import shutil
import subprocess
from pathlib import Path

from ..registry import register
from ..utils import IS_WIN, reveal_in_explorer, unique_path


def _exists(files):
    return bool(files) and all(Path(f).exists() for f in files)


def copy_path(files, ctx):
    from PySide6.QtGui import QGuiApplication
    QGuiApplication.clipboard().setText("\n".join(str(f) for f in files))
    return []


def _transfer(files, title, move):
    from PySide6.QtWidgets import QFileDialog
    folder = QFileDialog.getExistingDirectory(None, title)
    if not folder:
        return []
    outs = []
    for f in files:
        f = Path(f)
        target = unique_path(Path(folder) / f.name, is_dir=f.is_dir())
        if move:
            shutil.move(str(f), target)
        elif f.is_dir():
            shutil.copytree(f, target)
        else:
            shutil.copy2(f, target)
        outs.append(target)
    return outs


def reveal(files, ctx):
    reveal_in_explorer(files[0])
    return []


def terminal(files, ctx):
    f = Path(files[0])
    folder = f if f.is_dir() else f.parent
    if IS_WIN:
        wt = shutil.which("wt")
        if wt:
            subprocess.Popen([wt, "-d", str(folder)])
        else:
            subprocess.Popen(["powershell", "-NoExit"], cwd=folder, creationflags=subprocess.CREATE_NEW_CONSOLE)
    else:
        term = shutil.which("x-terminal-emulator") or shutil.which("gnome-terminal") or "xterm"
        subprocess.Popen([term], cwd=folder)
    return []


def rename(files, ctx):
    from PySide6.QtWidgets import QInputDialog
    f = Path(files[0])
    name, ok = QInputDialog.getText(None, "Renombrar", "Nuevo nombre:", text=f.name)
    if not ok or not name.strip() or name == f.name:
        return []
    target = f.with_name(name.strip())
    if target.exists():
        raise RuntimeError(f"Ya existe «{target.name}»")
    os.replace(f, target)
    return [target]


_one = lambda f: _exists(f) and len(f) == 1  # noqa: E731
_common = dict(mode="actions", group="action", per_file=False, main_thread=True, accepts=_exists)

register(id="act.copypath", label="Copiar ruta", func=copy_path, notify=False, **_common)
register(id="act.copyto", label="Copiar a…", func=lambda f, c: _transfer(f, "Copiar a…", False), **_common)
register(id="act.moveto", label="Mover a…", func=lambda f, c: _transfer(f, "Mover a…", True), **_common)
register(id="act.reveal", label="Mostrar en carpeta", func=reveal, notify=False, **_common)
register(id="act.terminal", label="Abrir terminal aquí", func=terminal, notify=False, **_common)
register(id="act.rename", label="Renombrar…", func=rename,
         **{**_common, "accepts": _one})
