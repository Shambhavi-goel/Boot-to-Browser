"""Lightweight visual verification helpers."""

from PIL import Image


def screen_changed(before_img: Image.Image, after_img: Image.Image, threshold: float = 0.01) -> bool:
    """Return whether downscaled pixel differences exceed the threshold."""
    if before_img.size != after_img.size:
        return True

    before = before_img.convert("RGB").resize((160, 90), Image.Resampling.BILINEAR)
    after = after_img.convert("RGB").resize((160, 90), Image.Resampling.BILINEAR)

    differences = 0
    total = before.width * before.height * 3
    for before_pixel, after_pixel in zip(before.getdata(), after.getdata(), strict=True):
        differences += sum(abs(first - second) for first, second in zip(before_pixel, after_pixel, strict=True))

    return differences / (total * 255) > threshold
