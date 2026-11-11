"""Threaded video capture and frame grabber with bounded queue."""

import time
import queue
import threading
import logging
from typing import Optional, Tuple, Union
import cv2
import numpy as np

logger = logging.getLogger(__name__)


class FrameGrabber:
    """
    Captures frames asynchronously in a dedicated background thread.
    Uses a bounded queue (default size 2) that drops the oldest frames when full,
    guaranteeing that inference workers always receive the freshest frame with lowest latency.
    """

    def __init__(
        self,
        source: Union[str, int],
        queue_size: int = 2,
        loop: bool = True,
        target_fps: Optional[float] = None,
    ):
        self.source = source
        self.queue_size = max(1, queue_size)
        self.loop = loop
        self.target_fps = target_fps

        self.cap: Optional[cv2.VideoCapture] = None
        self.queue: queue.Queue = queue.Queue(maxsize=self.queue_size)
        self.running = False
        self.thread: Optional[threading.Thread] = None

        self.frame_width = 0
        self.frame_height = 0
        self.native_fps = 30.0
        self.total_frames = 0
        self.frame_count = 0

    def start(self) -> bool:
        """Initializes VideoCapture and starts background capture thread."""
        if self.running:
            return True

        # Parse source (integer if webcam index string like '0')
        src = self.source
        if isinstance(src, str) and src.isdigit():
            src = int(src)

        self.cap = cv2.VideoCapture(src)
        if not self.cap.isOpened():
            logger.error(f"Failed to open video source: {self.source}")
            return False

        self.frame_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 1280
        self.frame_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 720
        self.native_fps = float(self.cap.get(cv2.CAP_PROP_FPS)) or 30.0
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))

        self.running = True
        self.thread = threading.Thread(target=self._capture_worker, daemon=True)
        self.thread.start()
        logger.info(
            f"FrameGrabber started for source={self.source} "
            f"({self.frame_width}x{self.frame_height} @ {self.native_fps:.1f}fps)"
        )
        return True

    def _capture_worker(self):
        """Worker loop reading frames continuously."""
        frame_interval = 1.0 / self.native_fps if self.native_fps > 0 else 0.033
        if self.target_fps and self.target_fps > 0:
            frame_interval = 1.0 / self.target_fps

        while self.running and self.cap and self.cap.isOpened():
            start_time = time.perf_counter()
            ret, frame = self.cap.read()

            if not ret or frame is None:
                if self.loop and self.total_frames > 0:
                    # Rewind to the beginning for video files
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    ret, frame = self.cap.read()
                    if not ret or frame is None:
                        logger.warning("Failed to rewind video source, ending capture.")
                        break
                else:
                    logger.info("End of video stream reached.")
                    break

            self.frame_count += 1

            # Put into bounded queue; if full, drop oldest
            if self.queue.full():
                try:
                    self.queue.get_nowait()
                except queue.Empty:
                    pass

            try:
                self.queue.put_nowait(frame)
            except queue.Full:
                pass

            # Throttle if reading from a file to avoid running at 1000 FPS
            if isinstance(self.source, str) and not self.source.startswith("rtsp://"):
                elapsed = time.perf_counter() - start_time
                sleep_time = frame_interval - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)

        self.running = False

    def read(self, timeout: float = 0.5) -> Tuple[bool, Optional[np.ndarray]]:
        """
        Retrieves the newest frame from the queue.
        Returns:
            (success, frame)
        """
        if not self.running and self.queue.empty():
            return False, None

        try:
            frame = self.queue.get(timeout=timeout)
            return True, frame
        except queue.Empty:
            return False, None

    def stop(self):
        """Stops the grabber thread and releases the video device."""
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
        if self.cap:
            self.cap.release()
            self.cap = None

        # Drain queue
        while not self.queue.empty():
            try:
                self.queue.get_nowait()
            except queue.Empty:
                break
        logger.info(f"FrameGrabber stopped for source={self.source}")

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

