"""Primary-monitor screen capture utilities."""

from PIL import Image

try:
    import ctypes

    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except (AttributeError, OSError):
    pass


def grab_screen() -> Image.Image:
    """Capture the Windows primary monitor and return an RGB PIL image."""
    import mss

    with mss.mss() as monitor:
        primary = monitor.monitors[1]
        pixels = monitor.grab(primary)

    return Image.frombytes("RGB", pixels.size, pixels.bgra, "raw", "BGRX")


def resize_for_model(
    img: Image.Image,
    max_width: int = 1280,
) -> tuple[Image.Image, float]:
    """Resize an image so its width does not exceed max_width."""
    if img.width <= max_width:
        return img.copy(), 1.0

    scale = max_width / img.width
    new_height = max(1, round(img.height * scale))
    resized = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
    return resized, scale
