"""Fusion and Decision Engine: Combines perception outputs, triggers safety alerts, and logs to SQLite."""

import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
import logging

from src.modules.pedestrian import PedestrianTrack
from src.modules.lanes import LaneResult
from src.modules.signs import DetectedSign
from src.api.db import EventDatabase

logger = logging.getLogger(__name__)


@dataclass
class Alert:
    """Active safety alert."""

    type: str  # LANE_DEPARTURE, PEDESTRIAN_AHEAD, PEDESTRIAN_COLLISION_RISK, SPEED_LIMIT_SIGN, STOP_SIGN_DETECTED
    severity: str  # INFO, WARNING, CRITICAL
    message: str

    def to_dict(self) -> Dict[str, str]:
        return {
            "type": self.type,
            "severity": self.severity,
            "message": self.message,
        }


class FusionEngine:
    """Evaluates multi-modal sensor state, enforces alert cooldowns, and persists safety events."""

    def __init__(self, config: Dict[str, Any], db: Optional[EventDatabase] = None):
        self.config = config.get("alerts", {})
        self.cooldown_s = float(self.config.get("cooldown_s", 3.0))
        self.speed_limit_conf = float(self.config.get("speed_limit_conf", 0.60))
        self.db = db or EventDatabase()

        # Alert type -> last triggered monotonic timestamp
        self.last_alert_time: Dict[str, float] = {}

    def update_config(self, new_cfg: Dict[str, Any]):
        if "cooldown_s" in new_cfg:
            self.cooldown_s = float(new_cfg["cooldown_s"])
        if "speed_limit_conf" in new_cfg:
            self.speed_limit_conf = float(new_cfg["speed_limit_conf"])

    def process(
        self,
        pedestrians: List[PedestrianTrack],
        lane: LaneResult,
        signs: List[DetectedSign],
    ) -> List[Alert]:
        """
        Processes perception results and returns any active alerts for the current frame.
        Logs newly triggered alerts with respected cooldowns to the event database.
        """
        now = time.monotonic()
        active_alerts: List[Alert] = []

        # 1. Critical Pedestrian Collision Risk (HIGH risk)
        high_risk_peds = [p for p in pedestrians if p.risk == "HIGH"]
        if high_risk_peds:
            target = high_risk_peds[0]
            msg = f"Collision risk! Pedestrian #{target.track_id} in danger zone ({target.distance_m:.1f}m)."
            alert = Alert(
                type="PEDESTRIAN_COLLISION_RISK",
                severity="CRITICAL",
                message=msg,
            )
            active_alerts.append(alert)
            self._try_log_alert("PEDESTRIAN_COLLISION_RISK", "CRITICAL", msg, now)

        # 2. Pedestrian Ahead (MEDIUM risk)
        elif any(p.risk == "MEDIUM" for p in pedestrians):
            medium_peds = [p for p in pedestrians if p.risk == "MEDIUM"]
            target = medium_peds[0]
            msg = f"Pedestrian #{target.track_id} ahead in danger corridor ({target.distance_m:.1f}m)."
            alert = Alert(
                type="PEDESTRIAN_AHEAD",
                severity="WARNING",
                message=msg,
            )
            active_alerts.append(alert)
            self._try_log_alert("PEDESTRIAN_AHEAD", "WARNING", msg, now)

        # 3. Lane Departure
        if lane.departure:
            offset_val = lane.offset_m if lane.offset_m is not None else 0.45
            direction = "right" if offset_val > 0 else "left"
            msg = f"Lane departure warning! Drift {direction} ({abs(offset_val):.2f}m)."
            alert = Alert(
                type="LANE_DEPARTURE",
                severity="WARNING",
                message=msg,
            )
            active_alerts.append(alert)
            self._try_log_alert("LANE_DEPARTURE", "WARNING", msg, now)

        # 4. Stop Sign Detected
        stop_signs = [s for s in signs if "Stop" in s.label]
        if stop_signs:
            s = stop_signs[0]
            msg = f"Stop sign detected (conf: {s.confidence:.2f}). Prepare to halt."
            alert = Alert(
                type="STOP_SIGN_DETECTED",
                severity="INFO",
                message=msg,
            )
            active_alerts.append(alert)
            self._try_log_alert("STOP_SIGN_DETECTED", "INFO", msg, now)

        # 5. Speed Limit Sign Detected
        speed_signs = [s for s in signs if s.is_speed_limit and s.confidence >= self.speed_limit_conf]
        if speed_signs:
            s = speed_signs[0]
            msg = f"Speed limit sign detected: {s.speed_value} km/h (conf: {s.confidence:.2f})."
            alert = Alert(
                type="SPEED_LIMIT_SIGN",
                severity="INFO",
                message=msg,
            )
            active_alerts.append(alert)
            self._try_log_alert("SPEED_LIMIT_SIGN", "INFO", msg, now)

        return active_alerts

    def _try_log_alert(self, alert_type: str, severity: str, message: str, now: float):
        """Logs event to database only if cooldown interval has elapsed."""
        last_t = self.last_alert_time.get(alert_type, 0.0)
        if (now - last_t) >= self.cooldown_s:
            self.last_alert_time[alert_type] = now
            try:
                self.db.log_event(alert_type=alert_type, severity=severity, message=message)
                logger.info(f"[{severity}] Alert logged: {alert_type} - {message}")
            except Exception as e:
                logger.error(f"Failed to log alert to DB: {e}")

