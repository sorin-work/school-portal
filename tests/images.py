"""Images made on the fly for the upload tests."""

import io

from PIL import Image


def jpeg_with_exif(size=(64, 48), orientation: int | None = None) -> bytes:
    image = Image.new("RGB", size, (200, 120, 40))
    exif = Image.Exif()
    exif[0x010F] = "Example Camera Co"  # Make
    exif[0x0131] = "Test firmware"  # Software
    if orientation is not None:
        exif[0x0112] = orientation
    # GPS IFD with a latitude reference, enough to prove it is dropped.
    exif.get_ifd(0x8825)[1] = "N"
    out = io.BytesIO()
    image.save(out, "JPEG", exif=exif.tobytes())
    return out.getvalue()


def png(size=(32, 32), mode="RGBA") -> bytes:
    out = io.BytesIO()
    Image.new(mode, size, (10, 200, 10, 128) if mode == "RGBA" else (10, 200, 10)).save(out, "PNG")
    return out.getvalue()
