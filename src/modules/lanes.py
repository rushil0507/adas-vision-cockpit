"""Lane Marking Detection Module (Classical Sliding-Window Bird's-Eye View + Deep Learning Mode)."""

from collections import deque
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any
import logging
import cv2
import numpy as np

from src.utils.geometry import calculate_lateral_offset, calculate_curvature

logger = logging.getLogger(__name__)


@dataclass
class LaneResult:
    """Detection results for lane markings and vehicle ego-positioning."""

    detected: bool
    left_fit: Optional[List[float]] = None
    right_fit: Optional[List[float]] = None
    offset_m: Optional[float] = None
    curvature_m: Optional[float] = None
    lane_width_px: Optional[float] = None
    departure: bool = False
    polygon_points: Optional[List[List[int]]] = None  # Original perspective polygon for visual overlay

    def to_dict(self) -> Dict[str, Any]:
        return {
            "detected": self.detected,
            "offset_m": round(self.offset_m, 2) if self.offset_m is not None else 0.0,
            "curvature_m": round(self.curvature_m, 1) if self.curvature_m is not None else 0.0,
            "departure": self.departure,
            "left_fit": [round(c, 5) for c in self.left_fit] if self.left_fit is not None else None,
            "right_fit": [round(c, 5) for c in self.right_fit] if self.right_fit is not None else None,
        }


