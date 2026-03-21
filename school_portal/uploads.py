"""Checking, cleaning and storing uploaded images.

The type is decided by what Pillow finds in the file, never by the name or the
browser's content type. Each image is decoded and written again, which drops
EXIF (GPS position, camera serial, time) and anything else that rode along in
the file. A thumbnail is made at the same time.
"""

import contextlib
import io
import os
from dataclasses import dataclass

from flask import current_app
from PIL import Image, UnidentifiedImageError
from werkzeug.datastructures import FileStorage

from .extensions import db
from .models import Media
from .models.media import new_media_id

FORMATS = {
    "JPEG": ("image/jpeg", "jpg"),
    "PNG": ("image/png", "png"),
    "WEBP": ("image/webp", "webp"),
}
MAX_PIXELS = 40_000_000
LONG_EDGE = 2048
THUMB_EDGE = 480


class UploadError(ValueError):
    pass


@dataclass
class Cleaned:
    data: bytes
    thumb: bytes
    content_type: str
    ext: str
    width: int
    height: int


def max_bytes() -> int:
    return current_app.config["MAX_UPLOAD_MB"] * 1024 * 1024


def clean_image(raw: bytes, limit: int) -> Cleaned:
    if len(raw) == 0:
        raise UploadError("The file is empty.")
    if len(raw) > limit:
        raise UploadError(f"The file is larger than {limit // (1024 * 1024)} MB.")
    try:
        with Image.open(io.BytesIO(raw)) as probe:
            fmt = probe.format
            if fmt not in FORMATS:
                raise UploadError("Only JPEG, PNG and WebP images can be uploaded.")
            if probe.width * probe.height > MAX_PIXELS:
                raise UploadError("The image has too many pixels.")
            probe.verify()
        image = Image.open(io.BytesIO(raw))
        image.load()
    except UploadError:
        raise
    except (UnidentifiedImageError, OSError, SyntaxError, Image.DecompressionBombError) as exc:
        raise UploadError("That file is not an image that can be read.") from exc

    content_type, ext = FORMATS[fmt]
    if fmt == "JPEG" and image.mode not in ("RGB", "L"):
        image = image.convert("RGB")
    image.thumbnail((LONG_EDGE, LONG_EDGE))
    data = _encode(image, fmt)
    thumb_image = image.copy()
    thumb_image.thumbnail((THUMB_EDGE, THUMB_EDGE))
    thumb = _encode(thumb_image, fmt)
    return Cleaned(data, thumb, content_type, ext, image.width, image.height)


def _encode(image: Image.Image, fmt: str) -> bytes:
    out = io.BytesIO()
    # No exif=, no pnginfo=: nothing but the pixels is written.
    if fmt == "JPEG":
        image.save(out, "JPEG", quality=85, optimize=True)
    elif fmt == "PNG":
        image.save(out, "PNG", optimize=True)
    else:
        image.save(out, "WEBP", quality=85)
    return out.getvalue()


def read_limited(file: FileStorage, limit: int) -> bytes:
    """Read at most limit + 1 bytes, so an oversized file is not read whole."""
    return file.stream.read(limit + 1)


def save_image(file: FileStorage, *, purpose: str, user_id: int | None) -> Media:
    if file is None or not file.filename:
        raise UploadError("Choose a file to upload.")
    limit = max_bytes()
    cleaned = clean_image(read_limited(file, limit), limit)
    media_id = new_media_id()
    folder = os.path.join(current_app.config["UPLOAD_DIR"], media_id[:2])
    os.makedirs(folder, exist_ok=True)
    stored = f"{media_id[:2]}/{media_id}.{cleaned.ext}"
    thumb = f"{media_id[:2]}/{media_id}.thumb.{cleaned.ext}"
    _write(stored, cleaned.data)
    _write(thumb, cleaned.thumb)
    media = Media(
        id=media_id,
        purpose=purpose,
        content_type=cleaned.content_type,
        size=len(cleaned.data),
        width=cleaned.width,
        height=cleaned.height,
        stored_name=stored,
        thumb_name=thumb,
        uploaded_by_id=user_id,
    )
    db.session.add(media)
    return media


def _write(name: str, data: bytes) -> None:
    path = os.path.join(current_app.config["UPLOAD_DIR"], name)
    with open(path, "wb") as fh:
        fh.write(data)


def path_of(name: str) -> str:
    return os.path.join(current_app.config["UPLOAD_DIR"], name)


def delete_files(media: Media) -> None:
    for name in (media.stored_name, media.thumb_name):
        with contextlib.suppress(FileNotFoundError):
            os.remove(path_of(name))
