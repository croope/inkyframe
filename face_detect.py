"""
face_detect.py — Face detection and face-aware smart cropping.

Uses OpenCV's Haar cascade for detection.  Falls back gracefully — returning
an empty list / a plain centred crop — when OpenCV is not installed.
"""

from __future__ import annotations

from typing import List, Tuple

from PIL import Image, ImageOps

# Lazy-initialised cascade classifier
_CASCADE = None


def _get_cascade():
    global _CASCADE
    if _CASCADE is None:
        import cv2  # type: ignore
        path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        _CASCADE = cv2.CascadeClassifier(path)
    return _CASCADE


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def detect_faces(img: Image.Image) -> List[Tuple[int, int, int, int]]:
    """
    Return a list of ``(x, y, w, h)`` face rectangles in *img* coordinates.

    Downsamples to 800 px wide before detection for speed; the rectangles
    are scaled back to the original image size before returning.

    Returns ``[]`` if no faces are found or if OpenCV is not available.
    """
    try:
        import cv2          # type: ignore
        import numpy as np  # type: ignore

        # Downsample — detection is still reliable at this resolution
        scale = min(1.0, 800 / max(img.width, img.height))
        small = img.resize(
            (int(img.width * scale), int(img.height * scale)),
            Image.Resampling.LANCZOS,
        )
        gray = cv2.cvtColor(np.array(small.convert("RGB")), cv2.COLOR_RGB2GRAY)

        cascade = _get_cascade()
        faces = cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30),
        )

        if len(faces) == 0:
            return []

        # Scale rectangles back to original image coordinates
        return [
            (
                int(x / scale),
                int(y / scale),
                int(w / scale),
                int(h / scale),
            )
            for x, y, w, h in faces
        ]

    except Exception:
        return []


def face_aware_crop(
    img: Image.Image,
    target_w: int,
    target_h: int,
    face_rects: List[Tuple[int, int, int, int]],
) -> Image.Image:
    """
    Crop *img* to ``target_w × target_h``, shifting the crop window towards
    the centroid of the detected faces so that heads are not cut off.

    Falls back to a plain centred crop when *face_rects* is empty.
    """
    if not face_rects:
        return ImageOps.fit(img, (target_w, target_h), Image.Resampling.LANCZOS)

    # Centroid of all face bounding boxes (in original image space)
    cx = sum(x + w // 2 for x, y, w, h in face_rects) // len(face_rects)
    cy = sum(y + h // 2 for x, y, w, h in face_rects) // len(face_rects)

    # Scale the image so it covers the target size
    scale     = max(target_w / img.width, target_h / img.height)
    scaled_w  = int(img.width  * scale)
    scaled_h  = int(img.height * scale)
    scaled    = img.resize((scaled_w, scaled_h), Image.Resampling.LANCZOS)

    # Map face centroid into scaled image space
    cx_s = int(cx * scale)
    cy_s = int(cy * scale)

    # Clamp the crop box so it stays fully within the scaled image
    left = max(0, min(cx_s - target_w // 2, scaled_w - target_w))
    top  = max(0, min(cy_s - target_h // 2, scaled_h - target_h))

    return scaled.crop((left, top, left + target_w, top + target_h))
