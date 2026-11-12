"""Safe media serving: path allowlist, HTTP Range and thumbnail cache."""

from __future__ import annotations

import hashlib
import mimetypes
import re
import subprocess
from pathlib import Path, PurePosixPath

from drama_studio import paths

ROOT = paths.output_root()
REPO_ROOT = paths.repo_root()
ALLOWED_ROOTS = ("assets", "experiments", "projects", "literary_intelligence", "workflows")
THUMB_DIR = ROOT / "logs" / "workspace" / "thumbs"

EXTRA_TYPES = {
    ".mp4": "video/mp4",
    ".mov": "video/quicktime",
    ".webm": "video/webm",
    ".wav": "audio/wav",
    ".mp3": "audio/mpeg",
    ".flac": "audio/flac",
    ".srt": "text/plain; charset=utf-8",
    ".ass": "text/plain; charset=utf-8",
    ".md": "text/markdown; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".otf": "font/otf",
    ".ttf": "font/ttf",
}


class MediaError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


class RangeNotSatisfiable(MediaError):
    def __init__(self) -> None:
        super().__init__("range_not_satisfiable", "请求的字节范围超出文件大小")


def content_type(path: Path) -> str:
    return EXTRA_TYPES.get(path.suffix.lower()) or mimetypes.guess_type(path.name)[0] or "application/octet-stream"


def safe_path(rel_path: str, *, must_exist: bool = True) -> Path:
    if not rel_path or rel_path.startswith(("/", "\\")) or re.match(r"^[A-Za-z]:", rel_path):
        raise MediaError("invalid_path", "只允许工作区相对路径")
    pure = PurePosixPath(rel_path.replace("\\", "/"))
    if not pure.parts or any(part in ("..", "", ".") for part in pure.parts):
        raise MediaError("invalid_path", "路径不能包含 .. / . / 空段")
    base = REPO_ROOT if paths.is_repo_path(pure) else ROOT
    resolved = (base / pure).resolve()
    allowed = False
    for name in ALLOWED_ROOTS:
        allowed_base = ((REPO_ROOT if name in ("assets", "workflows") else ROOT) / name).resolve()
        if resolved == allowed_base or resolved.is_relative_to(allowed_base):
            allowed = True
            break
    if not allowed:
        raise MediaError("forbidden_path", "该路径不在允许的媒体目录内")
    if must_exist and not resolved.is_file():
        raise MediaError("not_found", "文件不存在")
    return resolved


def parse_range(header: str, size: int) -> tuple[int, int]:
    match = re.match(r"bytes=(\d*)-(\d*)$", header.strip())
    if not match:
        raise MediaError("invalid_range", "无法解析 Range 头")
    start_raw, end_raw = match.groups()
    if start_raw == "" and end_raw == "":
        raise MediaError("invalid_range", "Range 头为空")
    if start_raw == "":
        length = int(end_raw)
        if length <= 0:
            raise RangeNotSatisfiable()
        start = max(0, size - length)
        end = size - 1
    else:
        start = int(start_raw)
        end = int(end_raw) if end_raw else size - 1
    if start >= size or start < 0:
        raise RangeNotSatisfiable()
    end = min(end, size - 1)
    if end < start:
        raise RangeNotSatisfiable()
    return start, end


def iter_file(path: Path, start: int, end: int, chunk_size: int = 256 * 1024):
    remaining = end - start + 1
    with path.open("rb") as fh:
        fh.seek(start)
        while remaining > 0:
            chunk = fh.read(min(chunk_size, remaining))
            if not chunk:
                break
            remaining -= len(chunk)
            yield chunk


def _thumb_key(path: Path, width: int) -> str:
    st = path.stat()
    raw = f"{path}|{st.st_mtime_ns}|{st.st_size}|{width}".encode("utf-8")
    return hashlib.sha1(raw).hexdigest()


def thumbnail(rel_path: str, width: int = 480) -> Path:
    path = safe_path(rel_path)
    width = max(80, min(int(width), 960))
    THUMB_DIR.mkdir(parents=True, exist_ok=True)
    target = THUMB_DIR / f"{_thumb_key(path, width)}.jpg"
    if target.is_file():
        return target
    ext = path.suffix.lower()
    if ext in {".png", ".jpg", ".jpeg", ".webp"}:
        try:
            from PIL import Image
        except ImportError as exc:  # pragma: no cover - pillow is a project dependency
            raise MediaError("thumbnail_unavailable", "Pillow 不可用") from exc
        try:
            with Image.open(path) as image:
                image = image.convert("RGB")
                image.thumbnail((width, width * 3))
                image.save(target, "JPEG", quality=82)
        except Exception as exc:  # noqa: BLE001 - any decode error means no thumbnail
            raise MediaError("thumbnail_failed", f"无法生成缩略图: {exc}") from exc
        return target
    if ext in {".mp4", ".mov", ".webm", ".mkv"}:
        cmd = [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-ss",
            "1.0",
            "-i",
            str(path),
            "-frames:v",
            "1",
            "-vf",
            f"scale={width}:-2",
            str(target),
        ]
        try:
            proc = subprocess.run(cmd, capture_output=True, timeout=60)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise MediaError("thumbnail_failed", f"ffmpeg 无法生成缩略图: {exc}") from exc
        if proc.returncode != 0 or not target.is_file():
            raise MediaError("thumbnail_failed", proc.stderr.decode("utf-8", "replace")[-300:])
        return target
    raise MediaError("thumbnail_unsupported", "该文件类型没有缩略图")
