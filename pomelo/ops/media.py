from ..registry import register
from ..utils import all_ext, ext, ffmpeg_exe, run_cmd

AUDIO_IN = {"mp3", "m4a", "aac", "wav", "flac", "ogg", "oga", "opus", "aiff", "aif", "wma", "amr", "ac3"}
VIDEO_IN = {"mp4", "mov", "mkv", "webm", "avi", "wmv", "m4v", "flv", "mpg", "mpeg", "3gp", "ts", "mts", "m2ts"}
EVEN = "scale=trunc(iw/2)*2:trunc(ih/2)*2"
H264 = ["-c:v", "libx264", "-crf", "23", "-preset", "medium", "-pix_fmt", "yuv420p", "-vf", EVEN,
        "-c:a", "aac", "-b:a", "160k"]

AUDIO_TARGETS = {
    "mp3": ("MP3", ["-vn", "-c:a", "libmp3lame", "-q:a", "2"]),
    "m4a": ("M4A", ["-vn", "-c:a", "aac", "-b:a", "192k"]),
    "wav": ("WAV", ["-vn", "-c:a", "pcm_s16le"]),
    "flac": ("FLAC", ["-vn", "-c:a", "flac"]),
    "ogg": ("OGG", ["-vn", "-c:a", "libvorbis", "-q:a", "5"]),
    "opus": ("Opus", ["-vn", "-c:a", "libopus", "-b:a", "128k"]),
    "aiff": ("AIFF", ["-vn", "-c:a", "pcm_s16be"]),
    "wma": ("WMA", ["-vn", "-c:a", "wmav2", "-b:a", "192k"]),
}
AUDIO_SAME = {"aiff": {"aif"}, "ogg": {"oga"}}

VIDEO_TARGETS = {
    "mp4": ("MP4", H264 + ["-movflags", "+faststart"]),
    "mov": ("MOV", H264),
    "mkv": ("MKV", H264),
    "webm": ("WebM", ["-c:v", "libvpx-vp9", "-crf", "32", "-b:v", "0", "-deadline", "good",
                      "-cpu-used", "4", "-row-mt", "1", "-pix_fmt", "yuv420p", "-c:a", "libopus", "-b:a", "128k"]),
    "avi": ("AVI", ["-c:v", "mpeg4", "-q:v", "4", "-vf", EVEN, "-c:a", "libmp3lame", "-q:a", "3"]),
    "wmv": ("WMV", ["-c:v", "wmv2", "-b:v", "3M", "-vf", EVEN, "-c:a", "wmav2", "-b:a", "160k"]),
    "gif": ("GIF", ["-an", "-vf", "fps=12,scale='min(480,iw)':-2:flags=lanczos,split[a][b];[a]palettegen[p];[b][p]paletteuse",
                    "-loop", "0"]),
}
VIDEO_SAME = {"mp4": {"m4v"}, "mpg": {"mpeg"}}


def ffmpeg(src, out, args):
    exe = ffmpeg_exe()
    if not exe:
        raise RuntimeError("No se encontró FFmpeg")
    run_cmd([exe, "-hide_banner", "-loglevel", "error", "-y", "-i", src, *args, out])
    return out


def _job(target, args, suffix=""):
    return lambda src, ctx: ffmpeg(src, ctx.out(src, target, suffix), args)


def _not_same(files, target, same):
    s = same.get(target, set()) | {target}
    return not all(ext(f) in s for f in files)


# --- Conversiones ---

for _t, (_label, _args) in AUDIO_TARGETS.items():
    register(id=f"audio.{_t}", label=_label, mode="convert", group="audio", requires=("ffmpeg",),
             accepts=lambda f, t=_t: all_ext(f, AUDIO_IN) and _not_same(f, t, AUDIO_SAME),
             func=_job(_t, _args))

for _t, (_label, _args) in VIDEO_TARGETS.items():
    _in = VIDEO_IN | ({"gif"} if _t in ("mp4", "webm") else set())
    register(id=f"video.{_t}", label=_label, mode="convert", group="video", requires=("ffmpeg",),
             accepts=lambda f, t=_t, i=_in: all_ext(f, i) and _not_same(f, t, VIDEO_SAME),
             func=_job(_t, _args))

for _t in ("mp3", "m4a", "wav"):
    _label, _args = AUDIO_TARGETS[_t]
    register(id=f"video.audio.{_t}", label=f"{_label} (audio)", mode="convert", group="audio",
             requires=("ffmpeg",), accepts=lambda f: all_ext(f, VIDEO_IN), func=_job(_t, _args))


# --- Herramientas ---

def _audio_args(path):
    e = {"aif": "aiff", "oga": "ogg"}.get(ext(path), ext(path))
    return (e, AUDIO_TARGETS[e][1]) if e in AUDIO_TARGETS else ("m4a", AUDIO_TARGETS["m4a"][1])


def compress_video(src, ctx):
    args = ["-c:v", "libx264", "-crf", "28", "-preset", "medium", "-pix_fmt", "yuv420p",
            "-vf", "scale='trunc(min(1920,iw)/2)*2':-2", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart"]
    return ffmpeg(src, ctx.out(src, "mp4", " (comprimido)"), args)


def to_720p(src, ctx):
    args = list(H264)
    args[args.index(EVEN)] = "scale=-2:'trunc(min(720,ih)/2)*2'"
    return ffmpeg(src, ctx.out(src, "mp4", " (720p)"), args + ["-movflags", "+faststart"])


def mute(src, ctx):
    return ffmpeg(src, ctx.out(src, ext(src), " (sin audio)"), ["-c:v", "copy", "-an"])


def normalize(src, ctx):
    e, args = _audio_args(src)
    return ffmpeg(src, ctx.out(src, e, " (normalizado)"), ["-af", "loudnorm=I=-16:TP=-1.5:LRA=11", *args])


def mono(src, ctx):
    e, args = _audio_args(src)
    return ffmpeg(src, ctx.out(src, e, " (mono)"), ["-ac", "1", *args])


def compress_audio(src, ctx):
    return ffmpeg(src, ctx.out(src, "mp3", " (comprimido)"), ["-vn", "-c:a", "libmp3lame", "-b:a", "128k"])


_video = lambda f: all_ext(f, VIDEO_IN)  # noqa: E731
_audio = lambda f: all_ext(f, AUDIO_IN)  # noqa: E731
register(id="video.compress", label="Comprimir vídeo", mode="tools", group="video",
         requires=("ffmpeg",), accepts=_video, func=compress_video)
register(id="video.720", label="Reducir a 720p", mode="tools", group="video",
         requires=("ffmpeg",), accepts=_video, func=to_720p)
register(id="video.mute", label="Quitar audio", mode="tools", group="video",
         requires=("ffmpeg",), accepts=_video, func=mute)
register(id="audio.normalize", label="Normalizar volumen", mode="tools", group="audio",
         requires=("ffmpeg",), accepts=_audio, func=normalize)
register(id="audio.mono", label="Pasar a mono", mode="tools", group="audio",
         requires=("ffmpeg",), accepts=_audio, func=mono)
register(id="audio.compress", label="Comprimir audio", mode="tools", group="audio",
         requires=("ffmpeg",), accepts=_audio, func=compress_audio)
