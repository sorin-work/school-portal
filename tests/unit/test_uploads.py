import io

import pytest
from PIL import Image

from school_portal.uploads import UploadError, clean_image

from ..images import jpeg_with_exif, png

LIMIT = 1024 * 1024


def test_exif_is_removed():
    raw = jpeg_with_exif()
    assert Image.open(io.BytesIO(raw)).getexif()  # the test image does carry EXIF
    cleaned = clean_image(raw, LIMIT)
    assert cleaned.content_type == "image/jpeg"
    result = Image.open(io.BytesIO(cleaned.data))
    assert not result.getexif()
    assert "exif" not in result.info
    assert not Image.open(io.BytesIO(cleaned.thumb)).getexif()


def test_png_keeps_its_format():
    cleaned = clean_image(png(), LIMIT)
    assert (cleaned.content_type, cleaned.ext) == ("image/png", "png")


def test_files_that_are_not_images_are_refused():
    with pytest.raises(UploadError, match="not an image"):
        clean_image(b"%PDF-1.7 pretending to be a photo", LIMIT)


def test_svg_and_gif_are_refused():
    gif = io.BytesIO()
    Image.new("RGB", (4, 4)).save(gif, "GIF")
    with pytest.raises(UploadError, match="Only JPEG, PNG and WebP"):
        clean_image(gif.getvalue(), LIMIT)
    with pytest.raises(UploadError):
        clean_image(b'<svg xmlns="http://www.w3.org/2000/svg"><script/></svg>', LIMIT)


def test_size_limit():
    with pytest.raises(UploadError, match="larger than"):
        clean_image(b"x" * (LIMIT + 1), LIMIT)
    with pytest.raises(UploadError, match="empty"):
        clean_image(b"", LIMIT)


def test_large_images_are_scaled_down():
    out = io.BytesIO()
    Image.new("RGB", (4000, 1000), (1, 2, 3)).save(out, "JPEG")
    cleaned = clean_image(out.getvalue(), 20 * LIMIT)
    assert (cleaned.width, cleaned.height) == (2048, 512)


def test_phone_orientation_is_applied_before_exif_goes():
    # Orientation 6 means "rotate 90 degrees clockwise to display".
    cleaned = clean_image(jpeg_with_exif(size=(64, 48), orientation=6), LIMIT)
    assert (cleaned.width, cleaned.height) == (48, 64)
