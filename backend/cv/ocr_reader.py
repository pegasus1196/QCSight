"""
OCR module for reading device labels and ferrule markings.
Uses EasyOCR (deep learning) with pytesseract fallback.
Applies CLAHE enhancement and adaptive thresholding for industrial text.
"""
import cv2
import numpy as np
from dataclasses import dataclass
from rapidfuzz import fuzz

try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False


@dataclass
class OCRResult:
    text: str
    confidence: float
    bbox: tuple[int, int, int, int]  # x, y, w, h
    method: str = "easyocr"


class CabinetOCR:
    def __init__(self, languages: list[str] | None = None):
        self.languages = languages or ["en"]
        self._reader = None

    @property
    def reader(self):
        if self._reader is None and EASYOCR_AVAILABLE:
            try:
                import os
                os.environ.setdefault("PYTHONIOENCODING", "utf-8")
                self._reader = easyocr.Reader(self.languages, gpu=False, verbose=False)
            except Exception:
                self._reader = None
        return self._reader

    def preprocess_for_ocr(self, image: np.ndarray) -> list[np.ndarray]:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)

        _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        adaptive = cv2.adaptiveThreshold(
            enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        inverted = cv2.bitwise_not(binary)

        return [enhanced, binary, adaptive, inverted]

    def read_text(self, image: np.ndarray, min_confidence: float = 0.3) -> list[OCRResult]:
        results = []

        if self.reader is not None:
            results = self._read_easyocr(image, min_confidence)

        if not results and TESSERACT_AVAILABLE:
            results = self._read_tesseract(image, min_confidence)

        if not results:
            preprocessed = self.preprocess_for_ocr(image)
            for variant in preprocessed:
                if self.reader is not None:
                    results = self._read_easyocr(variant, min_confidence)
                elif TESSERACT_AVAILABLE:
                    results = self._read_tesseract(variant, min_confidence)
                if results:
                    break

        return results

    def _read_easyocr(self, image: np.ndarray, min_confidence: float) -> list[OCRResult]:
        if self.reader is None:
            return []

        raw = self.reader.readtext(image)
        results = []
        for bbox_pts, text, conf in raw:
            if conf < min_confidence or not text.strip():
                continue
            pts = np.array(bbox_pts, dtype=int)
            x, y = pts[:, 0].min(), pts[:, 1].min()
            w, h = pts[:, 0].max() - x, pts[:, 1].max() - y
            results.append(OCRResult(
                text=text.strip(), confidence=float(conf),
                bbox=(int(x), int(y), int(w), int(h)), method="easyocr",
            ))
        return results

    def _read_tesseract(self, image: np.ndarray, min_confidence: float) -> list[OCRResult]:
        if not TESSERACT_AVAILABLE:
            return []

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        data = pytesseract.image_to_data(gray, output_type=pytesseract.Output.DICT)
        results = []
        for i, text in enumerate(data["text"]):
            conf = float(data["conf"][i]) / 100.0
            if conf < min_confidence or not text.strip():
                continue
            results.append(OCRResult(
                text=text.strip(), confidence=conf,
                bbox=(data["left"][i], data["top"][i], data["width"][i], data["height"][i]),
                method="tesseract",
            ))
        return results

    def read_region(self, image: np.ndarray, x: int, y: int, w: int, h: int, padding: int = 5) -> list[OCRResult]:
        ih, iw = image.shape[:2]
        x1 = max(0, x - padding)
        y1 = max(0, y - padding)
        x2 = min(iw, x + w + padding)
        y2 = min(ih, y + h + padding)
        roi = image[y1:y2, x1:x2]

        if roi.size == 0:
            return []

        scale = max(1, 64 // min(roi.shape[:2]))
        if scale > 1:
            roi = cv2.resize(roi, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

        results = self.read_text(roi)
        for r in results:
            bx, by, bw, bh = r.bbox
            r.bbox = (
                int(bx / scale + x1), int(by / scale + y1),
                int(bw / scale), int(bh / scale),
            )
        return results

    def fuzzy_match(self, detected: str, expected: str, threshold: int = 70) -> tuple[bool, int]:
        score = fuzz.ratio(detected.upper().strip(), expected.upper().strip())
        return score >= threshold, score

    def find_label(
        self, image: np.ndarray, expected_label: str, threshold: int = 70
    ) -> tuple[OCRResult | None, bool]:
        all_text = self.read_text(image)
        best_match = None
        best_score = 0

        for result in all_text:
            is_match, score = self.fuzzy_match(result.text, expected_label, threshold)
            if score > best_score:
                best_score = score
                best_match = result

        if best_match and best_score >= threshold:
            return best_match, True
        return best_match, False
