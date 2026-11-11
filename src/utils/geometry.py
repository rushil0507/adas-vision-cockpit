"""Geometry and spatial calculation utilities for ADAS."""

from typing import List, Tuple, Optional
import numpy as np


def point_in_polygon(point: Tuple[float, float], polygon: List[List[float]]) -> bool:
    """
    Determines whether a 2D point (x, y) is inside or on the boundary of a polygon.
    Uses the ray-casting algorithm (even-odd rule) for pure-Python reliability.
    """
    x, y = point
    n = len(polygon)
    if n < 3:
        return False

    inside = False
    p1x, p1y = polygon[0]
    for i in range(1, n + 1):
        p2x, p2y = polygon[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        x_inters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    else:
                        x_inters = p1x
                    if p1x == p2x or x <= x_inters:
                        inside = not inside
        p1x, p1y = p2x, p2y

    return inside


def scale_polygon(
    polygon: List[List[float]],
    src_width: float,
    src_height: float,
    target_width: float,
    target_height: float,
) -> List[List[int]]:
    """Scale a polygon from a source resolution (e.g. 1280x720) to target frame resolution."""
    scale_x = target_width / max(1.0, src_width)
    scale_y = target_height / max(1.0, src_height)
    return [[int(round(pt[0] * scale_x)), int(round(pt[1] * scale_y))] for pt in polygon]


def calculate_pinhole_distance(
    bbox_h_px: float,
    real_height_m: float = 1.70,
    focal_length_px: float = 800.0,
) -> float:
    """
    Estimates distance (meters) to target object using pinhole camera model:
    distance = (real_height * focal_length) / bbox_height_px
    """
    if bbox_h_px <= 0:
        return 999.0
    return float((real_height_m * focal_length_px) / bbox_h_px)


def calculate_centroid(bbox: List[float]) -> Tuple[float, float]:
    """Calculates center (cx, cy) from [x1, y1, x2, y2]."""
    x1, y1, x2, y2 = bbox
    return (float((x1 + x2) / 2.0), float((y1 + y2) / 2.0))


def calculate_bottom_center(bbox: List[float]) -> Tuple[float, float]:
    """Calculates bottom-center point (cx, y2) from [x1, y1, x2, y2] representing object contact point with road."""
    x1, _, x2, y2 = bbox
    return (float((x1 + x2) / 2.0), float(y2))


def calculate_velocity(centroid_history: List[Tuple[float, float]], window: int = 5) -> Tuple[float, float, float]:
    """
    Calculates estimated velocity vector (dx/dt, dy/dt) and speed magnitude in px/frame
    over the recent history window.
    Positive dy means moving downward on image (towards the vehicle).
    """
    if len(centroid_history) < 2:
        return (0.0, 0.0, 0.0)

    pts = centroid_history[-min(len(centroid_history), window):]
    dt = len(pts) - 1
    dx = (pts[-1][0] - pts[0][0]) / max(1, dt)
    dy = (pts[-1][1] - pts[0][1]) / max(1, dt)
    speed = float(np.hypot(dx, dy))
    return (float(dx), float(dy), speed)


def calculate_lateral_offset(
    left_fit: Optional[np.ndarray],
    right_fit: Optional[np.ndarray],
    y_eval: float,
    frame_width: float,
    lane_width_m: float = 3.70,
) -> Tuple[Optional[float], Optional[float]]:
    """
    Calculates vehicle lateral offset in meters relative to lane center.
    Returns:
        (offset_m, lane_width_px)
        offset_m > 0: vehicle is right of center
        offset_m < 0: vehicle is left of center
    """
    if left_fit is None or right_fit is None:
        return None, None

    x_left = left_fit[0] * (y_eval ** 2) + left_fit[1] * y_eval + left_fit[2]
    x_right = right_fit[0] * (y_eval ** 2) + right_fit[1] * y_eval + right_fit[2]

    pixel_lane_width = x_right - x_left
    if pixel_lane_width <= 20:  # Invalid or crossed lanes
        return None, None

    lane_center_px = (x_left + x_right) / 2.0
    vehicle_center_px = frame_width / 2.0

    meters_per_pixel = lane_width_m / pixel_lane_width
    offset_m = (vehicle_center_px - lane_center_px) * meters_per_pixel

    return float(offset_m), float(pixel_lane_width)


def calculate_curvature(
    fit: Optional[np.ndarray],
    y_eval: float,
    meters_per_pixel_x: float = 3.7 / 700.0,
    meters_per_pixel_y: float = 30.0 / 720.0,
) -> Optional[float]:
    """
    Calculates radius of curvature in meters for a 2nd-order polynomial fit:
    x = A*y^2 + B*y + C
    R_curve = ((1 + (2*A*y*my + B)^2)**1.5) / |2*A*mx/my^2|
    """
    if fit is None or len(fit) < 3:
        return None

    a, b, _ = fit
    if abs(a) < 1e-7:
        return 9999.0  # Straight line

    # Convert fit to world coordinates
    a_world = a * (meters_per_pixel_x / (meters_per_pixel_y ** 2))
    b_world = b * (meters_per_pixel_x / meters_per_pixel_y)
    y_world = y_eval * meters_per_pixel_y

    curverad = ((1.0 + (2.0 * a_world * y_world + b_world) ** 2) ** 1.5) / max(1e-6, abs(2.0 * a_world))
    return float(round(curverad, 1))

