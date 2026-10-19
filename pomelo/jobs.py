import itertools

from PySide6.QtCore import QObject, QRunnable, QThreadPool, QTimer, Signal


class _Signals(QObject):
    finished = Signal(int, object, list, list)


class _Job(QRunnable):
    def __init__(self, job_id, op, files, ctx):
        super().__init__()
        self.job_id, self.op, self.files, self.ctx = job_id, op, files, ctx
        self.signals = _Signals()

    def run(self):
        outputs, errors = self.op.execute(self.files, self.ctx)
        self.signals.finished.emit(self.job_id, self.op, outputs, errors)


class JobManager(QObject):
    started = Signal(int, object, list)
    done = Signal(int, object, list, list)
    busy_changed = Signal(int)

    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.pool = QThreadPool.globalInstance()
        self.pool.setMaxThreadCount(max(2, min(4, self.pool.maxThreadCount())))
        self.active = 0
        self._ids = itertools.count(1)
        self._jobs = {}

    def submit(self, op, files):
        files = list(files)
        job_id = next(self._ids)
        self.started.emit(job_id, op, files)
        self._set_active(self.active + 1)
        if op.main_thread:
            QTimer.singleShot(0, lambda: self._finish(job_id, op, *op.execute(files, self.ctx)))
            return job_id
        job = _Job(job_id, op, files, self.ctx)
        job.setAutoDelete(False)
        self._jobs[job_id] = job
        job.signals.finished.connect(self._finish)
        self.pool.start(job)
        return job_id

    def _finish(self, job_id, op, outputs, errors):
        self._jobs.pop(job_id, None)
        self._set_active(self.active - 1)
        self.done.emit(job_id, op, outputs, errors)

    def _set_active(self, n):
        self.active = max(0, n)
        self.busy_changed.emit(self.active)
