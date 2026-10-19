import os
import sys


def _redirect_streams():
    # Sin consola (pythonw / exe) stdout y stderr son None: se redirigen a un log
    if sys.stdout is None or sys.stderr is None:
        from pomelo.config import config_dir
        log = open(config_dir() / "pomelo.log", "a", encoding="utf-8", buffering=1)
        sys.stdout = sys.stdout or log
        sys.stderr = sys.stderr or log


def main():
    _redirect_streams()
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    start_in_tray = "--tray" in sys.argv

    from PySide6.QtWidgets import QApplication
    from pomelo import APP_NAME
    from pomelo.app import PomeloApp, send_to_running_instance

    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
    qapp = QApplication(sys.argv)
    qapp.setApplicationName(APP_NAME)
    qapp.setQuitOnLastWindowClosed(False)

    if send_to_running_instance(args):
        return 0

    _app = PomeloApp(qapp, start_in_tray=start_in_tray, files=args)  # noqa: F841
    return qapp.exec()


if __name__ == "__main__":
    sys.exit(main())
