"""Computer Vision Visualization Overlay and HUD Drawing for ADAS."""

import base64
from typing import List, Optional, Tuple, Any
import cv2
import numpy as np

from src.modules.pedestrian import PedestrianTrack
from src.modules.lanes import LaneResult
from src.modules.signs import DetectedSign
from src.core.fusion import Alert


def frame_to_base64(frame: np.ndarray, quality: int = 75) -> str:
    """Encodes a BGR image frame to a JPEG base64 string."""
    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), max(10, min(100, quality))]
    success, buffer = cv2.imencode(".jpg", frame, encode_param)
    if not success:
        return ""
    return base64.b64encode(buffer).decode("utf-8")


class Visualizer:
    """Renders visual overlays, bounding boxes, lane corridors, and HUD instrumentation."""

    def __init__(self):
        # Color palette (BGR)
        self.COLOR_GREEN = (40, 210, 40)
        self.COLOR_AMBER = (0, 165, 255)
        self.COLOR_RED = (40, 40, 240)
        self.COLOR_CYAN = (240, 240, 40)
        self.COLOR_BLUE = (255, 120, 0)
        self.COLOR_WHITE = (255, 255, 255)
        self.COLOR_DARK = (20, 20, 25)

    def draw(
        self,
        frame: np.ndarray,
        pedestrians: List[PedestrianTrack],
        lane: LaneResult,
        signs: List[DetectedSign],
        danger_zone: Optional[List[List[int]]] = None,
        fps: float = 0.0,
        alerts: Optional[List[Alert]] = None,
        last_speed_limit: Optional[int] = None,
    ) -> np.ndarray:
        """Composes all annotations, lane polygons, and HUD elements onto frame."""
        vis = frame.copy()
        h, w = vis.shape[:2]

        # 1. Draw Lane Overlay (filled polygon + boundaries)
        if lane.detected and lane.polygon_points and len(lane.polygon_points) > 3:
            lane_overlay = vis.copy()
            lane_color = self.COLOR_RED if lane.departure else (30, 200, 70)
            poly_np = np.array([lane.polygon_points], dtype=np.int32)
            cv2.fillPoly(lane_overlay, poly_np, lane_color)
            # Alpha blend lane overlay
            cv2.addWeighted(lane_overlay, 0.35, vis, 0.65, 0, vis)
            cv2.polylines(vis, poly_np, isClosed=False, color=lane_color, thickness=2, lineType=cv2.LINE_AA)

        # 2. Draw Danger Zone Trapezoid
        if danger_zone and len(danger_zone) >= 4:
            dz_overlay = vis.copy()
            dz_np = np.array([danger_zone], dtype=np.int32)
            has_danger = any(p.risk in ("MEDIUM", "HIGH") for p in pedestrians)
            dz_color = self.COLOR_RED if has_danger else (180, 180, 50)
            cv2.fillPoly(dz_overlay, dz_np, dz_color)
            cv2.addWeighted(dz_overlay, 0.18, vis, 0.82, 0, vis)
            cv2.polylines(vis, dz_np, isClosed=True, color=dz_color, thickness=1, lineType=cv2.LINE_AA)

        # 3. Draw Pedestrian Bounding Boxes, Tracks, and Trails
        for ped in pedestrians:
            x1, y1, x2, y2 = ped.bbox
            if ped.risk == "HIGH":
                color = self.COLOR_RED
            elif ped.risk == "MEDIUM":
                color = self.COLOR_AMBER
            else:
                color = self.COLOR_GREEN

            # Bounding box
            cv2.rectangle(vis, (x1, y1), (x2, y2), color, 2, lineType=cv2.LINE_AA)

            # Centroid movement trail
            if len(ped.centroid_history) > 1:
                pts = list(ped.centroid_history)
                for i in range(1, len(pts)):
                    pt1 = (int(pts[i - 1][0]), int(pts[i - 1][1]))
                    pt2 = (int(pts[i][0]), int(pts[i][1]))
                    cv2.line(vis, pt1, pt2, color, 2, lineType=cv2.LINE_AA)

            # Contact point dot
            bc = (int((x1 + x2) / 2), int(y2))
            cv2.circle(vis, bc, 4, color, -1)

            # Label tag
            tag = f"#{ped.track_id} {ped.risk} {ped.distance_m:.1f}m"
            (tw, th), _ = cv2.getTextSize(tag, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(vis, (x1, max(0, y1 - th - 8)), (x1 + tw + 6, max(0, y1)), color, -1)
            cv2.putText(
                vis,
                tag,
                (x1 + 3, max(12, y1 - 4)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 255, 255),
                1,
                cv2.LINE_AA,
            )

        # 4. Draw Signs
        for sign in signs:
            sx1, sy1, sx2, sy2 = sign.bbox
            color = self.COLOR_CYAN
            if "Stop" in sign.label:
                color = self.COLOR_RED
            elif sign.is_speed_limit:
                color = self.COLOR_AMBER

            cv2.rectangle(vis, (sx1, sy1), (sx2, sy2), color, 2, lineType=cv2.LINE_AA)
            tag = f"{sign.label} {int(sign.confidence * 100)}%"
            (tw, th), _ = cv2.getTextSize(tag, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(vis, (sx1, max(0, sy1 - th - 8)), (sx1 + tw + 6, max(0, sy1)), color, -1)
            cv2.putText(
                vis,
                tag,
                (sx1 + 3, max(12, sy1 - 4)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (10, 10, 10),
                1,
                cv2.LINE_AA,
            )

        # 5. Top HUD Instrumentation Bar
        self._draw_hud(vis, fps, lane, last_speed_limit, pedestrians, alerts)

        return vis

    def _draw_hud(
        self,
        vis: np.ndarray,
        fps: float,
        lane: LaneResult,
        speed_limit: Optional[int],
        pedestrians: List[PedestrianTrack],
        alerts: Optional[List[Alert]],
    ):
        """Draws top telemetry bar, speed limit circle badge, and active alert toasts."""
        w = vis.shape[1]

        # Top HUD background panel
        hud_bar = vis[0:50, 0:w].copy()
        cv2.rectangle(hud_bar, (0, 0), (w, 50), self.COLOR_DARK, -1)
        cv2.addWeighted(hud_bar, 0.75, vis[0:50, 0:w], 0.25, 0, vis[0:50, 0:w])

        # FPS indicator
        cv2.putText(
            vis,
            f"FPS: {fps:.1f}",
            (18, 32),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            self.COLOR_GREEN if fps >= 15 else self.COLOR_AMBER,
            2,
            cv2.LINE_AA,
        )

        # Lane Offset & Curvature
        if lane.detected and lane.offset_m is not None:
            off_color = self.COLOR_RED if lane.departure else self.COLOR_GREEN
            off_text = f"OFFSET: {lane.offset_m:+.2f}m"
            cv2.putText(vis, off_text, (160, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.6, off_color, 2, cv2.LINE_AA)

            if lane.curvature_m is not None:
                curv_text = f"R: {int(lane.curvature_m)}m" if lane.curvature_m < 5000 else "R: STR"
                cv2.putText(vis, curv_text, (360, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.COLOR_WHITE, 1, cv2.LINE_AA)
        else:
            cv2.putText(vis, "LANES: SEARCHING", (160, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (160, 160, 160), 1, cv2.LINE_AA)

        # Pedestrian Count
        ped_count = len(pedestrians)
        ped_color = self.COLOR_RED if any(p.risk == "HIGH" for p in pedestrians) else self.COLOR_WHITE
        cv2.putText(
            vis,
            f"PEDS: {ped_count}",
            (500, 32),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            ped_color,
            2 if ped_count > 0 else 1,
            cv2.LINE_AA,
        )

        # Speed Limit Circle Badge
        if speed_limit is not None:
            cx, cy = w - 60, 25
            cv2.circle(vis, (cx, cy), 20, self.COLOR_RED, -1)
            cv2.circle(vis, (cx, cy), 17, self.COLOR_WHITE, -1)
            speed_str = str(speed_limit)
            font_scale = 0.5 if len(speed_str) <= 2 else 0.4
            (stw, sth), _ = cv2.getTextSize(speed_str, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 2)
            cv2.putText(
                vis,
                speed_str,
                (cx - stw // 2, cy + sth // 2),
                cv2.FONT_HERSHEY_SIMPLEX,
                font_scale,
                (10, 10, 10),
                2,
                cv2.LINE_AA,
            )

        # Active Alert Banner (if any)
        if alerts and len(alerts) > 0:
            top_alert = alerts[0]
            severity_color = self.COLOR_RED if top_alert.severity == "CRITICAL" else self.COLOR_AMBER
            banner_text = f"[{top_alert.severity}] {top_alert.message}"
            (btw, bth), _ = cv2.getTextSize(banner_text, cv2.FONT_HERSHEY_SIMPLEX, 0.65, 2)
            bx1 = (w - btw) // 2 - 15
            bx2 = (w + btw) // 2 + 15
            cv2.rectangle(vis, (bx1, 60), (bx2, 95), severity_color, -1)
            cv2.rectangle(vis, (bx1, 60), (bx2, 95), (255, 255, 255), 1)
            cv2.putText(
                vis,
                banner_text,
                (bx1 + 15, 84),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (255, 255, 255),
                2,
                cv2.LINE_AA,
            )

