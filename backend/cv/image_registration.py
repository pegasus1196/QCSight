"""
Image registration / alignment module.
Aligns cabinet photo to GA drawing using feature-based homography —
same approach as face alignment in recognition pipelines:
detect keypoints → match → RANSAC homography → warp.
"""
import cv2
import numpy as np
from dataclasses import dataclass
from .feature_extractor import FeatureExtractor, FeatureMatch


@dataclass
class RegistrationResult:
    aligned_image: np.ndarray | None
    homography: np.ndarray | None
    score: float  # 0-1, how well the images align
    inlier_count: int
    total_matches: int
    method: str


class ImageRegistrar:
    def __init__(self):
        self.orb_extractor = FeatureExtractor(method="orb", n_features=2000)
        self.sift_extractor = FeatureExtractor(method="sift", n_features=2000)

    def register(
        self, photo: np.ndarray, reference: np.ndarray, method: str = "auto"
    ) -> RegistrationResult:
        if method == "auto":
            result_orb = self._register_with(self.orb_extractor, photo, reference, "orb")
            result_sift = self._register_with(self.sift_extractor, photo, reference, "sift")
            return result_orb if result_orb.score >= result_sift.score else result_sift

        extractor = self.orb_extractor if method == "orb" else self.sift_extractor
        return self._register_with(extractor, photo, reference, method)

    def _register_with(
        self, extractor: FeatureExtractor, photo: np.ndarray, reference: np.ndarray, method: str
    ) -> RegistrationResult:
        match = extractor.match_images(photo, reference)

        if match.homography is None:
            return RegistrationResult(
                aligned_image=None, homography=None,
                score=0.0, inlier_count=0,
                total_matches=len(match.good_matches), method=method,
            )

        h, w = reference.shape[:2]
        aligned = cv2.warpPerspective(photo, match.homography, (w, h))

        inliers = int(match.inlier_mask.sum()) if match.inlier_mask is not None else 0
        score = self._compute_alignment_score(aligned, reference, match.match_ratio, inliers)

        return RegistrationResult(
            aligned_image=aligned, homography=match.homography,
            score=score, inlier_count=inliers,
            total_matches=len(match.good_matches), method=method,
        )

    def _compute_alignment_score(
        self, aligned: np.ndarray, reference: np.ndarray, match_ratio: float, inliers: int
    ) -> float:
        gray_a = cv2.cvtColor(aligned, cv2.COLOR_BGR2GRAY) if len(aligned.shape) == 3 else aligned
        gray_r = cv2.cvtColor(reference, cv2.COLOR_BGR2GRAY) if len(reference.shape) == 3 else reference

        if gray_a.shape != gray_r.shape:
            gray_a = cv2.resize(gray_a, (gray_r.shape[1], gray_r.shape[0]))

        ssim_score = self._structural_similarity(gray_a, gray_r)

        hist_a = cv2.calcHist([gray_a], [0], None, [256], [0, 256])
        hist_r = cv2.calcHist([gray_r], [0], None, [256], [0, 256])
        cv2.normalize(hist_a, hist_a)
        cv2.normalize(hist_r, hist_r)
        hist_corr = cv2.compareHist(hist_a, hist_r, cv2.HISTCMP_CORREL)

        inlier_score = min(inliers / 50.0, 1.0)

        score = 0.4 * match_ratio + 0.3 * max(ssim_score, 0) + 0.2 * max(hist_corr, 0) + 0.1 * inlier_score
        return min(max(score, 0.0), 1.0)

    def _structural_similarity(self, img1: np.ndarray, img2: np.ndarray) -> float:
        C1 = (0.01 * 255) ** 2
        C2 = (0.03 * 255) ** 2

        img1 = img1.astype(np.float64)
        img2 = img2.astype(np.float64)

        mu1 = cv2.GaussianBlur(img1, (11, 11), 1.5)
        mu2 = cv2.GaussianBlur(img2, (11, 11), 1.5)

        mu1_sq = mu1 ** 2
        mu2_sq = mu2 ** 2
        mu1_mu2 = mu1 * mu2

        sigma1_sq = cv2.GaussianBlur(img1 ** 2, (11, 11), 1.5) - mu1_sq
        sigma2_sq = cv2.GaussianBlur(img2 ** 2, (11, 11), 1.5) - mu2_sq
        sigma12 = cv2.GaussianBlur(img1 * img2, (11, 11), 1.5) - mu1_mu2

        ssim_map = ((2 * mu1_mu2 + C1) * (2 * sigma12 + C2)) / (
            (mu1_sq + mu2_sq + C1) * (sigma1_sq + sigma2_sq + C2)
        )
        return float(ssim_map.mean())

    def rectify_perspective(self, image: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        edges = cv2.Canny(gray, 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, 100, minLineLength=100, maxLineGap=10)

        if lines is None or len(lines) < 4:
            return image

        angles = []
        for line in lines:
            pts = line.flatten()
            x1, y1, x2, y2 = pts[0], pts[1], pts[2], pts[3]
            angle = np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi
            angles.append(angle)

        horizontal = [a for a in angles if abs(a) < 15 or abs(a) > 165]
        if horizontal:
            median_angle = np.median(horizontal)
            if abs(median_angle) > 0.5:
                h, w = image.shape[:2]
                center = (w / 2, h / 2)
                M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
                return cv2.warpAffine(image, M, (w, h), borderMode=cv2.BORDER_REPLICATE)

        return image
