"""FastAPI REST routes for pipeline control, telemetry, configuration, and event query."""

import os
import shutil
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, UploadFile, File, Query, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter()


class SourceRequest(BaseModel):
    type: str = Field(..., description="'file', 'webcam', or 'rtsp'")
    path: str = Field(..., description="File path, device index (e.g. '0'), or stream URL")


class ConfigUpdateRequest(BaseModel):
    pedestrian: Optional[Dict[str, Any]] = None
    lanes: Optional[Dict[str, Any]] = None
    signs: Optional[Dict[str, Any]] = None
    alerts: Optional[Dict[str, Any]] = None


@router.post("/start")
async def start_pipeline(request: Request):
    """Starts ADAS vision pipeline."""
    pipeline = request.app.state.pipeline
    success = pipeline.start()
    return {"status": "started" if success else "failed", "running": pipeline.running}


@router.post("/stop")
async def stop_pipeline(request: Request):
    """Stops ADAS vision pipeline."""
    pipeline = request.app.state.pipeline
    pipeline.stop()
    return {"status": "stopped", "running": False}


@router.post("/source")
async def set_source(body: SourceRequest, request: Request):
    """Switches input source (video file, camera device index, or RTSP stream)."""
    pipeline = request.app.state.pipeline
    pipeline.set_source(source_type=body.type, path=body.path)
    return {"status": "source_updated", "source": {"type": body.type, "path": body.path}}


@router.get("/stats")
async def get_stats(request: Request):
    """Returns FPS, latency measurements, and module runtime timings."""
    pipeline = request.app.state.pipeline
    return pipeline.get_stats()


@router.get("/config")
async def get_config(request: Request):
    """Returns the current pipeline configuration."""
    pipeline = request.app.state.pipeline
    return pipeline.config


@router.put("/config")
async def update_config(body: ConfigUpdateRequest, request: Request):
    """Updates runtime threshold configuration dynamically."""
    pipeline = request.app.state.pipeline
    updates = body.model_dump(exclude_none=True)
    pipeline.update_config(updates)
    return {"status": "updated", "config": pipeline.config}


@router.get("/events")
async def get_events(
    request: Request,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    severity: Optional[str] = Query(None, description="INFO, WARNING, or CRITICAL"),
):
    """Retrieves paginated alert and incident history from SQLite."""
    db = request.app.state.pipeline.db
    events = db.get_events(limit=limit, offset=offset, severity=severity)
    total = db.get_event_count(severity=severity)
    return {
        "events": events,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.post("/upload")
async def upload_video(file: UploadFile = File(...)):
    """Uploads a dashcam MP4/AVI video file to data/samples/ for playback."""
    upload_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "data",
        "samples",
    )
    os.makedirs(upload_dir, exist_ok=True)
    destination_path = os.path.join(upload_dir, file.filename)

    try:
        with open(destination_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        return {
            "status": "success",
            "filename": file.filename,
            "path": os.path.relpath(destination_path),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload video: {str(e)}")
