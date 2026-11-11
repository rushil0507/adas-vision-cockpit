# ADAS Vision Cockpit — Complete Project Manual & Architecture Guide

A production-grade, real-time Advanced Driver Assistance System (ADAS) built in Python and React. It processes dashcam footage, live webcam feeds, or RTSP camera streams to perform real-time pedestrian tracking, lane departure warning, and road sign recognition with sub-40ms latency.

---

## Table of Contents

1. [System Architecture & Data Flow](#1-system-architecture--data-flow)
2. [Deep Dive: Perception Subsystems](#2-deep-dive-perception-subsystems)
   - [Pedestrian Tracking & Danger Zone Kinematics](#21-pedestrian-tracking--danger-zone-kinematics)
   - [Lane Marking Detection & Lateral Offset](#22-lane-marking-detection--lateral-offset)
   - [Road Sign Recognition & GTSRB Classification](#23-road-sign-recognition--gtsrb-classification)
3. [Decision & Alert Fusion Engine](#3-decision--alert-fusion-engine)
4. [Backend API & WebSocket Streaming](#4-backend-api--websocket-streaming)
5. [Frontend Cockpit Web Dashboard](#5-frontend-cockpit-web-dashboard)
6. [Master Configuration Reference](#6-master-configuration-reference)
7. [How to Run the Project (Step-by-Step)](#7-how-to-run-the-project-step-by-step)
   - [Option A: One-Click Startup Script (Recommended)](#option-a-one-click-startup-script-recommended)
   - [Option B: Manual Terminal Execution](#option-b-manual-terminal-execution)
   - [Option C: Production Single-Port Mode](#option-c-production-single-port-mode)
   - [Option D: Docker Container](#option-d-docker-container)
8. [Testing & Benchmarking](#8-testing--benchmarking)
9. [Troubleshooting & Common Questions](#9-troubleshooting--common-questions)

---

## 1. System Architecture & Data Flow

```
┌────────────────────────────────────────────────────────────────────────┐
│                              INPUT SOURCE                              │
│       Dashcam Video (MP4)  /  USB Webcam  /  RTSP Network Stream       │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        THREADED FRAME GRABBER                          │
│        Non-blocking capture loop with bounded queue (drops stale)       │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                       PARALLEL PERCEPTION MODULES                      │
│                                                                        │
│  ┌─────────────────────────┐  ┌───────────────────┐  ┌──────────────┐  │
│  │   Pedestrian Module     │  │    Lane Module    │  │ Sign Module  │  │
│  │ YOLOv8n + ByteTrack     │  │  BEV Perspective  │  │ YOLO + GTSRB │  │
│  │ Pinhole 3D Distance     │  │  Sliding Windows  │  │ CNN Classify │  │
│  │ Centroid Velocity Kin.  │  │  2nd-order Poly   │  │ Temporal     │  │
│  │ Corridor Ray-Casting    │  │  Lateral Offset   │  │ Smoothing    │  │
│  └────────────┬────────────┘  └─────────┬─────────┘  └──────┬───────┘  │
└───────────────┼─────────────────────────┼───────────────────┼──────────┘
                └───────────────────┬─────┴───────────────────┘
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                       FUSION & DECISION ENGINE                         │
│   - Multi-sensor risk scoring (CRITICAL, WARNING, INFO)                │
│   - Time-window alert cooldown deduplication (default 3.0s)            │
│   - SQLite incident audit logger (adas_events.db)                      │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                     HUD VISUALIZATION & STREAMING                      │
│   - Dynamic HUD instrumentation overlay (lane corridor, 3D boxes)      │
│   - Base64 JPEG compression + Telemetry JSON serialization             │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        FASTAPI BACKEND SERVER                          │
│   - WebSocket: /ws/stream (annotated frames + real-time metadata)      │
│   - REST API: /api/stats, /api/config, /api/events, /api/source        │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   REACT COCKPIT WEB DASHBOARD (UI)                     │
│   - Live video stream display at ~30 FPS                               │
│   - Real-time gauge metrics (FPS, lateral offset, speed limits)        │
│   - Active safety incident banner and audio/visual risk alerts         │
│   - Historical telemetry graphs and paginated event table              │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Deep Dive: Perception Subsystems

### 2.1. Pedestrian Tracking & Danger Zone Kinematics

Implemented in `src/modules/pedestrian.py` and `src/utils/geometry.py`.

1. **Object Detection**:
   - Uses `yolov8n.pt` with confidence threshold ($conf \ge 0.40$) and NMS IoU threshold ($0.45$).
   - Filters exclusively for COCO class index `0` (`person`).
2. **ByteTrack Association**:
   - Maintains persistent track IDs across frames even during temporary occlusions or motion blur.
3. **Pinhole Distance Estimation**:
   - Estimates real-world distance $Z$ (in meters) from camera to pedestrian without requiring LiDAR:
     $$\text{Distance } Z = \frac{f \times H_{\text{real}}}{h_{\text{px}}}$$
     Where:
     - $f$: Camera focal length in pixels (default `800.0 px`).
     - $H_{\text{real}}$: Assumed average human height (default `1.70 m`).
     - $h_{\text{px}}$: Height of pedestrian bounding box in pixels ($y_2 - y_1$).
4. **Kinematic Velocity Calculation**:
   - Tracks centroid history over the last 30 frames.
   - Computes vertical velocity component:
     $$v_y = y_{\text{current}} - y_{\text{previous}}$$
   - If $v_y > 1.5\text{ px/frame}$, the pedestrian is classified as actively approaching the vehicle.
5. **Danger Zone Corridor Ray-Casting**:
   - Defines a trapezoidal polygonal ego-corridor directly in front of the vehicle.
   - Evaluates whether the pedestrian's ground contact point (bottom-center of bounding box) lies inside this polygon using the Jordan curve theorem (ray-casting algorithm).
6. **Risk Classification**:
   - **HIGH RISK**: Inside danger zone AND ($Z \le 8.0\text{ m}$ OR approaching fast).
   - **MEDIUM RISK**: Inside danger zone AND $8.0\text{ m} < Z \le 18.0\text{ m}$.
   - **LOW RISK**: Outside danger zone or far away.

---

### 2.2. Lane Marking Detection & Lateral Offset

Implemented in `src/modules/lanes.py` and `src/utils/geometry.py`.

1. **Region of Interest (ROI) & Color Filtering**:
   - Isolates the lower portion of the road ($top\_ratio = 0.55$).
   - Converts RGB to HLS color space:
     - Extracts white lines via Lightness threshold ($L \ge 195$).
     - Extracts yellow lines via Hue-Lightness-Saturation ranges ($H \in [15, 35]$, $S \ge 80$).
   - Computes Canny edges ($50, 150$) and combines with color masks.
2. **Bird's-Eye View (BEV) Perspective Transform**:
   - Applies homography warp matrix $M$ converting trapezoidal road perspective into top-down parallel view.
3. **Sliding-Window Polynomial Fitting**:
   - Computes column histogram of the lower half of the BEV binary image to find left and right lane line base peaks.
   - Iterates through 9 vertical sliding windows, recentering when pixel count exceeds `minpix` (40 px).
   - Fits 2nd-order quadratic polynomial to collected pixel coordinates:
     $$x(y) = A y^2 + B y + C$$
4. **Temporal Smoothing**:
   - A moving average queue over 5 frames smooths polynomial coefficients $(A, B, C)$ to eliminate jitter from road cracks or shadows.
5. **Lateral Offset & Curvature Calculation**:
   - **Ego-Vehicle Lateral Offset**:
     $$\text{Offset } = \left(\frac{x_{\text{left}} + x_{\text{right}}}{2} - \frac{\text{width}}{2}\right) \times m_x$$
     Where $m_x = \frac{3.70\text{ m}}{\text{lane width in pixels}}$. A positive offset indicates drift to the right, negative to the left.
   - **Radius of Curvature**:
     $$R = \frac{\left(1 + (2Ay + B)^2\right)^{3/2}}{|2A|}$$
6. **Lane Departure Warning (LDW)**:
   - When $|\text{Offset}| > 0.40\text{ m}$ for 5 or more consecutive frames, a `LANE_DEPARTURE` warning triggers.

---

### 2.3. Road Sign Recognition & GTSRB Classification

Implemented in `src/modules/signs.py`.

1. **Two-Stage Detection & Classification**:
   - **Stage 1 (Localization)**: YOLOv8 model detects candidate traffic sign bounding boxes.
   - **Stage 2 (Classification)**: Crops candidate bounding box, resizes to $48 \times 48\text{ px}$, and passes through a 43-class German Traffic Sign Recognition Benchmark (GTSRB) CNN classifier.
2. **Temporal Smoothing via Majority Voting**:
   - Maintains a sliding history of sign detections over 5 frames.
   - Requires consistent majority voting to confirm sign identity, preventing rapid flickering.
3. **Fallback Mechanism**:
   - If specialized GTSRB weights (`weights/sign_det.pt` and `weights/sign_cls.pt`) are not present, the module automatically activates an intelligent fallback using YOLOv8 COCO classes (e.g. Stop Sign, Traffic Light), ensuring complete out-of-the-box functionality without crashes.
4. **Telemetry HUD Updates**:
   - When a speed limit sign (e.g., 30, 50, 80 km/h) is identified with confidence $\ge 0.60$, the cockpit's speed limit display immediately reflects the updated regulation.

---

## 3. Decision & Alert Fusion Engine

Implemented in `src/core/fusion.py` and `src/api/db.py`.

The Fusion Engine correlates telemetry from all perception modules to generate prioritized safety warnings:

| Alert Identifier | Severity | Trigger Condition | System Action |
| :--- | :--- | :--- | :--- |
| `PEDESTRIAN_COLLISION_RISK` | **CRITICAL** | Pedestrian in danger corridor $\le 8.0\text{ m}$ or approaching fast | Flashing red HUD alert, logged to SQLite database |
| `PEDESTRIAN_AHEAD` | **WARNING** | Pedestrian in corridor between $8.0\text{ m}$ and $18.0\text{ m}$ | Amber advisory banner |
| `LANE_DEPARTURE` | **WARNING** | Lateral offset $> 0.40\text{ m}$ for $\ge 5$ frames | Directional lane departure warning |
| `STOP_SIGN_DETECTED` | **INFO** | Stop sign detected in visual field | Stop indicator HUD badge |
| `SPEED_LIMIT_SIGN` | **INFO** | Speed limit sign recognized ($conf \ge 0.60$) | Speed limit icon updated |

- **Cooldown Deduplication**: Enforces a configurable 3.0-second cooldown per alert type so drivers/operators are not spammed with duplicate notifications.
- **Persistent Database**: Every safety incident is saved to `adas_events.db` (SQLite) with timestamp, severity, alert type, and context metadata.

---

## 4. Backend API & WebSocket Streaming

Built using FastAPI, Uvicorn, and WebSockets (`src/api/main.py`, `src/api/routes.py`, `src/api/websocket.py`).

### 4.1. WebSocket Stream: `/ws/stream`
High-speed bidirectional connection streaming real-time video frames and metadata at 30 FPS:
```json
{
  "frame": "data:image/jpeg;base64,...",
  "fps": 28.5,
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
    {"label": "Speed limit (50km/h)", "conf": 0.92, "is_speed_limit": true, "speed_value": 50}
  ],
  "lane": {
    "detected": true,
    "offset_m": -0.12,
    "curvature_m": 1250.0,
    "departure": false
  },
  "alerts": [
    {"type": "PEDESTRIAN_COLLISION_RISK", "severity": "CRITICAL", "message": "Collision risk! Pedestrian #1 in danger zone (7.5m)."}
  ],
  "metrics": {
    "total_ms": 34.2,
    "pedestrian_ms": 16.1,
    "lanes_ms": 11.2,
    "signs_ms": 5.4,
    "fusion_ms": 0.8
  }
}
```

### 4.2. REST Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | Health check endpoint returning `{ "status": "ok" }` |
| `GET` | `/docs` | Interactive Swagger UI API documentation |
| `GET` | `/api/stats` | Pipeline FPS and per-module millisecond latencies |
| `GET` | `/api/config` | Retrieves active system configurations |
| `PUT` | `/api/config` | Live-updates thresholds (confidence, cooldowns, lane mode) |
| `POST`| `/api/start` | Starts perception worker thread |
| `POST`| `/api/stop` | Stops perception worker thread |
| `POST`| `/api/source` | Switches video source (`{"type":"file"\|"webcam"\|"rtsp", "path":"..."}`) |
| `GET` | `/api/events` | Paginated SQLite incident audit history (`limit`, `offset`, `severity`) |
| `POST`| `/api/upload` | Uploads `.mp4` dashcam video directly into `data/samples/` |

---

## 5. Frontend Cockpit Web Dashboard

Located in `frontend/`, built with **React 18 + Vite + Tailwind CSS + Lucide Icons + Recharts**:

- **Live Video Player**: Renders the annotated 30 FPS video stream over WebSockets with full-screen toggle.
- **Top Metrics Row**:
  - **Inference Performance**: Live FPS counter and end-to-end latency in milliseconds.
  - **Lane Position**: Lateral offset in meters with color-coded safety badges and curve radius.
  - **Speed Limit Badge**: Shows active speed limit or scanning status.
  - **Pedestrians Tracked**: Active count and danger zone tally.
- **Active Safety Incident Banner**: Dynamic card displaying active alerts with color-coded severity borders (Red for CRITICAL, Amber for WARNING, Green for Clear).
- **Telemetry History Charts**: Real-time sliding window graphs plotting lane offset drift and pedestrian counts.
- **Interactive Controls**: Buttons to pause/resume pipeline, toggle lane detection modes, switch input sources, and adjust detection thresholds.
- **Incident History Table**: Live paginated log of events recorded in the SQLite database.

---

## 6. Master Configuration Reference

Defined in `configs/config.yaml`:

```yaml
source:
  type: "file"                  # "file" | "webcam" | "rtsp"
  path: "data/samples/demo.mp4" # Path to video file, webcam device index (e.g. 0), or RTSP URL
  loop: true                    # Loop video playback continuously

inference:
  device: "auto"                # "cpu", "cuda", or "auto"
  imgsz: 640                    # Input resolution for YOLO
  half: false                   # FP16 half-precision on GPU

pedestrian:
  weights: "yolov8n.pt"         # COCO pretrained weights
  conf: 0.40                    # Confidence threshold
  iou: 0.45                     # NMS IoU threshold
  tracker: "bytetrack.yaml"     # ByteTrack tracking configuration
  focal_length_px: 800.0        # Camera focal length in pixels
  real_height_m: 1.70           # Average pedestrian height (meters)
  risk_distance_medium_m: 18.0  # Medium distance risk threshold
  risk_distance_high_m: 8.0     # Critical proximity threshold
  approach_velocity_px: 1.5     # Vertical approach velocity threshold

lanes:
  mode: "classical"             # "classical" or "deep"
  roi_top_ratio: 0.55           # Top of ROI trapezoid as ratio of frame height
  lane_width_m: 3.70            # Road lane width in meters
  sliding_windows: 9            # Number of sliding search windows
  window_margin: 60             # Search margin (+/- px)
  smoothing_frames: 5           # Moving average history for polynomial fit

alerts:
  lane_offset_m: 0.40           # Lane departure lateral offset threshold (meters)
  lane_consecutive_frames: 5    # Consecutive frames needed to trigger LDW
  cooldown_s: 3.0               # Minimum seconds between duplicate alerts
```

---

## 7. How to Run the Project (Step-by-Step)

### Option A: One-Click Startup Script (Recommended)

Two launcher scripts are provided in the project root:

1. **Using PowerShell**:
   Open PowerShell and run:
   ```powershell
   cd C:\Users\rushi\.gemini\antigravity\scratch\adas-project
   .\start.ps1
   ```
2. **Using Windows Command Prompt / Double-Click**:
   Double-click `start.bat` or run:
   ```cmd
   start.bat
   ```

*The script checks your Python environment, installs missing dependencies, starts the FastAPI backend, starts the Vite frontend, and automatically opens your browser to the cockpit.*

---

### Option B: Manual Terminal Execution

#### Terminal 1 — Start the Python FastAPI Backend:
```powershell
cd C:\Users\rushi\.gemini\antigravity\scratch\adas-project

# Activate your virtual environment (if using one)
.\venv\Scripts\Activate.ps1

# Install dependencies if not already installed
pip install -r requirements.txt

# Start backend server
uvicorn src.api.main:app --reload --port 8000
```
*Backend is now running at `http://localhost:8000`.*

#### Terminal 2 — Start the React Frontend Dashboard:
```powershell
cd C:\Users\rushi\.gemini\antigravity\scratch\adas-project\frontend

# Install dependencies if running for the first time
npm install

# Start Vite development server
npm run dev
```
*Frontend will open at `http://localhost:5173`.*

---

### Option C: Production Single-Port Mode (No Node.js needed after build)

You can compile the React frontend into static assets so that FastAPI serves everything on **port 8000**:

```powershell
# 1. Build frontend bundle
cd C:\Users\rushi\.gemini\antigravity\scratch\adas-project\frontend
npm run build

# 2. Run backend
cd ..
uvicorn src.api.main:app --port 8000
```
Open `http://localhost:8000` in your browser. Both the API and UI run from the single FastAPI instance!

---

### Option D: Docker Container

To run in a containerized environment:

```bash
docker build -t adas-cockpit .
docker run -p 8000:8000 adas-cockpit
```
Then navigate to `http://localhost:8000`.

---

## 8. Testing & Benchmarking

### Running the Test Suite
The project includes automated pytest tests covering geometry, lane detection, alert fusion, and API endpoints:

```powershell
python -m pytest tests/ -v
```

### Running the Benchmark Tool
To evaluate FPS, detection stability, and module latency breakdown:

```powershell
python benchmark.py --frames 100
```

Sample benchmark output:
```text
===========================================================================
 REAL-TIME ADAS VISION SYSTEM BENCHMARK & PERFORMANCE EVALUATION 
===========================================================================
Loaded Video: data/samples/demo.mp4 (300 frames)
Benchmarking next 100 frames...

---------------------------------------------------------------------------
BENCHMARK RESULTS TABLE
---------------------------------------------------------------------------
Overall Throughput:             28.4 FPS
Average Frame Latency:          35.2 ms
95th Percentile Latency:        41.0 ms
Lane Detection Success Rate:    98.0 %
Unique Pedestrians Tracked:     4
Sign Detections Total:          12
---------------------------------------------------------------------------
Latency Breakdown:
- Pedestrian Tracking (YOLO):   16.8 ms (47.7%)
- Lane Marking Detection:       11.4 ms (32.4%)
- Sign Localization & Classify:  4.8 ms (13.6%)
- Decision & Alert Fusion:       0.9 ms (2.6%)
- Visual HUD Drawing & Overlay:  1.3 ms (3.7%)
---------------------------------------------------------------------------
```

---

## 9. Troubleshooting & Common Questions

### Why does the dashboard say "🔴 Disconnected 0.0 FPS" / "Waiting for WebSocket video stream"?
The React frontend is loaded in your browser, but the **FastAPI backend is not running**. Start the backend via `uvicorn src.api.main:app --port 8000` (or run `.\start.ps1`). As soon as the server starts, the status turns green: `🟢 Connected`.

### How do I use my Webcam instead of the demo video?
1. In the Web Cockpit: Click **Input Controls** $\to$ Select **Webcam** $\to$ Device `0` $\to$ Click **Switch Source**.
2. Or via `configs/config.yaml`:
   ```yaml
   source:
     type: "webcam"
     path: 0
   ```

### How do I run on GPU (NVIDIA CUDA)?
Ensure PyTorch with CUDA is installed (`torch.cuda.is_available() == True`). In `configs/config.yaml`, set:
```yaml
inference:
  device: "cuda"
  half: true
```

### Where are safety incidents stored?
All safety events are stored in `adas_events.db` (SQLite). You can view them in the dashboard table or query them via `GET /api/events` or any SQLite viewer.

