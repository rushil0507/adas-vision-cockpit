"""FastAPI Application Entry Point for Real-Time ADAS Vision System."""

import asyncio
import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from src.core.pipeline import ADASPipeline
from src.api.routes import router as api_router
from src.api.websocket import manager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("adas.server")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize master pipeline
    loop = asyncio.get_running_loop()
    manager.set_loop(loop)

    config_path = os.getenv("ADAS_CONFIG", "configs/config.yaml")
    pipeline = ADASPipeline(config_path=config_path)
    app.state.pipeline = pipeline

    # Hook frame callback to WebSocket dispatcher
    pipeline.add_callback(manager.dispatch_from_thread)

    # Automatically start pipeline if demo video exists or configured
    try:
        pipeline.start()
        logger.info("ADAS Pipeline started automatically at server launch.")
    except Exception as e:
        logger.warning(f"Could not auto-start pipeline on launch: {e}")

    yield

    # Shutdown: Stop pipeline
    logger.info("Shutting down ADAS Pipeline...")
    pipeline.stop()


app = FastAPI(
    title="Real-Time ADAS Vision API",
    description="Dashcam Road Sign Localization, Lane Marking Detection, and Pedestrian Tracking",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for local Vite development server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include REST API endpoints
app.include_router(api_router, prefix="/api")


@app.websocket("/ws/stream")
async def websocket_stream(websocket: WebSocket):
    """Real-time streaming WebSocket sending annotated video frame + detection metadata."""
    await manager.connect(websocket)

    # Immediately push latest frame result if available
    latest = app.state.pipeline.get_latest_result()
    if latest:
        try:
            await websocket.send_json(latest)
        except Exception:
            pass

    try:
        while True:
            # Keep socket alive and handle any incoming client messages / heartbeat
            msg = await websocket.receive_text()
            if msg == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.warning(f"WebSocket client error: {e}")
        manager.disconnect(websocket)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "ADAS Vision API"}


# Serve compiled frontend dashboard if built
frontend_dist = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "frontend",
    "dist",
)
if os.path.exists(frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = os.path.join(frontend_dist, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(frontend_dist, "index.html"))

