"""
Upload validation helpers.

Never trust the filename or the client supplied Content-Type. The kind of a
file is detected from its bytes. Images are additionally verified by Pillow.
"""

import os

from django.conf import settings
from PIL import Image, UnidentifiedImageError


class UnsupportedUpload(ValueError):
    """Raised when an uploaded file is not a safe image or video."""


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
VIDEO_EXTENSIONS = {
    ".mp4",
    ".m4v",
    ".mov",
    ".webm",
    ".avi",
    ".mpeg",
    ".mpg",
    ".ogv",
}

MAX_IMAGE_PIXELS = 50_000_000


def _read_head(uploaded_file, size=64):
    uploaded_file.seek(0)
    head = uploaded_file.read(size)
    uploaded_file.seek(0)
    return head


def _is_png(head):
    return head.startswith(b"\x89PNG\r\n\x1a\n")


def _is_jpeg(head):
    return head.startswith(b"\xff\xd8\xff")


def _is_gif(head):
    return head.startswith((b"GIF87a", b"GIF89a"))


def _is_webp(head):
    return (
        head[:4] == b"RIFF"
        and len(head) >= 12
        and head[8:12] == b"WEBP"
    )


def _is_image_magic(head):
    return (
        _is_png(head)
        or _is_jpeg(head)
        or _is_gif(head)
        or _is_webp(head)
    )


def _is_mp4_like(head):
    return len(head) >= 12 and head[4:8] == b"ftyp"


def _is_video_magic(head):
    if _is_mp4_like(head):
        return True
    if head.startswith(b"\x1a\x45\xdf\xa3"):  # Matroska / WebM
        return True
    if head.startswith(b"RIFF") and head[8:12] == b"AVI ":
        return True
    if head.startswith(b"OggS"):
        return True
    if head.startswith((b"\x00\x00\x01\xba", b"\x00\x00\x01\xb3")):
        return True
    return False


def _verify_image(uploaded_file):
    try:
        with Image.open(uploaded_file) as image:
            width, height = image.size
            if width * height > MAX_IMAGE_PIXELS:
                raise UnsupportedUpload(
                    "Image dimensions are too large."
                )
            image.verify()
    except UnsupportedUpload:
        raise
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError):
        raise UnsupportedUpload("The file is not a valid image.")
    finally:
        uploaded_file.seek(0)


def classify_upload(uploaded_file):
    """
    Return "image" or "video" for a safe upload, raising UnsupportedUpload
    otherwise. The original file position is restored.
    """
    if uploaded_file is None:
        raise UnsupportedUpload("No file was provided.")

    try:
        size = uploaded_file.size
    except (AttributeError, OSError):
        raise UnsupportedUpload("The uploaded file could not be read.")

    if not size:
        raise UnsupportedUpload("Empty files are not allowed.")

    if size > settings.MAX_UPLOAD_SIZE:
        raise UnsupportedUpload(
            f"File size must not exceed "
            f"{settings.MAX_UPLOAD_SIZE_MB} MB."
        )

    name = os.path.basename(getattr(uploaded_file, "name", "") or "")
    extension = os.path.splitext(name)[1].lower()
    head = _read_head(uploaded_file)

    if extension in IMAGE_EXTENSIONS and _is_image_magic(head):
        _verify_image(uploaded_file)
        return "image"

    if extension in VIDEO_EXTENSIONS and _is_video_magic(head):
        return "video"

    raise UnsupportedUpload(
        "Only safe image (JPG, PNG, GIF, WebP) and video "
        "(MP4, MOV, WebM, AVI, MPEG) files are allowed."
    )


def validate_media_file(uploaded_file):
    """Validate a single upload and tag it with the detected kind."""
    kind = classify_upload(uploaded_file)
    uploaded_file._detected_media_kind = kind
    return uploaded_file


def media_kind(uploaded_file):
    kind = getattr(uploaded_file, "_detected_media_kind", None)
    if kind is None:
        kind = classify_upload(uploaded_file)
        uploaded_file._detected_media_kind = kind
    return kind
