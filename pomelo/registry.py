from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .utils import requirement_label, requirement_ok, stem, unique_path

MODES = ("convert", "tools", "actions")
MODE_LABELS = {"convert": "Convertir", "tools": "Herramientas", "actions": "Acciones"}


@dataclass
class Context:
    config: dict

    def folder_for(self, src) -> Path:
        custom = self.config.get("output_dir") or ""
        folder = Path(custom) if custom else Path(src).parent
        folder.mkdir(parents=True, exist_ok=True)
        return folder

    def out(self, src, new_ext: str, suffix: str = "") -> Path:
        return unique_path(self.folder_for(src) / f"{stem(src)}{suffix}.{new_ext}")

    @property
    def quality(self) -> int:
        return int(self.config.get("image_quality", 90))


@dataclass
class Operation:
    id: str
    label: str
    mode: str
    group: str
    accepts: Callable[[list], bool]
    func: Callable
    per_file: bool = True
    requires: tuple = ()
    main_thread: bool = False
    notify: bool = True

    def missing(self) -> list:
        return [requirement_label(r) for r in self.requires if not requirement_ok(r)]

    @property
    def available(self) -> bool:
        return not self.missing()

    def execute(self, files, ctx):
        outputs, errors = [], []
        missing = self.missing()
        if missing:
            return [], [(None, f"Necesitas instalar: {', '.join(missing)}")]
        batches = [[f] for f in files] if self.per_file else [list(files)]
        for batch in batches:
            try:
                res = self.func(batch[0] if self.per_file else batch, ctx)
                if res is None:
                    continue
                outputs.extend(res if isinstance(res, (list, tuple)) else [res])
            except Exception as exc:  # noqa: BLE001
                errors.append((batch[0] if self.per_file else None, str(exc) or exc.__class__.__name__))
        return outputs, errors


OPERATIONS: list = []


def register(**kw) -> Operation:
    op = Operation(**kw)
    OPERATIONS.append(op)
    return op


def operations_for(mode: str, files) -> list:
    files = [Path(f) for f in files]
    result = []
    for op in OPERATIONS:
        if op.mode != mode:
            continue
        try:
            if op.accepts(files):
                result.append(op)
        except Exception:
            pass
    return result


def load_all():
    if OPERATIONS:
        return
    from .ops import images, media, documents, archives, actions  # noqa: F401
