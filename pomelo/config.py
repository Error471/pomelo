import json
import os
import subprocess
import sys
from pathlib import Path

from . import APP_NAME
from .utils import IS_WIN

DEFAULTS = {
    "keys": {"convert": "shift", "tools": "ctrl", "actions": "alt"},
    "wheel_enabled": True,
    "theme": "system",
    "output_dir": "",
    "soffice_path": "",
    "image_quality": 90,
    "pdf_dpi": 150,
    "csv_separator": ";",
    "notifications": True,
    "autostart": False,
}


def config_dir() -> Path:
    base = os.environ.get("APPDATA") or str(Path.home() / ".config")
    d = Path(base) / APP_NAME
    d.mkdir(parents=True, exist_ok=True)
    return d


def config_file() -> Path:
    return config_dir() / "config.json"


def load() -> dict:
    cfg = json.loads(json.dumps(DEFAULTS))
    try:
        data = json.loads(config_file().read_text(encoding="utf-8"))
        for k, v in data.items():
            if isinstance(v, dict) and isinstance(cfg.get(k), dict):
                cfg[k].update(v)
            else:
                cfg[k] = v
    except (OSError, ValueError):
        pass
    return cfg


def save(cfg: dict):
    config_file().write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")


# --- Integración con Windows ---

def launch_command() -> tuple:
    if getattr(sys, "frozen", False):
        return sys.executable, ""
    exe = Path(sys.executable)
    pythonw = exe.with_name("pythonw.exe")
    main = Path(__file__).resolve().parent.parent / "main.py"
    return str(pythonw if pythonw.exists() else exe), f'"{main}"'


def set_autostart(enabled: bool):
    if not IS_WIN:
        return
    import winreg
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0,
                         winreg.KEY_SET_VALUE)
    with key:
        if enabled:
            exe, args = launch_command()
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, f'"{exe}" {args} --tray'.strip())
        else:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except FileNotFoundError:
                pass


def install_send_to() -> Path:
    if not IS_WIN:
        raise RuntimeError("Solo disponible en Windows")
    exe, args = launch_command()
    lnk = Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "SendTo" / f"{APP_NAME}.lnk"
    ps = (
        "$s=(New-Object -ComObject WScript.Shell).CreateShortcut($env:POMELO_LNK);"
        "$s.TargetPath=$env:POMELO_EXE;$s.Arguments=$env:POMELO_ARGS;$s.Save()"
    )
    env = {**os.environ, "POMELO_LNK": str(lnk), "POMELO_EXE": exe, "POMELO_ARGS": args}
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], env=env, check=True,
                   creationflags=0x08000000)
    return lnk
