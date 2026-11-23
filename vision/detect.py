"""Detect clickable screen regions using YOLO or an OpenCV fallback."""

from pathlib import Path

from PIL import Image

from vision.ocr import run_ocr


def _iou(first: tuple[int, int, int, int], second: tuple[int, int, int, int]) -> float:
    """Calculate intersection-over-union for two boxes."""
    left = max(first[0], second[0])
    top = max(first[1], second[1])
    right = min(first[2], second[2])
    bottom = min(first[3], second[3])
    if right <= left or bottom <= top:
        return 0.0

    intersection = (right - left) * (bottom - top)
    first_area = (first[2] - first[0]) * (first[3] - first[1])
    second_area = (second[2] - second[0]) * (second[3] - second[1])
    return intersection / (first_area + second_area - intersection)


def _opencv_boxes(img: Image.Image) -> list[dict[str, object]]:
    """Find reasonably sized rectangular regions with Canny and contours."""
    import cv2
    import numpy as np

    array = cv2.cvtColor(np.asarray(img), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(array, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    boxes: list[dict[str, object]] = []
    width, height = img.size
    for contour in contours:
        x1, y1, box_width, box_height = cv2.boundingRect(contour)
        x2 = x1 + box_width
        y2 = y1 + box_height
        if box_width < 18 or box_height < 18:
            continue
        if box_width > width * 0.95 and box_height > height * 0.95:
            continue
        if box_width * box_height < 400:
            continue
        boxes.append({"bbox": (x1, y1, x2, y2), "kind": "region"})
    return boxes


def _merge_detections(detections: list[dict[str, object]]) -> list[dict[str, object]]:
    """Remove duplicate boxes using an IoU threshold."""
    merged: list[dict[str, object]] = []
    for detection in detections:
        bbox = detection["bbox"]
        if not isinstance(bbox, tuple):
            continue
        if any(_iou(bbox, kept["bbox"]) > 0.5 for kept in merged if isinstance(kept["bbox"], tuple)):
            continue
        merged.append(detection)
    return merged


def detect_elements(img: Image.Image) -> list[dict[str, object]]:
    """Detect elements, merging vision detections and OCR boxes."""
    detections: list[dict[str, object]] = []
    weights = Path("models") / "icon_detect.pt"

    if weights.is_file():
        try:
            from ultralytics import YOLO

            model = YOLO(str(weights))
            results = model.predict(source=img, imgsz=640, device="cpu", verbose=False)
            for result in results:
                for box in result.boxes:
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    kind = model.names.get(int(box.cls[0]), "icon")
                    detections.append(
                        {
                            "bbox": (int(x1), int(y1), int(x2), int(y2)),
                            "kind": str(kind),
                        }
                    )
        except Exception:
            detections.extend(_opencv_boxes(img))
    else:
        detections.extend(_opencv_boxes(img))

    for ocr_box in run_ocr(img):
        detections.append({"bbox": ocr_box["bbox"], "kind": "text", "text": ocr_box["text"]})

    return _merge_detections(detections)
