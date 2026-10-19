from pathlib import Path

from .utils import ext


def group_for(path) -> str:
    from .ops import archives, documents, images, media
    path = Path(path)
    if path.is_dir():
        return "folder"
    e = ext(path)
    if e == "pdf":
        return "pdf"
    for group, exts in (("image", images.IMAGE_IN), ("video", media.VIDEO_IN), ("audio", media.AUDIO_IN),
                        ("sheet", documents.SHEET_IN), ("slides", documents.SLIDE_IN),
                        ("doc", documents.WORD_IN | documents.TEXT_IN | documents.HTML_IN | documents.SUB_IN),
                        ("archive", archives.ARCH_IN)):
        if e in exts:
            return group
    return "file"


def group_for_files(files) -> str:
    groups = {group_for(f) for f in files}
    return groups.pop() if len(groups) == 1 else "file"


def human_size(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}".replace(".", ",")
        n /= 1024
    return ""


def describe_files(files) -> str:
    files = [Path(f) for f in files]
    size = sum(f.stat().st_size for f in files if f.is_file())
    head = files[0].name if len(files) == 1 else f"{len(files)} elementos"
    return f"{head} · {human_size(size)}" if size else head
