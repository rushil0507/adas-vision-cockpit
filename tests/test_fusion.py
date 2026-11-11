"""Unit tests for Fusion and Decision Engine alert rules, cooldowns, and SQLite logging."""

import os
import time
import pytest
from src.core.fusion import FusionEngine, Alert
from src.modules.pedestrian import PedestrianTrack
from src.modules.lanes import LaneResult
from src.modules.signs import DetectedSign
from src.api.db import EventDatabase


@pytest.fixture
def temp_db(tmp_path):
    db_file = os.path.join(tmp_path, "test_events.db")
    return EventDatabase(db_path=db_file)


def test_fusion_pedestrian_collision_alert(temp_db):
    cfg = {"alerts": {"cooldown_s": 1.0}}
    fusion = FusionEngine(cfg, db=temp_db)

    ped_high = PedestrianTrack(
        track_id=1,
        bbox=[200, 300, 250, 450],
        confidence=0.9,
        distance_m=6.5,
        in_danger_zone=True,
        risk="HIGH",
    )
    lane = LaneResult(detected=True, offset_m=0.1, departure=False)
    signs = []

    # First trigger: should alert and log to DB
    alerts = fusion.process([ped_high], lane, signs)
    assert len(alerts) == 1
    assert alerts[0].type == "PEDESTRIAN_COLLISION_RISK"
    assert alerts[0].severity == "CRITICAL"
    assert temp_db.get_event_count() == 1

    # Second trigger immediately (within cooldown): should return active alert but not duplicate DB log
    alerts2 = fusion.process([ped_high], lane, signs)
    assert len(alerts2) == 1
    assert temp_db.get_event_count() == 1  # Still 1 due to cooldown!


def test_fusion_lane_departure_alert(temp_db):
    cfg = {"alerts": {"cooldown_s": 0.5}}
    fusion = FusionEngine(cfg, db=temp_db)

    lane_depart = LaneResult(detected=True, offset_m=0.55, departure=True)
    alerts = fusion.process([], lane_depart, [])
    assert len(alerts) == 1
    assert alerts[0].type == "LANE_DEPARTURE"
    assert alerts[0].severity == "WARNING"
    assert temp_db.get_event_count() == 1


def test_fusion_signs_alert(temp_db):
    cfg = {"alerts": {"cooldown_s": 1.0, "speed_limit_conf": 0.60}}
    fusion = FusionEngine(cfg, db=temp_db)

    stop_sign = DetectedSign(bbox=[100, 100, 150, 150], label="Stop", confidence=0.85)
    speed_sign = DetectedSign(
        bbox=[200, 100, 250, 150],
        label="Speed limit (50km/h)",
        confidence=0.92,
        is_speed_limit=True,
        speed_value=50,
    )
    lane = LaneResult(detected=True, departure=False)

    alerts = fusion.process([], lane, [stop_sign, speed_sign])
    alert_types = {a.type for a in alerts}
    assert "STOP_SIGN_DETECTED" in alert_types
    assert "SPEED_LIMIT_SIGN" in alert_types
    assert temp_db.get_event_count() == 2

