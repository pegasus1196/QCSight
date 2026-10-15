"""
Wire color analysis using HSV histograms and k-means clustering.
Detects wire colors in cabinet regions and matches against expected color codes.
"""
import cv2
import numpy as np
from dataclasses import dataclass
from sklearn.cluster import KMeans


# IEC 60445 standard wire colors for industrial cabinets
WIRE_COLORS = {
    "red":    {"hsv_low": (0, 100, 100),   "hsv_high": (10, 255, 255),  "hsv_low2": (170, 100, 100), "hsv_high2": (180, 255, 255)},
    "blue":   {"hsv_low": (100, 100, 80),  "hsv_high": (130, 255, 255)},
    "green":  {"hsv_low": (35, 80, 80),    "hsv_high": (85, 255, 255)},
    "yellow": {"hsv_low": (20, 100, 100),  "hsv_high": (35, 255, 255)},
    "black":  {"hsv_low": (0, 0, 0),       "hsv_high": (180, 100, 50)},
    "white":  {"hsv_low": (0, 0, 200),     "hsv_high": (180, 30, 255)},
    "brown":  {"hsv_low": (10, 100, 50),   "hsv_high": (20, 255, 200)},
    "orange": {"hsv_low": (10, 150, 150),  "hsv_high": (25, 255, 255)},
    "grey":   {"hsv_low": (0, 0, 80),      "hsv_high": (180, 50, 180)},
}


@dataclass
class ColorDetection:
    color_name: str
    confidence: float
    pixel_ratio: float
    dominant_hsv: tuple[float, float, float]
    bbox: tuple[int, int, int, int] | None = None


class WireColorAnalyzer:
    def __init__(self):
        self.colors = WIRE_COLORS

    def detect_dominant_colors(self, image: np.ndarray, n_colors: int = 3) -> list[ColorDetection]:
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        pixels = hsv.reshape(-1, 3).astype(np.float32)

        if len(pixels) < n_colors:
            return []

        kmeans = KMeans(n_clusters=min(n_colors, len(pixels)), random_state=42, n_init=10)
        kmeans.fit(pixels)

        centers = kmeans.cluster_centers_
        labels = kmeans.labels_
        counts = np.bincount(labels)
        total = len(labels)

        detections = []
        for i, center in enumerate(centers):
            h, s, v = center
            color_name = self._classify_hsv(h, s, v)
            ratio = counts[i] / total
            confidence = self._color_confidence(center, color_name)

            detections.append(ColorDetection(
                color_name=color_name,
                confidence=confidence,
                pixel_ratio=float(ratio),
                dominant_hsv=(float(h), float(s), float(v)),
            ))

        detections.sort(key=lambda d: d.pixel_ratio, reverse=True)
        return detections

    def _classify_hsv(self, h: float, s: float, v: float) -> str:
        if v < 50:
            return "black"
        if s < 30 and v > 200:
            return "white"
        if s < 50 and 80 < v < 200:
            return "grey"

        for name, ranges in self.colors.items():
            if name in ("black", "white", "grey"):
                continue
            low = ranges["hsv_low"]
            high = ranges["hsv_high"]
            if low[0] <= h <= high[0] and low[1] <= s <= high[1] and low[2] <= v <= high[2]:
                return name
            if "hsv_low2" in ranges:
                low2 = ranges["hsv_low2"]
                high2 = ranges["hsv_high2"]
                if low2[0] <= h <= high2[0] and low2[1] <= s <= high2[1] and low2[2] <= v <= high2[2]:
                    return name

        return "unknown"

    def _color_confidence(self, hsv_center: np.ndarray, color_name: str) -> float:
        if color_name == "unknown":
            return 0.3

        if color_name not in self.colors:
            return 0.5

        ranges = self.colors[color_name]
        low = np.array(ranges["hsv_low"], dtype=float)
        high = np.array(ranges["hsv_high"], dtype=float)
        center = (low + high) / 2
        span = (high - low) / 2
        span[span == 0] = 1

        dist = np.abs(hsv_center - center) / span
        normalized = 1.0 - min(np.mean(dist), 1.0)
        return float(max(0.3, normalized))

    def check_wire_color(
        self, image: np.ndarray, region: tuple[int, int, int, int], expected_color: str
    ) -> ColorDetection | None:
        x, y, w, h = region
        ih, iw = image.shape[:2]
        x1 = max(0, x)
        y1 = max(0, y)
        x2 = min(iw, x + w)
        y2 = min(ih, y + h)
        roi = image[y1:y2, x1:x2]

        if roi.size == 0:
            return None

        hsv_mask_result = self._check_color_by_mask(roi, expected_color)
        if hsv_mask_result:
            hsv_mask_result.bbox = (x1, y1, x2 - x1, y2 - y1)
            return hsv_mask_result

        detections = self.detect_dominant_colors(roi, n_colors=3)
        if not detections:
            return None

        for det in detections:
            if det.color_name.lower() == expected_color.lower():
                det.bbox = (x1, y1, x2 - x1, y2 - y1)
                return det

        best = detections[0]
        best.bbox = (x1, y1, x2 - x1, y2 - y1)
        return best

    def _check_color_by_mask(self, roi: np.ndarray, color_name: str) -> ColorDetection | None:
        if color_name.lower() not in self.colors:
            return None

        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        ranges = self.colors[color_name.lower()]
        low = np.array(ranges["hsv_low"])
        high = np.array(ranges["hsv_high"])
        mask = cv2.inRange(hsv, low, high)
        if "hsv_low2" in ranges:
            low2 = np.array(ranges["hsv_low2"])
            high2 = np.array(ranges["hsv_high2"])
            mask = mask | cv2.inRange(hsv, low2, high2)

        total_pixels = roi.shape[0] * roi.shape[1]
        color_pixels = cv2.countNonZero(mask)
        ratio = color_pixels / max(total_pixels, 1)

        if ratio > 0.05:
            masked_hsv = hsv[mask > 0]
            mean_hsv = masked_hsv.mean(axis=0) if len(masked_hsv) > 0 else (0, 0, 0)
            confidence = min(0.95, 0.5 + ratio)
            return ColorDetection(
                color_name=color_name.lower(),
                confidence=confidence,
                pixel_ratio=float(ratio),
                dominant_hsv=(float(mean_hsv[0]), float(mean_hsv[1]), float(mean_hsv[2])),
            )
        return None

    def detect_wire_regions(self, image: np.ndarray) -> list[tuple[int, int, int, int]]:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        ih, iw = image.shape[:2]
        wire_regions = []

        edges = cv2.Canny(gray, 30, 100)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 5))
        edges = cv2.dilate(edges, kernel, iterations=2)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            aspect = h / max(w, 1)
            if aspect > 1.5 and h > 20:
                wire_regions.append((x, y, w, h))

        if not wire_regions:
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            sat_mask = hsv[:, :, 1] > 80
            val_low_mask = hsv[:, :, 2] < 60
            color_mask = (sat_mask | val_low_mask).astype(np.uint8) * 255
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
            color_mask = cv2.morphologyEx(color_mask, cv2.MORPH_CLOSE, kernel, iterations=2)
            contours2, _ = cv2.findContours(color_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for cnt in contours2:
                x, y, w, h = cv2.boundingRect(cnt)
                area = w * h
                if area > 200 and h > 15:
                    wire_regions.append((x, y, w, h))

        wire_regions.sort(key=lambda r: r[0])
        return wire_regions
