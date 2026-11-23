"""Lazy OCR for captured screen images."""

from typing import Any

from PIL import Image

_engine: Any | None = None


def _get_engine() -> Any:
    """Load the RapidOCR engine once on first use."""
    global _engine
    if _engine is None:
        from rapidocr_onnxruntime import RapidOCR

        _engine = RapidOCR()
    return _engine


def run_ocr(img: Image.Image) -> list[dict[str, object]]:
    """Run OCR and return text, bounding boxes, and confidences."""
    import numpy as np

    engine = _get_engine()
    result, _ = engine(np.asarray(img))
    if not result:
        return []

    detections: list[dict[str, object]] = []
    for points, text, confidence in result:
        xs = [int(point[0]) for point in points]
        ys = [int(point[1]) for point in points]
        detections.append(
            {
                "text": str(text),
                "bbox": (min(xs), min(ys), max(xs), max(ys)),
                "conf": float(confidence),
            }
        )
    return detections
