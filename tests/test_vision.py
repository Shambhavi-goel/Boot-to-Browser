"""Synthetic tests for vision capture, detection, and Set-of-Mark output."""

from pathlib import Path

import pytest
from PIL import Image, ImageDraw, ImageFont

from vision.capture import resize_for_model


def _synthetic_image(width: int = 640, height: int = 360) -> Image.Image:
    """Create an image containing two rectangular clickable regions."""
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((40, 50, 180, 110), outline="black", width=4)
    draw.rectangle((260, 180, 430, 250), outline="black", width=4)

    try:
        font = ImageFont.truetype("arial.ttf", 18)
    except OSError:
        font = ImageFont.load_default()
    draw.text((55, 65), "Submit", fill="black", font=font)
    return image


def test_resize_for_model_preserves_aspect_ratio_and_scale() -> None:
    """Wide images are resized and report their scale."""
    image = _synthetic_image(width=2560, height=1440)

    resized, scale = resize_for_model(image, max_width=1280)

    assert resized.size == (1280, 720)
    assert scale == 0.5


def test_resize_for_model_keeps_small_image() -> None:
    """Images below the limit are copied unchanged."""
    image = _synthetic_image()

    resized, scale = resize_for_model(image)

    assert resized.size == image.size
    assert scale == 1.0
    assert resized is not image


def test_detect_elements_finds_rectangles(monkeypatch: pytest.MonkeyPatch) -> None:
    """The Canny fallback finds synthetic rectangular regions."""
    monkeypatch.setattr("vision.detect.run_ocr", lambda _image: [])
    from vision.detect import detect_elements

    detections = detect_elements(_synthetic_image())

    assert detections
    assert all("bbox" in detection and "kind" in detection for detection in detections)


def test_observe_marks_elements_and_scales_coordinates(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Observe writes a marked image and scales model boxes to real pixels."""
    image = _synthetic_image(width=1920, height=1080)
    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr("vision.marks.grab_screen", lambda: image)
    monkeypatch.setattr(
        "vision.marks.resize_for_model",
        lambda image, _max_width=1280: (
            image.resize((1280, 720)),
            2 / 3,
        ),
    )
    monkeypatch.setattr(
        "vision.marks.detect_elements",
        lambda _img: [
            {"bbox": (40, 50, 180, 110), "kind": "button", "text": "Submit"},
            {"bbox": (260, 180, 430, 250), "kind": "region"},
        ],
    )

    from vision.marks import observe

    observation = observe()

    assert observation.screen_size == (1920, 1080)
    assert len(observation.elements) == 2
    assert observation.elements[0].bbox == (60, 75, 270, 165)
    assert observation.elements[0].label == "Submit"
    assert Path(observation.image_path).is_file()
