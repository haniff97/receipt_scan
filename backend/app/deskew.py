"""Auto-deskew: detect the receipt in a photo, straighten it, and perspective-crop
it into a clean top-down document image (the 'document scanner' look)."""

import cv2
import numpy as np


def order_corners(pts):
    """Order 4 corner points as [top-left, top-right, bottom-right, bottom-left]."""
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect


def detect_document(image):
    """Find the largest quadrilateral (the receipt) in a photo.

    Returns the 4 ordered corners, or None if nothing reliable was found.
    """
    h, w = image.shape[:2]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Downscale for faster + more robust contour detection
    scale = 600.0 / max(w, h)
    small = cv2.resize(gray, (int(w * scale), int(h * scale)))

    blurred = cv2.GaussianBlur(small, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)

    # Close gaps so the receipt outline is one solid contour
    kernel = np.ones((5, 5), np.uint8)
    closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:5]

    for cnt in contours:
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
        if len(approx) == 4 and cv2.contourArea(cnt) > 0.2 * small.shape[0] * small.shape[1]:
            corners = approx.reshape(4, 2).astype("float32") / scale
            return order_corners(corners)

    return None


def deskew(image):
    """Straighten and crop a receipt photo. Returns the corrected image.

    If no document is detected, returns the original image unchanged so OCR still runs.
    """
    corners = detect_document(image)
    if corners is None:
        return image

    h, w = image.shape[:2]
    tl, tr, br, bl = corners

    width_a = np.linalg.norm(br - bl)
    width_b = np.linalg.norm(tr - tl)
    max_width = max(int(width_a), int(width_b))

    height_a = np.linalg.norm(tr - br)
    height_b = np.linalg.norm(tl - bl)
    max_height = max(int(height_a), int(height_b))

    if max_width < 10 or max_height < 10:
        return image

    dst = np.array(
        [[0, 0], [max_width - 1, 0], [max_width - 1, max_height - 1], [0, max_height - 1]],
        dtype="float32",
    )
    matrix = cv2.getPerspectiveTransform(np.array([tl, tr, br, bl], dtype="float32"), dst)
    return cv2.warpPerspective(image, matrix, (max_width, max_height))
