# Real-Time Advanced Driver Assistance System (ADAS)

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.0+-ee4c2c.svg)](https://pytorch.org/)
[![Ultralytics YOLOv8](https://img.shields.io/badge/YOLOv8-ByteTrack-00FFFF.svg)](https://github.com/ultralytics/ultralytics)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-009688.svg)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB.svg)](https://react.dev/)
[![Tailwind CSS](https://img.shields.io/badge/TailwindCSS-3.4-38B2AC.svg)](https://tailwindcss.com/)
[![CI Pipeline](https://github.com/rushil0507/adas-vision-cockpit/actions/workflows/ci.yml/badge.svg)](https://github.com/rushil0507/adas-vision-cockpit/actions)
[![Deploy to Netlify](https://www.netlify.com/img/deploy/button.svg)](https://app.netlify.com/start/deploy?repository=https://github.com/rushil0507/adas-vision-cockpit)

A modular, real-time vision system for dashcam footage, webcam devices, and RTSP live streams that executes:
1. **Pedestrian Tracking & Danger Zone Risk Estimation**: YOLOv8 + ByteTrack persistent IDs with pinhole camera distance estimation and kinematics.
2. **Classical & Deep Lane Marking Detection**: Bird's-eye perspective sliding-window polynomial fitting with lateral offset calculation and curvature estimation.
3. **Road Sign Localization & Classification**: Two-stage localization with a 43-class GTSRB CNN classifier and majority-vote temporal smoothing.
4. **Fusion & Decision Engine**: Evaluates safety risks with cooldown deduplication and persistent SQLite event logging.
5. **Interactive Cockpit Web Dashboard**: React + Vite + Tailwind CSS + Recharts streaming annotated video and telemetry over WebSockets.

---

## Architecture Overview

```
┌──────────────┐    ┌───────────────────┐    ┌──────────────────────────────┐
│ Video Source │───▶│ Frame Grabber     │───▶│ Preprocessing                │
│ file/webcam  │    │ (thread + queue)  │    │ resize, normalize, ROI crop  │
└──────────────┘    └───────────────────┘    └──────────────┬───────────────┘
                                                            │
                       ┌────────────────────────────────────┼──────────────────────┐
                       ▼                                    ▼                      ▼
          ┌─────────────────────────┐      ┌──────────────────────────┐   ┌───────────────────┐
          │ Pedestrian Module       │      │ Road Sign Module         │   │ Lane Module       │
          │ YOLOv8 (class: person)  │      │ YOLOv8 sign detector     │   │ Classical pipeline│
          │ + ByteTrack IDs         │      │ + CNN sign classifier    │   │ (+ optional DL)   │
          └────────────┬────────────┘      └────────────┬─────────────┘   └─────────┬─────────┘
                       └────────────────────┬───────────┴───────────────────────────┘
                                            ▼
                             ┌──────────────────────────────┐
                             │ Fusion & Decision Engine     │
                             │ alerts, risk levels, SQLite  │
                             └──────────────┬───────────────┘
                                            ▼
                  ┌─────────────────────────────────────────────────┐
                  │ Visualization Overlay (boxes, lanes, HUD)       │
                  └──────────────┬──────────────────────────────────┘
                                 ▼
                  ┌─────────────────────────────────────────────────┐
                  │ FastAPI Server                                  │
                  │ /ws/stream (frames+JSON), REST (events, config) │
                  └──────────────┬──────────────────────────────────┘
                                 ▼
                  ┌─────────────────────────────────────────────────┐
                  │ React Dashboard                                 │
                  │ live feed, alert panel, FPS, detection history  │
                  └─────────────────────────────────────────────────┘
```

---

## Folder Structure

```
adas-project/
├── configs/
│   └── config.yaml               # Master pipeline and threshold configuration
├── data/
│   ├── samples/                  # Demo videos (e.g. demo.mp4)
│   └── datasets/                 # Training datasets (GTSDB, GTSRB)
├── weights/                      # Trained model weights (sign_det.pt, sign_cls.pt)
├── src/
│   ├── core/
│   │   ├── pipeline.py           # Pipeline master coordinator
│   │   ├── frame_source.py       # Threaded frame grabber with bounded queue
│   │   └── fusion.py             # Multi-sensor alert fusion & decision engine
│   ├── modules/
│   │   ├── pedestrian.py         # YOLOv8 + ByteTrack pedestrian kinematics
│   │   ├── signs.py              # Road sign detector + GTSRB CNN classifier
│   │   └── lanes.py              # Classical sliding-window + deep lane mode
│   ├── utils/
│   │   ├── visualization.py      # HUD instrumentation and frame overlays
│   │   ├── geometry.py           # Polygon testing, pinhole math, curvature
│   │   └── metrics.py            # Latency profiler and running FPS tracker
│   ├── training/
│   │   ├── train_sign_detector.py   # YOLOv8 fine-tuning script
│   │   ├── train_sign_classifier.py # 43-class CNN trainer
│   │   └── convert_dataset.py       # GTSDB to YOLO dataset converter
│   └── api/
│       ├── main.py               # FastAPI application entry point
│       ├── routes.py             # REST endpoints (/api/stats, /api/events, etc.)
│       ├── websocket.py          # WebSocket client broadcaster
│       └── db.py                 # SQLite alert and incident store
├── frontend/                     # React + Vite + Tailwind CSS dashboard
├── tests/                        # Pytest unit and integration test suite
├── benchmark.py                  # Benchmarking script for FPS and latency
├── requirements.txt              # Python dependencies
├── Dockerfile                    # Container definition
└── pytest.ini                    # Test runner configuration
```

---

## Quickstart Setup

### 1. Python Backend Setup

In PowerShell or Bash:

```powershell
# 1. Navigate to adas-project
cd adas-project

# 2. Create virtual environment
python -m venv venv

# 3. Activate virtual environment
# Windows PowerShell:
.\venv\Scripts\Activate.ps1
# Linux/macOS:
source venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt
```

### 2. Run the Backend Server

```powershell
uvicorn src.api.main:app --reload --port 8000
```

The FastAPI backend will start on `http://localhost:8000` and automatically initialize the pipeline with the sample demo video.

Interactive API Documentation:
- Swagger UI: `http://localhost:8000/docs`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

---

### 3. Frontend Dashboard Setup

In a new terminal window:

```powershell
cd adas-project/frontend

# Install node dependencies
npm install

# Start Vite development server
npm run dev
```

Open your browser at `http://localhost:5173` to access the Cockpit Dashboard!

Alternatively, build the production frontend assets:
```powershell
npm run build
```
Once built, the FastAPI server serves the compiled dashboard directly at `http://localhost:8000/`.

---

## Safety Alert Specifications

| Alert | Condition | Severity | Action / HUD |
| :--- | :--- | :--- | :--- |
| **`PEDESTRIAN_COLLISION_RISK`** | Pedestrian in danger zone, close (≤ 8m) or approaching fast | **`CRITICAL`** | Red banner, hazard indicator, SQLite logged |
| **`PEDESTRIAN_AHEAD`** | Pedestrian in danger zone corridor (> 8m, medium distance) | **`WARNING`** | Amber banner, advisory tag |
| **`LANE_DEPARTURE`** | Lateral lane offset > 0.40m for ≥ 5 consecutive frames | **`WARNING`** | Amber/Red lane overlay & directional alert |
| **`STOP_SIGN_DETECTED`** | Stop sign detected in visual field | **`INFO`** | Cyan/Red badge, stop reminder |
| **`SPEED_LIMIT_SIGN`** | Speed limit sign detected (conf ≥ 0.60) | **`INFO`** | Speed badge updated in top telemetry HUD |

All alerts enforce a configurable 3.0-second cooldown interval to prevent spam, and all safety events are recorded in SQLite (`adas_events.db`).

---

## REST & WebSocket API Contracts

### WebSocket Streaming: `/ws/stream`

Broadcasts JPEG base64 annotated frames alongside per-frame metadata:

```json
{
  "frame": "data:image/jpeg;base64,...",
  "fps": 22.4,
  "pedestrians": [
    {
      "id": 1,
      "bbox": [280, 420, 340, 560],
      "confidence": 0.88,
      "distance_m": 7.5,
      "velocity_px": [0.4, 2.1],
      "in_danger_zone": true,
      "risk": "HIGH"
    }
  ],
  "signs": [
    {
      "bbox": [980, 240, 1040, 300],
      "label": "Speed limit (50km/h)",
      "conf": 0.92,
      "is_speed_limit": true,
      "speed_value": 50
    }
  ],
  "lane": {
    "detected": true,
    "offset_m": -0.12,
    "curvature_m": 1250.0,
    "departure": false
  },
  "alerts": [
    {
      "type": "PEDESTRIAN_COLLISION_RISK",
      "severity": "CRITICAL",
      "message": "Collision risk! Pedestrian #1 in danger zone (7.5m)."
    }
  ],
  "metrics": {
    "total_ms": 38.4,
    "pedestrian_ms": 18.2,
    "lanes_ms": 11.5,
    "signs_ms": 7.2
  }
}
```

### REST Endpoints

- `POST /api/start` - Starts video capture and perception worker.
- `POST /api/stop` - Halts pipeline processing.
- `POST /api/source` - Switch source dynamically (`{"type": "file" | "webcam" | "rtsp", "path": "0"}`).
- `GET /api/stats` - Telemetry, FPS, and per-module millisecond latencies.
- `GET /api/config` - Retrieve current detection thresholds and parameters.
- `PUT /api/config` - Dynamically update confidence, lane mode, or alert cooldowns.
- `GET /api/events` - Retrieve paginated SQLite incident history (`limit`, `offset`, `severity`).
- `POST /api/upload` - Upload a local `.mp4` dashcam video directly into `data/samples/`.

---

## Testing & Benchmarking

### Run the Test Suite

```powershell
python -m pytest tests/ -v
```

16 comprehensive unit and integration tests covering:
- Geometry utilities (point-in-polygon ray casting, pinhole distance calculation, kinematics).
- Classical lane detection on synthetic test images (sliding window & curvature).
- Alert rules, cooldown verification, and SQLite event logging.
- FastAPI REST endpoints.

### Run Performance Benchmarking

```powershell
python benchmark.py --frames 50
```

Generates a detailed ASCII performance table displaying end-to-end FPS, latency distributions, lane detection reliability, and ByteTrack stability.

---

## Docker Deployment (Optional)

Build and run using Docker:

```bash
docker build -t adas-cockpit .
docker run -p 8000:8000 adas-cockpit
```

Access the system at `http://localhost:8000`.

