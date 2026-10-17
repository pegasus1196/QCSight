"""
Main inspection orchestrator.
Runs all CV checks against the cabinet photo and reference documents,
produces CheckResult verdicts following the precision-first policy:
uncertain → UNREADABLE, never a false FAIL.
"""
import cv2
import numpy as np
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .feature_extractor import FeatureExtractor, DeviceDetector, DetectedRegion
from .ocr_reader import CabinetOCR, OCRResult
from .image_registration import ImageRegistrar, RegistrationResult
from .color_analyzer import WireColorAnalyzer, ColorDetection
from ..models.schemas import CheckResult, Verdict, InspectionResponse


class CabinetInspector:
    def __init__(self, confidence_threshold: float = 0.72):
        self.confidence_threshold = confidence_threshold
        self.feature_extractor = FeatureExtractor(method="orb", n_features=2000)
        self.device_detector = DeviceDetector()
        self.ocr = CabinetOCR()
        self.registrar = ImageRegistrar()
        self.color_analyzer = WireColorAnalyzer()

    def inspect(
        self,
        photo: np.ndarray,
        reference: np.ndarray | None = None,
        checks: list[str] | None = None,
        project_name: str = "Control cabinet QC",
        photo_filename: str = "cabinet.jpg",
        expected_devices: list[dict] | None = None,
        expected_labels: list[dict] | None = None,
        expected_ferrules: list[dict] | None = None,
        expected_wire_colors: list[dict] | None = None,
    ) -> InspectionResponse:
        if checks is None:
            checks = ["presence", "labels", "ferrules", "alignment", "colour"]

        rectified = self.registrar.rectify_perspective(photo)

        alignment_score = None
        aligned = rectified
        if reference is not None and "alignment" in checks:
            reg_result = self.registrar.register(rectified, reference)
            alignment_score = reg_result.score
            if reg_result.aligned_image is not None:
                aligned = reg_result.aligned_image

        detected_regions = self.device_detector.find_device_contours(aligned)
        ocr_results = self.ocr.read_text(aligned)

        results: list[CheckResult] = []
        check_idx = {}

        has_expected = expected_devices or expected_labels or expected_ferrules

        if not has_expected:
            auto_devices, auto_labels, auto_ferrules = self._derive_expected_from_ocr(ocr_results)
            if not expected_devices:
                expected_devices = auto_devices
            if not expected_labels:
                expected_labels = auto_labels
            if not expected_ferrules:
                expected_ferrules = auto_ferrules

        if "presence" in checks and expected_devices:
            presence_results = self._check_presence(
                aligned, detected_regions, ocr_results, expected_devices,
            )
            check_idx["presence"] = len(results)
            results.extend(presence_results)

        if "labels" in checks and expected_labels:
            label_results = self._check_labels(
                aligned, ocr_results, expected_labels,
            )
            check_idx["labels"] = len(results)
            results.extend(label_results)

        if "ferrules" in checks and expected_ferrules:
            ferrule_results = self._check_ferrules(
                aligned, ocr_results, detected_regions, expected_ferrules,
            )
            check_idx["ferrules"] = len(results)
            results.extend(ferrule_results)

        if "alignment" in checks:
            alignment_result = self._check_alignment(alignment_score, reference is not None)
            results.append(alignment_result)

        if "colour" in checks and expected_wire_colors:
            colour_results = self._check_wire_colours(
                aligned, expected_wire_colors,
            )
            results.extend(colour_results)

        for i, r in enumerate(results):
            r.id = f"{r.id.split('-')[0]}-{i}" if "-" in r.id else f"{r.id}-{i}"
            if r.status in (Verdict.FAIL, Verdict.UNREADABLE) and not r.suggestion:
                r.suggestion = self._generate_suggestion(r)

        run_id = f"CS-{datetime.now(timezone.utc).strftime('%y%m%d')}-{uuid.uuid4().hex[:4].upper()}"

        return InspectionResponse(
            run_id=run_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            project=project_name,
            photo_file=photo_filename,
            checks_run=checks,
            confidence_threshold=self.confidence_threshold,
            results=results,
            alignment_score=alignment_score,
        )

    def _verdict(self, confidence: float) -> Verdict:
        if confidence >= self.confidence_threshold:
            return Verdict.PASS
        if confidence >= self.confidence_threshold * 0.6:
            return Verdict.UNREADABLE
        return Verdict.FAIL

    def _region_to_box(self, region: DetectedRegion, img_shape: tuple) -> list[float]:
        h, w = img_shape[:2]
        return [
            round(region.x / w * 100, 1),
            round(region.y / h * 100, 1),
            round(region.w / w * 100, 1),
            round(region.h / h * 100, 1),
        ]

    def _check_presence(
        self,
        image: np.ndarray,
        detected_regions: list[DetectedRegion],
        ocr_results: list[OCRResult],
        expected: list[dict],
    ) -> list[CheckResult]:
        results = []
        h, w = image.shape[:2]

        ocr_texts = [(r.text.upper(), r) for r in ocr_results]

        for exp in expected:
            device_name = exp["name"]
            device_id = exp.get("id", device_name)
            search_text = device_id.upper()

            found = False
            best_ocr = None
            best_score = 0

            for text, ocr_r in ocr_texts:
                match, score = self.ocr.fuzzy_match(text, search_text, threshold=80)
                if score > best_score:
                    best_score = score
                    best_ocr = ocr_r
                    if match:
                        found = True

            if found and best_ocr:
                bx, by, bw, bh = best_ocr.bbox
                box = [
                    round(bx / w * 100, 1), round(by / h * 100, 1),
                    round(bw / w * 100, 1), round(bh / h * 100, 1),
                ]
                confidence = best_ocr.confidence
                verdict = Verdict.PASS if confidence >= self.confidence_threshold else Verdict.UNREADABLE
                results.append(CheckResult(
                    id=f"presence-{len(results)}", check="Device presence",
                    name=device_name, expected="Installed", found=f"Found: {best_ocr.text}",
                    status=verdict, confidence=confidence, box=box,
                    detail=f"Device {device_id} detected via OCR with {confidence:.0%} confidence.",
                ))
            else:
                matched_region = self._find_region_for_device(
                    image, detected_regions, exp, ocr_results
                )
                if matched_region:
                    box = self._region_to_box(matched_region, image.shape)
                    conf = matched_region.confidence * 0.7
                    verdict = Verdict.UNREADABLE if conf < self.confidence_threshold else Verdict.PASS
                    results.append(CheckResult(
                        id=f"presence-{len(results)}", check="Device presence",
                        name=device_name, expected="Installed",
                        found=f"Component detected (shape match, label unclear)",
                        status=verdict, confidence=conf, box=box,
                        detail=f"A component was detected at this location by shape, but the label could not be confirmed.",
                    ))
                else:
                    has_partial = best_score >= 40
                    if has_partial and best_ocr:
                        bx, by, bw, bh = best_ocr.bbox
                        box = [
                            round(bx / w * 100, 1), round(by / h * 100, 1),
                            round(bw / w * 100, 1), round(bh / h * 100, 1),
                        ]
                        results.append(CheckResult(
                            id=f"presence-{len(results)}", check="Device presence",
                            name=device_name, expected="Installed",
                            found=f"Possible: {best_ocr.text} ({best_score}% match)",
                            status=Verdict.UNREADABLE, confidence=best_score / 100,
                            box=box,
                            detail=f"Text '{best_ocr.text}' partially matches '{device_id}' but confidence is too low.",
                        ))
                    else:
                        results.append(CheckResult(
                            id=f"presence-{len(results)}", check="Device presence",
                            name=device_name, expected="Installed",
                            found="Not readable – retake a close-up",
                            status=Verdict.UNREADABLE, confidence=None,
                            detail=f"Device {device_id} could not be located in the cabinet photo. The item may be present but not visible — retake with better angle or lighting.",
                        ))

        return results

    def _find_region_for_device(
        self,
        image: np.ndarray,
        regions: list[DetectedRegion],
        expected: dict,
        ocr_results: list[OCRResult],
    ) -> DetectedRegion | None:
        exp_area = expected.get("expected_area")
        if not exp_area:
            return None

        ex, ey, ew, eh = exp_area
        h, w = image.shape[:2]
        target_x = int(ex / 100 * w)
        target_y = int(ey / 100 * h)

        best = None
        best_dist = float("inf")

        for region in regions:
            cx = region.x + region.w / 2
            cy = region.y + region.h / 2
            dist = ((cx - target_x) ** 2 + (cy - target_y) ** 2) ** 0.5
            if dist < best_dist:
                best_dist = dist
                best = region

        if best and best_dist < max(w, h) * 0.15:
            return best
        return None

    def _check_labels(
        self, image: np.ndarray, ocr_results: list[OCRResult], expected: list[dict]
    ) -> list[CheckResult]:
        results = []
        h, w = image.shape[:2]

        for exp in expected:
            label = exp["label"]
            best_match = None
            best_score = 0
            matched = False
            for ocr_r in ocr_results:
                is_match, score = self.ocr.fuzzy_match(ocr_r.text, label, threshold=80)
                if score > best_score:
                    best_score = score
                    best_match = ocr_r
                    if is_match:
                        matched = True
            result_ocr = best_match

            if matched and result_ocr:
                bx, by, bw, bh = result_ocr.bbox
                box = [
                    round(bx / w * 100, 1), round(by / h * 100, 1),
                    round(bw / w * 100, 1), round(bh / h * 100, 1),
                ]
                conf = result_ocr.confidence
                verdict = Verdict.PASS if conf >= self.confidence_threshold else Verdict.UNREADABLE
                results.append(CheckResult(
                    id=f"labels-{len(results)}", check="Device labels",
                    name=f"{exp.get('device', 'Device')} label", expected=label,
                    found=result_ocr.text, status=verdict, confidence=conf, box=box,
                    detail=f"Label '{result_ocr.text}' found with {conf:.0%} confidence.",
                ))
            elif result_ocr:
                bx, by, bw, bh = result_ocr.bbox
                box = [
                    round(bx / w * 100, 1), round(by / h * 100, 1),
                    round(bw / w * 100, 1), round(bh / h * 100, 1),
                ]
                if result_ocr.confidence < 0.4:
                    verdict = Verdict.UNREADABLE
                    found_text = f"Read: '{result_ocr.text}' (low confidence)"
                    detail = f"OCR read '{result_ocr.text}' but confidence is too low ({result_ocr.confidence:.0%}) to confirm a mismatch."
                else:
                    verdict = Verdict.FAIL
                    found_text = f"Read: '{result_ocr.text}' (mismatch)"
                    detail = f"Expected label '{label}' but OCR read '{result_ocr.text}'."
                results.append(CheckResult(
                    id=f"labels-{len(results)}", check="Device labels",
                    name=f"{exp.get('device', 'Device')} label", expected=label,
                    found=found_text,
                    status=verdict, confidence=result_ocr.confidence, box=box,
                    detail=detail,
                ))
            else:
                has_nearby_text = any(
                    self.ocr.fuzzy_match(ocr_r.text, label, threshold=40)[1] >= 30
                    for ocr_r in ocr_results
                )
                results.append(CheckResult(
                    id=f"labels-{len(results)}", check="Device labels",
                    name=f"{exp.get('device', 'Device')} label", expected=label,
                    found="Not readable – retake a close-up",
                    status=Verdict.UNREADABLE, confidence=None,
                    detail=f"No readable label found for expected '{label}'. Retake a close-up with better lighting.",
                ))

        return results

    def _check_ferrules(
        self, image: np.ndarray, ocr_results: list[OCRResult],
        detected_regions: list[DetectedRegion], expected: list[dict]
    ) -> list[CheckResult]:
        results = []
        h, w = image.shape[:2]

        for exp in expected:
            ferrule_id = exp["id"]

            best_match = None
            best_score = 0
            matched = False
            for ocr_r in ocr_results:
                is_match, score = self.ocr.fuzzy_match(ocr_r.text, ferrule_id, threshold=65)
                if score > best_score:
                    best_score = score
                    best_match = ocr_r
                    if is_match:
                        matched = True

            if matched and best_match:
                bx, by, bw, bh = best_match.bbox
                box = [
                    round(bx / w * 100, 1), round(by / h * 100, 1),
                    round(bw / w * 100, 1), round(bh / h * 100, 1),
                ]
                results.append(CheckResult(
                    id=f"ferrules-{len(results)}", check="Wire ferrules",
                    name=f"Ferrule on {ferrule_id}", expected="Ferrule fitted",
                    found=f"Ferrule: {best_match.text}", status=Verdict.PASS,
                    confidence=best_match.confidence, box=box,
                    detail=f"Ferrule marking '{best_match.text}' matches expected '{ferrule_id}'.",
                ))
            elif best_match and best_score >= 40:
                bx, by, bw, bh = best_match.bbox
                box = [
                    round(bx / w * 100, 1), round(by / h * 100, 1),
                    round(bw / w * 100, 1), round(bh / h * 100, 1),
                ]
                verdict = Verdict.UNREADABLE if best_match.confidence < self.confidence_threshold else Verdict.FAIL
                results.append(CheckResult(
                    id=f"ferrules-{len(results)}", check="Wire ferrules",
                    name=f"Ferrule on {ferrule_id}", expected="Ferrule fitted",
                    found=f"Read: '{best_match.text}' (partial match)",
                    status=verdict, confidence=best_match.confidence, box=box,
                    detail=f"Ferrule text '{best_match.text}' partially matches '{ferrule_id}' ({best_score}%).",
                ))
            else:
                results.append(CheckResult(
                    id=f"ferrules-{len(results)}", check="Wire ferrules",
                    name=f"Ferrule on {ferrule_id}", expected="Ferrule fitted",
                    found="Not readable – retake a close-up",
                    status=Verdict.UNREADABLE, confidence=None,
                    detail=f"No ferrule marking found for {ferrule_id}. The ferrule may be present but not readable — retake a close-up.",
                ))

        return results

    def _check_alignment(self, score: float | None, has_reference: bool) -> CheckResult:
        if not has_reference:
            return CheckResult(
                id="alignment-0", check="Photo alignment",
                name="Photo to GA registration",
                expected="Cabinet layout aligned to GA",
                found="No reference drawing provided",
                status=Verdict.NOT_AUTOMATED, confidence=0.0,
                detail="Upload a GA drawing PDF to enable alignment checking.",
            )

        if score is None:
            score = 0.0

        if score >= 0.7:
            return CheckResult(
                id="alignment-0", check="Photo alignment",
                name="Photo to GA registration",
                expected="Cabinet layout aligned to GA",
                found=f"Alignment established · {score:.0%}",
                status=Verdict.PASS, confidence=score,
                detail=f"Photo-to-drawing alignment score: {score:.0%}. Registration successful.",
            )
        elif score >= 0.4:
            return CheckResult(
                id="alignment-0", check="Photo alignment",
                name="Photo to GA registration",
                expected="Cabinet layout aligned to GA",
                found=f"Partial alignment · {score:.0%}",
                status=Verdict.UNREADABLE, confidence=score,
                detail=f"Alignment score {score:.0%} is below threshold. Photo angle or quality may need improvement.",
            )
        else:
            return CheckResult(
                id="alignment-0", check="Photo alignment",
                name="Photo to GA registration",
                expected="Cabinet layout aligned to GA",
                found=f"Could not align photo to drawing · {score:.0%}",
                status=Verdict.UNREADABLE, confidence=score,
                detail="Retake a front-on photo with even lighting and the full cabinet in frame.",
            )

    def _check_wire_colours(
        self, image: np.ndarray, expected: list[dict]
    ) -> list[CheckResult]:
        results = []
        h, w = image.shape[:2]

        all_regions = self.color_analyzer.detect_wire_regions(image)
        wire_regions = [
            r for r in all_regions
            if r[1] > h * 0.3 and r[3] > 30
        ]

        for i, exp in enumerate(expected):
            wire_name = exp["name"]
            expected_color = exp["color"]
            region = exp.get("region")

            if region:
                rx, ry, rw, rh = [int(v / 100 * dim) for v, dim in zip(region, [w, h, w, h])]
            elif i < len(wire_regions):
                rx, ry, rw, rh = wire_regions[i]
                pad = 5
                rx = max(0, rx - pad)
                ry = max(0, ry - pad)
                rw = min(w - rx, rw + 2 * pad)
                rh = min(h - ry, rh + 2 * pad)
            else:
                rx, ry, rw, rh = 0, int(h * 0.3), w, int(h * 0.5)

            detection = self.color_analyzer.check_wire_color(
                image, (rx, ry, rw, rh), expected_color
            )

            box = [
                round(rx / w * 100, 1), round(ry / h * 100, 1),
                round(rw / w * 100, 1), round(rh / h * 100, 1),
            ]

            if detection and detection.color_name.lower() == expected_color.lower():
                results.append(CheckResult(
                    id=f"colour-{len(results)}", check="Wire colour",
                    name=wire_name, expected=expected_color.capitalize(),
                    found=detection.color_name.capitalize(),
                    status=Verdict.PASS, confidence=detection.confidence, box=box,
                    detail=f"Wire color matches: expected {expected_color}, found {detection.color_name}.",
                ))
            elif detection:
                conf = detection.confidence
                verdict = Verdict.UNREADABLE if conf < self.confidence_threshold else Verdict.FAIL
                results.append(CheckResult(
                    id=f"colour-{len(results)}", check="Wire colour",
                    name=wire_name, expected=expected_color.capitalize(),
                    found=detection.color_name.capitalize(),
                    status=verdict, confidence=conf, box=box,
                    detail=f"Expected {expected_color} wire but dominant color is {detection.color_name}.",
                ))
            else:
                results.append(CheckResult(
                    id=f"colour-{len(results)}", check="Wire colour",
                    name=wire_name, expected=expected_color.capitalize(),
                    found="Unable to determine",
                    status=Verdict.UNREADABLE, confidence=0.3, box=box,
                    detail=f"Could not extract wire color in the specified region.",
                ))

        return results

    def _derive_expected_from_ocr(self, ocr_results: list[OCRResult]):
        skip_words = {"terminal", "block", "wiring", "din", "rail", "panel", "power",
                      "distribution", "motor", "control", "cabinet", "automation",
                      "lighting", "hvac", "the", "and"}
        devices = []
        labels = []
        ferrules = []
        for r in ocr_results:
            text = r.text.strip()
            if len(text) < 2 or len(text) > 12:
                continue
            words = text.lower().split()
            if any(w in skip_words for w in words):
                continue
            if " " in text and len(text) > 8:
                continue
            devices.append({"name": f"Detected: {text}", "id": text})
            labels.append({"device": f"Component {text}", "label": text})
            if "-" in text and len(text) <= 8:
                ferrules.append({"id": text})
        return devices, labels, ferrules

    def _default_expected_colours(self) -> list[dict]:
        return [
            {"name": "24 VDC positive", "color": "red", "region": [60, 70, 30, 15]},
            {"name": "Neutral", "color": "blue", "region": [60, 80, 30, 15]},
        ]

    def _generate_suggestion(self, result: CheckResult) -> str:
        check = result.check.lower()
        name = result.name
        expected = result.expected
        found = result.found

        if "presence" in check:
            if "missing" in found.lower():
                return (
                    f"Install {name} in the position indicated on the GA drawing. "
                    f"Secure the DIN rail clip and verify all wiring connections match "
                    f"the wire list before re-checking."
                )
            if "swap" in found.lower() or "order" in result.detail.lower() if result.detail else False:
                return (
                    f"De-energise the panel and reposition the components to match the "
                    f"expected order: {expected}. Re-land all wires per the wire list "
                    f"after repositioning."
                )
            return (
                f"Verify {name} is correctly installed and its label is visible. "
                f"Clean the label surface and retake the photo with better lighting if needed."
            )

        if "label" in check:
            if "no label" in found.lower() or "not detected" in found.lower():
                return (
                    f"Print and attach label \"{expected}\" to the device using an approved "
                    f"label printer (e.g. Brady BMP21). Use high-contrast tape to ensure "
                    f"readability during re-check."
                )
            raw = found.split(":", 1)[-1].strip() if ":" in found else found
            actual = raw.strip("' ").replace(" (mismatch)", "")
            return (
                f'The current label reads "{actual}" but '
                f'expected "{expected}". Remove the incorrect label and apply the correct one. '
                f"Ensure it is flat, unobstructed, and facing the camera."
            )

        if "ferrule" in check:
            if "no ferrule" in found.lower() or "not detected" in found.lower():
                return (
                    f"Strip 8 mm of insulation from the wire and crimp a printed ferrule "
                    f"sleeve marked with the correct ID using the appropriate crimping tool. "
                    f"Ensure the marking faces outward for OCR readability."
                )
            return (
                f"The ferrule marking does not match the expected ID. Replace the ferrule "
                f"with one printed \"{expected.split(':')[-1].strip()}\" and ensure it is "
                f"correctly crimped and legible."
            )

        if "alignment" in check:
            return (
                "Retake the cabinet photo ensuring: (1) camera is centred and perpendicular "
                "to the panel, (2) the full cabinet is in frame with minimal perspective "
                "distortion, (3) lighting is even with no glare or shadows."
            )

        if "colour" in check:
            return (
                f"Wire colour mismatch: expected {expected} but found {found}. "
                f"Verify the wire against the IEC 60445 colour code and the wire list. "
                f"If incorrect, replace the wire with the correct colour and re-terminate."
            )

        return (
            f"Review {name} against the design documents and correct to match "
            f"the expected value: \"{expected}\". Re-check after applying the fix."
        )
