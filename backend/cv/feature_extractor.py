"""
Feature extraction using ORB and AKAZE descriptors.
Same keypoint-descriptor-matching paradigm as face recognition (LBPH/eigenfaces).
ORB detects oriented FAST keypoints + BRIEF descriptors;
AKAZE provides more robust non-linear scale-space features.
"""
import cv2
import numpy as np
from dataclasses import dataclass, field


@dataclass
class FeatureMatch:
    query_pts: np.ndarray
    train_pts: np.ndarray
    good_matches: list
    match_ratio: float
    homography: np.ndarray | None = None
    inlier_mask: np.ndarray | None = None


@dataclass
class DetectedRegion:
    x: int
    y: int
    w: int
    h: int
    label: str = ""
    confidence: float = 0.0
    descriptor: np.ndarray | None = field(default=None, repr=False)
    keypoints_count: int = 0


class FeatureExtractor:
    def __init__(self, method: str = "orb", n_features: int = 1000):
        self.method = method.lower()
        if self.method == "orb":
            self.detector = cv2.ORB.create(nfeatures=n_features, scoreType=cv2.ORB_HARRIS_SCORE)
            self.norm = cv2.NORM_HAMMING
        elif self.method == "sift":
            self.detector = cv2.SIFT.create(nfeatures=n_features)
            self.norm = cv2.NORM_L2
        else:
            self.detector = cv2.ORB.create(nfeatures=n_features)
            self.norm = cv2.NORM_HAMMING

        self.matcher = cv2.BFMatcher(self.norm, crossCheck=False)

    def extract(self, image: np.ndarray) -> tuple[list[cv2.KeyPoint], np.ndarray | None]:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        kps, descs = self.detector.detectAndCompute(enhanced, None)
        return kps, descs

    def match_features(
        self, desc1: np.ndarray, desc2: np.ndarray, ratio_thresh: float = 0.75
    ) -> list:
        if desc1 is None or desc2 is None or len(desc1) < 2 or len(desc2) < 2:
            return []
        raw_matches = self.matcher.knnMatch(desc1, desc2, k=2)
        good = []
        for pair in raw_matches:
            if len(pair) == 2:
                m, n = pair
                if m.distance < ratio_thresh * n.distance:
                    good.append(m)
        return good

    def compute_homography(
        self,
        kps1: list[cv2.KeyPoint],
        kps2: list[cv2.KeyPoint],
        good_matches: list,
        min_matches: int = 8,
    ) -> FeatureMatch:
        src_pts = np.float32([kps1[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
        dst_pts = np.float32([kps2[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)

        H, mask = None, None
        if len(good_matches) >= min_matches:
            H, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)

        inliers = int(mask.sum()) if mask is not None else 0
        ratio = inliers / max(len(good_matches), 1)

        return FeatureMatch(
            query_pts=src_pts,
            train_pts=dst_pts,
            good_matches=good_matches,
            match_ratio=ratio,
            homography=H,
            inlier_mask=mask,
        )

    def match_images(
        self, img1: np.ndarray, img2: np.ndarray, ratio_thresh: float = 0.75
    ) -> FeatureMatch:
        kps1, desc1 = self.extract(img1)
        kps2, desc2 = self.extract(img2)
        good = self.match_features(desc1, desc2, ratio_thresh)
        if len(good) < 4:
            return FeatureMatch(
                query_pts=np.array([]),
                train_pts=np.array([]),
                good_matches=good,
                match_ratio=0.0,
            )
        return self.compute_homography(kps1, kps2, good)


class DeviceDetector:
    """Detects individual devices/components in cabinet images using contour analysis
    and feature matching — analogous to face detection bounding boxes."""

    def __init__(self):
        self.extractor = FeatureExtractor(method="orb", n_features=1500)

    def preprocess(self, image: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        return blurred

    def detect_edges(self, image: np.ndarray) -> np.ndarray:
        gray = self.preprocess(image)
        edges = cv2.Canny(gray, 50, 150)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        edges = cv2.dilate(edges, kernel, iterations=2)
        edges = cv2.erode(edges, kernel, iterations=1)
        return edges

    def find_device_contours(
        self, image: np.ndarray, min_area: int = 500, max_area_ratio: float = 0.4
    ) -> list[DetectedRegion]:
        edges = self.detect_edges(image)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        h, w = image.shape[:2]
        max_area = h * w * max_area_ratio
        regions = []

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < min_area or area > max_area:
                continue

            x, y, bw, bh = cv2.boundingRect(cnt)
            aspect = bw / max(bh, 1)
            if aspect < 0.1 or aspect > 10:
                continue

            roi = image[y : y + bh, x : x + bw]
            kps, descs = self.extractor.extract(roi)
            regions.append(
                DetectedRegion(
                    x=x, y=y, w=bw, h=bh,
                    confidence=min(area / max_area * 2, 1.0),
                    descriptor=descs,
                    keypoints_count=len(kps),
                )
            )

        regions.sort(key=lambda r: r.w * r.h, reverse=True)
        return self._non_max_suppression(regions)

    def _non_max_suppression(self, regions: list[DetectedRegion], overlap_thresh: float = 0.5) -> list[DetectedRegion]:
        if not regions:
            return []

        boxes = np.array([[r.x, r.y, r.x + r.w, r.y + r.h] for r in regions], dtype=float)
        x1, y1, x2, y2 = boxes[:, 0], boxes[:, 1], boxes[:, 2], boxes[:, 3]
        areas = (x2 - x1) * (y2 - y1)
        idxs = np.argsort(areas)

        keep = []
        while len(idxs) > 0:
            last = len(idxs) - 1
            i = idxs[last]
            keep.append(i)

            xx1 = np.maximum(x1[i], x1[idxs[:last]])
            yy1 = np.maximum(y1[i], y1[idxs[:last]])
            xx2 = np.minimum(x2[i], x2[idxs[:last]])
            yy2 = np.minimum(y2[i], y2[idxs[:last]])

            inter = np.maximum(0, xx2 - xx1) * np.maximum(0, yy2 - yy1)
            iou = inter / (areas[idxs[:last]] + areas[i] - inter)

            idxs = np.delete(idxs, np.concatenate(([last], np.where(iou > overlap_thresh)[0])))

        return [regions[i] for i in keep]

    def match_template_multi(
        self, image: np.ndarray, template: np.ndarray, threshold: float = 0.6
    ) -> list[DetectedRegion]:
        gray_img = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        gray_tpl = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY) if len(template.shape) == 3 else template

        th, tw = gray_tpl.shape[:2]
        regions = []

        for scale in [0.5, 0.75, 1.0, 1.25, 1.5]:
            resized = cv2.resize(gray_tpl, None, fx=scale, fy=scale)
            rh, rw = resized.shape[:2]
            if rh > gray_img.shape[0] or rw > gray_img.shape[1]:
                continue

            result = cv2.matchTemplate(gray_img, resized, cv2.TM_CCOEFF_NORMED)
            locations = np.where(result >= threshold)

            for pt_y, pt_x in zip(*locations):
                regions.append(
                    DetectedRegion(
                        x=int(pt_x), y=int(pt_y),
                        w=int(rw), h=int(rh),
                        confidence=float(result[pt_y, pt_x]),
                    )
                )

        return self._non_max_suppression(regions)
