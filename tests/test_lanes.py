"""Unit tests for lane detection on synthetic test images."""

import pytest
import numpy as np
import cv2
from src.modules.lanes import LaneModule


def create_synthetic_lane_image(w=1280, h=720, shift=0):
    """Draws a clean road frame with left and right lane markings."""
    img = np.full((h, w, 3), 40, dtype=np.uint8)
    horizon = int(h * 0.55)

    # Left lane (white)
    pt1 = (int(w * 0.25) + shift, h)
    pt2 = (int(w * 0.45), horizon)
    cv2.line(img, pt1, pt2, (255, 255, 255), 10)

    # Right lane (yellow)
    pt3 = (int(w * 0.75) + shift, h)
    pt4 = (int(w * 0.55), horizon)
    cv2.line(img, pt3, pt4, (0, 220, 255), 10)

    return img


def test_synthetic_lane_detection():
    cfg = {
        "lanes": {
            "mode": "classical",
            "roi_top_ratio": 0.50,
            "lane_width_m": 3.70,
            "canny": [30, 100],
            "hls_white_thresh": 180,
            "sliding_windows": 8,
            "smoothing_frames": 2,
        }
    }
    module = LaneModule(cfg)

    frame = create_synthetic_lane_image()
    res = module.process(frame)

    assert res.detected is True
    assert res.left_fit is not None
    assert res.right_fit is not None
    assert res.offset_m is not None
    assert abs(res.offset_m) < 0.35
    assert res.departure is False

