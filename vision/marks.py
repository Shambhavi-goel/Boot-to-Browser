"""Capture and annotate screen observations with numbered Set-of-Mark boxes."""

import logging
import time
from datetime import datetime
from pathlib import Path

from PIL import ImageDraw

from schema import Element, Observation
from vision.capture import grab_screen, resize_for_model
from vision.detect import detect_elements

logger = logging.getLogger("boot_to_browser")


def _label_for_detection(detection: dict[str, object]) -> str:
    """Choose OCR text or the detected kind as an element label."""
    text = detection.get("text")
    if isinstance(text, str) and text.strip():
        return text.strip()
    kind = detection.get("kind")
    return str(kind) if isinstance(kind, str) else "element"


def _number_position(
    box: tuple[int, int, int, int],
    number: int,
    image_width: int,
    image_height: int,
) -> tuple[int, int]:
    """Place a number near a box corner, away from its centre."""
    x1, y1, x2, y2 = box
    width = max(18, len(str(number)) * 10 + 8)
    height = 18

    if x1 - width >= 0:
        return x1 - width, max(0, y1)
    if y1 - height >= 0:
        return max(0, x1), y1 - height
    if x2 + width <= image_width:
        return x2, max(0, y1)

    return min(image_width - width, max(0, x1)), min(image_height - height, max(0, y1))


def observe() -> Observation:
    """Capture the screen, detect elements, and save a numbered observation image."""
    started = time.perf_counter()

    capture_started = time.perf_counter()
    real_image = grab_screen()
    screen_width, screen_height = real_image.size
    logger.info("vision.capture_ms=%d", round((time.perf_counter() - capture_started) * 1000))

    model_started = time.perf_counter()
    model_image, scale = resize_for_model(real_image)
    logger.info("vision.resize_ms=%d", round((time.perf_counter() - model_started) * 1000))

    detect_started = time.perf_counter()
    detections = detect_elements(model_image)
    logger.info("vision.detect_ms=%d", round((time.perf_counter() - detect_started) * 1000))

    draw_started = time.perf_counter()
    Path("logs").mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    image_path = str(Path("logs") / f"obs_{timestamp}.png")

    canvas = model_image.convert("RGB")
    draw = ImageDraw.Draw(canvas)
    elements: list[Element] = []

    for element_id, detection in enumerate(detections, start=1):
        bbox = detection.get("bbox")
        if not isinstance(bbox, tuple) or len(bbox) != 4:
            continue

        x1, y1, x2, y2 = (int(value) for value in bbox)
        real_box = (
            max(0, min(screen_width, round(x1 / scale))),
            max(0, min(screen_height, round(y1 / scale))),
            max(0, min(screen_width, round(x2 / scale))),
            max(0, min(screen_height, round(y2 / scale))),
        )

        colour = (255, 64, 64) if element_id % 2 else (64, 220, 255)
        draw.rectangle((x1, y1, x2, y2), outline=colour, width=3)

        number_x, number_y = _number_position(
            (x1, y1, x2, y2), element_id, canvas.width, canvas.height
        )
        label = str(element_id)
        text_width = max(18, draw.textlength(label) + 8)
        draw.rectangle(
            (number_x, number_y, number_x + int(text_width), number_y + 18),
            fill=(0, 0, 0),
        )
        draw.text((number_x + 4, number_y + 1), label, fill=(255, 255, 255))

        elements.append(
            Element(
                id=element_id,
                bbox=real_box,
                label=_label_for_detection(detection),
            )
        )

    canvas.save(image_path)
    logger.info("vision.draw_ms=%d", round((time.perf_counter() - draw_started) * 1000))
    logger.info("vision.total_ms=%d", round((time.perf_counter() - started) * 1000))

    return Observation(
        image_path=image_path,
        elements=elements,
        screen_size=(screen_width, screen_height),
    )