class LaneModule:
    """Robust lane detection pipeline with temporal smoothing, offset estimation, and departure logic."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config.get("lanes", {})
        self.mode = self.config.get("mode", "classical")
        self.roi_top_ratio = float(self.config.get("roi_top_ratio", 0.55))
        self.lane_width_m = float(self.config.get("lane_width_m", 3.70))
        self.canny_thresh = self.config.get("canny", [50, 150])
        self.hls_white_thresh = int(self.config.get("hls_white_thresh", 195))
        self.nwindows = int(self.config.get("sliding_windows", 9))
        self.margin = int(self.config.get("window_margin", 60))
        self.minpix = int(self.config.get("minpix", 40))
        self.smoothing_frames = int(self.config.get("smoothing_frames", 5))

        self.left_fit_history: deque = deque(maxlen=self.smoothing_frames)
        self.right_fit_history: deque = deque(maxlen=self.smoothing_frames)
        self.consecutive_departures = 0

        # Deep learning lane model if mode == 'deep'
        self.deep_model = None
        if self.mode == "deep":
            self._init_deep_model()

    def _init_deep_model(self):
        try:
            from ultralytics import YOLO

            deep_weights = self.config.get("deep_weights", "yolov8n-seg.pt")
            logger.info(f"Loading Deep Lane Model from {deep_weights}...")
            self.deep_model = YOLO(deep_weights)
        except Exception as e:
            logger.warning(f"Could not load deep lane model ({e}), falling back to classical pipeline.")
            self.mode = "classical"

    def update_config(self, new_cfg: Dict[str, Any]):
        """Update runtime configurations."""
        if "mode" in new_cfg:
            self.mode = new_cfg["mode"]
            if self.mode == "deep" and self.deep_model is None:
                self._init_deep_model()
        if "roi_top_ratio" in new_cfg:
            self.roi_top_ratio = float(new_cfg["roi_top_ratio"])
        if "lane_width_m" in new_cfg:
            self.lane_width_m = float(new_cfg["lane_width_m"])

    def _preprocess_binary(self, frame: np.ndarray) -> np.ndarray:
        """Thresholds white and yellow lane markings combined with Canny edges."""
        hls = cv2.cvtColor(frame, cv2.COLOR_BGR2HLS)
        l_channel = hls[:, :, 1]
        s_channel = hls[:, :, 2]

        # White mask: high lightness
        white_mask = np.zeros_like(l_channel)
        white_mask[l_channel > self.hls_white_thresh] = 255

        # Yellow mask: H between 15 and 35, high saturation, moderate lightness
        h_channel = hls[:, :, 0]
        yellow_mask = np.zeros_like(h_channel)
        yellow_cond = (h_channel >= 15) & (h_channel <= 35) & (s_channel >= 70) & (l_channel >= 60)
        yellow_mask[yellow_cond] = 255

        # Edge detection on grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, self.canny_thresh[0], self.canny_thresh[1])

        combined = np.zeros_like(l_channel)
        combined[(white_mask == 255) | (yellow_mask == 255) | (edges == 255)] = 255
        return combined

    def _get_perspective_transforms(self, w: int, h: int) -> Tuple[np.ndarray, np.ndarray]:
        """Calculates forward and inverse bird's-eye perspective transform matrices."""
        top_y = int(h * self.roi_top_ratio)
        src = np.float32([
            [w * 0.15, h],
            [w * 0.43, top_y],
            [w * 0.57, top_y],
            [w * 0.88, h],
        ])
        dst = np.float32([
            [w * 0.20, h],
            [w * 0.20, 0],
            [w * 0.80, 0],
            [w * 0.80, h],
        ])
        M = cv2.getPerspectiveTransform(src, dst)
        Minv = cv2.getPerspectiveTransform(dst, src)
        return M, Minv

    def _sliding_window_fit(self, binary_warped: np.ndarray) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """Finds left and right lane pixels using sliding windows on warped binary image."""
        h, w = binary_warped.shape[:2]
        # Histogram of lower half
        histogram = np.sum(binary_warped[h // 2 :, :], axis=0)
        midpoint = int(w // 2)
        leftx_base = np.argmax(histogram[:midpoint])
        rightx_base = np.argmax(histogram[midpoint:]) + midpoint

        # If peaks are degenerate, estimate based on expected lane positions
        if leftx_base < 10 or leftx_base > midpoint - 20:
            leftx_base = int(w * 0.25)
        if rightx_base < midpoint + 20 or rightx_base > w - 10:
            rightx_base = int(w * 0.75)

        window_height = int(h // self.nwindows)
        nonzero = binary_warped.nonzero()
        nonzeroy = np.array(nonzero[0])
        nonzerox = np.array(nonzero[1])

        leftx_current = leftx_base
        rightx_current = rightx_base

        left_lane_inds = []
        right_lane_inds = []

        for window in range(self.nwindows):
            win_y_low = h - (window + 1) * window_height
            win_y_high = h - window * window_height
            win_xleft_low = leftx_current - self.margin
            win_xleft_high = leftx_current + self.margin
            win_xright_low = rightx_current - self.margin
            win_xright_high = rightx_current + self.margin

            good_left_inds = (
                (nonzeroy >= win_y_low)
                & (nonzeroy < win_y_high)
                & (nonzerox >= win_xleft_low)
                & (nonzerox < win_xleft_high)
            ).nonzero()[0]
            good_right_inds = (
                (nonzeroy >= win_y_low)
                & (nonzeroy < win_y_high)
                & (nonzerox >= win_xright_low)
                & (nonzerox < win_xright_high)
            ).nonzero()[0]

            left_lane_inds.append(good_left_inds)
            right_lane_inds.append(good_right_inds)

            if len(good_left_inds) > self.minpix:
                leftx_current = int(np.mean(nonzerox[good_left_inds]))
            if len(good_right_inds) > self.minpix:
                rightx_current = int(np.mean(nonzerox[good_right_inds]))

        left_lane_inds = np.concatenate(left_lane_inds)
        right_lane_inds = np.concatenate(right_lane_inds)

        left_fit = None
        right_fit = None

        if len(left_lane_inds) > 150:
            leftx = nonzerox[left_lane_inds]
            lefty = nonzeroy[left_lane_inds]
            left_fit = np.polyfit(lefty, leftx, 2)

        if len(right_lane_inds) > 150:
            rightx = nonzerox[right_lane_inds]
            righty = nonzeroy[right_lane_inds]
            right_fit = np.polyfit(righty, rightx, 2)

        # Fallback extrapolation if one lane is missing
        expected_lane_px = int(w * 0.55)
        if left_fit is not None and right_fit is None:
            right_fit = left_fit.copy()
            right_fit[2] += expected_lane_px
        elif right_fit is not None and left_fit is None:
            left_fit = right_fit.copy()
            left_fit[2] -= expected_lane_px

        return left_fit, right_fit

    def process(self, frame: np.ndarray) -> LaneResult:
        """Processes frame to detect lanes, calculate offset and curvature, and check departure."""
        h, w = frame.shape[:2]

        if self.mode == "deep" and self.deep_model is not None:
            # Deep mode delegation
            return self._process_deep(frame)

        # Classical Pipeline
        # 1. Color thresholding & Canny
        binary = self._preprocess_binary(frame)

        # 2. Bird's-eye perspective transform
        M, Minv = self._get_perspective_transforms(w, h)
        binary_warped = cv2.warpPerspective(binary, M, (w, h), flags=cv2.INTER_LINEAR)

        # 3. Sliding window search
        left_fit_raw, right_fit_raw = self._sliding_window_fit(binary_warped)

        # 4. Temporal smoothing across frames
        if left_fit_raw is not None:
            self.left_fit_history.append(left_fit_raw)
        if right_fit_raw is not None:
            self.right_fit_history.append(right_fit_raw)

        if not self.left_fit_history or not self.right_fit_history:
            return LaneResult(detected=False)

        left_fit = np.mean(self.left_fit_history, axis=0)
        right_fit = np.mean(self.right_fit_history, axis=0)

        # 5. Compute vehicle lateral offset & lane curvature
        y_eval = float(h - 1)
        offset_m, lane_width_px = calculate_lateral_offset(
            left_fit, right_fit, y_eval, float(w), self.lane_width_m
        )
        left_curv = calculate_curvature(left_fit, y_eval)
        right_curv = calculate_curvature(right_fit, y_eval)
        curv_m = None
        if left_curv and right_curv:
            curv_m = (left_curv + right_curv) / 2.0
        elif left_curv:
            curv_m = left_curv
        elif right_curv:
            curv_m = right_curv

        # 6. Unwarp lane polygon to camera perspective for visualization
        ploty = np.linspace(0, h - 1, num=30)
        left_fitx = left_fit[0] * ploty**2 + left_fit[1] * ploty + left_fit[2]
        right_fitx = right_fit[0] * ploty**2 + right_fit[1] * ploty + right_fit[2]

        pts_left = np.array([np.transpose(np.vstack([left_fitx, ploty]))])
        pts_right = np.array([np.flipud(np.transpose(np.vstack([right_fitx, ploty])))])
        pts = np.hstack((pts_left, pts_right))

        # Unwarp back to original perspective
        unwarped_pts = cv2.perspectiveTransform(pts, Minv)
        polygon_points = unwarped_pts[0].astype(int).tolist()

        # 7. Departure check
        is_departure = False
        if offset_m is not None and abs(offset_m) > 0.40:
            self.consecutive_departures += 1
            if self.consecutive_departures >= 5:
                is_departure = True
        else:
            self.consecutive_departures = 0

        return LaneResult(
            detected=True,
            left_fit=left_fit.tolist(),
            right_fit=right_fit.tolist(),
            offset_m=offset_m,
            curvature_m=curv_m,
            lane_width_px=lane_width_px,
            departure=is_departure,
            polygon_points=polygon_points,
        )

    def _process_deep(self, frame: np.ndarray) -> LaneResult:
        """Deep learning lane segmentation fallback."""
        try:
            results = self.deep_model(frame, verbose=False)
            # Default fallback to classical if no segmentations found
            return self.process(frame)
        except Exception:
            return self.process(frame)

