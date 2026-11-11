"""Unit tests for geometry, spatial calculations, and coordinate transformations."""

import pytest
import numpy as np
from src.utils.geometry import (
    point_in_polygon,
    scale_polygon,
    calculate_pinhole_distance,
    calculate_centroid,
    calculate_bottom_center,
    calculate_velocity,
    calculate_lateral_offset,
    calculate_curvature,
)


def test_point_in_polygon():
    polygon = [[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0]]
    # Inside
    assert point_in_polygon((5.0, 5.0), polygon) is True
    # Outside
    assert point_in_polygon((15.0, 5.0), polygon) is False
    assert point_in_polygon((-1.0, 5.0), polygon) is False
    # Degenerate
    assert point_in_polygon((5.0, 5.0), [[0, 0], [1, 1]]) is False


def test_scale_polygon():
    poly = [[100, 200], [300, 400]]
    scaled = scale_polygon(poly, src_width=1000, src_height=500, target_width=500, target_height=250)
    assert scaled == [[50, 100], [150, 200]]


def test_calculate_pinhole_distance():
    # Distance = (1.70 * 800) / 100 = 13.6 meters
    dist = calculate_pinhole_distance(bbox_h_px=100.0, real_height_m=1.70, focal_length_px=800.0)
    assert abs(dist - 13.6) < 1e-3

    # Half height -> double distance
    dist_far = calculate_pinhole_distance(bbox_h_px=50.0, real_height_m=1.70, focal_length_px=800.0)
    assert abs(dist_far - 27.2) < 1e-3


def test_centroids_and_bottom_center():
    bbox = [100, 200, 200, 400]
    cx, cy = calculate_centroid(bbox)
    assert cx == 150.0
    assert cy == 300.0

    bc_x, bc_y = calculate_bottom_center(bbox)
    assert bc_x == 150.0
    assert bc_y == 400.0


def test_calculate_velocity():
    history = [(100.0, 100.0), (100.0, 105.0), (100.0, 110.0), (100.0, 115.0)]
    dx, dy, speed = calculate_velocity(history, window=4)
    assert abs(dx) < 1e-5
    assert abs(dy - 5.0) < 1e-5
    assert abs(speed - 5.0) < 1e-5


def test_calculate_lateral_offset():
    # Symmetric lanes centered at x=640 in 1280 wide image
    # Left lane at x=400, right lane at x=880 (width 480 px, center 640)
    left_fit = np.array([0.0, 0.0, 400.0])
    right_fit = np.array([0.0, 0.0, 880.0])
    offset_m, width_px = calculate_lateral_offset(left_fit, right_fit, y_eval=720, frame_width=1280, lane_width_m=3.7)
    assert abs(offset_m) < 0.01  # Centered

    # Vehicle shifted right: lanes appear shifted to left (x=300 and 780, center=540)
    left_shifted = np.array([0.0, 0.0, 300.0])
    right_shifted = np.array([0.0, 0.0, 780.0])
    offset_shifted, _ = calculate_lateral_offset(left_shifted, right_shifted, y_eval=720, frame_width=1280, lane_width_m=3.7)
    assert offset_shifted > 0.40  # Vehicle is to the right of lane center


def test_calculate_curvature():
    # Straight line: curvature should be large
    straight_fit = np.array([0.0, 0.0, 400.0])
    curv = calculate_curvature(straight_fit, y_eval=720)
    assert curv >= 5000.0

