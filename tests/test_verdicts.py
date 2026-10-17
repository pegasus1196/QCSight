"""
Verify the no-false-FAIL policy:
- nothing detected → UNREADABLE (not FAIL)
- low OCR confidence → UNREADABLE (not FAIL)
- low alignment score → UNREADABLE (not FAIL)
- confident wrong label → FAIL
"""
import numpy as np
import pytest
from unittest.mock import patch, MagicMock

from backend.cv.inspector import CabinetInspector
from backend.cv.ocr_reader import OCRResult
from backend.models.schemas import Verdict


@pytest.fixture
def inspector():
    return CabinetInspector(confidence_threshold=0.72)


@pytest.fixture
def blank_image():
    return np.zeros((480, 640, 3), dtype=np.uint8)


class TestNothingDetected:
    """When no text or region is found, verdict must be UNREADABLE, not FAIL."""

    def test_presence_not_found_is_unreadable(self, inspector, blank_image):
        results = inspector._check_presence(
            blank_image,
            detected_regions=[],
            ocr_results=[],
            expected=[{"name": "Breaker CB1", "id": "CB1"}],
        )
        assert len(results) == 1
        assert results[0].status == Verdict.UNREADABLE

    def test_label_not_found_is_unreadable(self, inspector, blank_image):
        results = inspector._check_labels(
            blank_image,
            ocr_results=[],
            expected=[{"device": "Relay K1", "label": "K1"}],
        )
        assert len(results) == 1
        assert results[0].status == Verdict.UNREADABLE

    def test_ferrule_not_found_is_unreadable(self, inspector, blank_image):
        results = inspector._check_ferrules(
            blank_image,
            ocr_results=[],
            detected_regions=[],
            expected=[{"id": "X3"}],
        )
        assert len(results) == 1
        assert results[0].status == Verdict.UNREADABLE


class TestLowOCRConfidence:
    """Low-confidence OCR reads must not become FAIL."""

    def test_low_confidence_mismatch_is_unreadable(self, inspector, blank_image):
        low_conf_ocr = OCRResult(
            text="XYZ", confidence=0.25, bbox=(100, 100, 50, 20)
        )
        results = inspector._check_labels(
            blank_image,
            ocr_results=[low_conf_ocr],
            expected=[{"device": "Relay", "label": "K1"}],
        )
        assert len(results) == 1
        assert results[0].status == Verdict.UNREADABLE


class TestLowAlignmentScore:
    """A poor alignment score must be UNREADABLE, not FAIL."""

    def test_low_alignment_is_unreadable(self, inspector):
        result = inspector._check_alignment(score=0.15, has_reference=True)
        assert result.status == Verdict.UNREADABLE
        assert result.confidence == 0.15


class TestConfidentWrongLabel:
    """A high-confidence read that contradicts the expected label IS a real FAIL."""

    def test_confident_mismatch_is_fail(self, inspector, blank_image):
        high_conf_ocr = OCRResult(
            text="CB2", confidence=0.95, bbox=(100, 100, 80, 20)
        )
        results = inspector._check_labels(
            blank_image,
            ocr_results=[high_conf_ocr],
            expected=[{"device": "Breaker", "label": "CB1"}],
        )
        assert len(results) == 1
        assert results[0].status == Verdict.FAIL
