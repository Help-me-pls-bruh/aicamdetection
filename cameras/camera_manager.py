"""
Camera Manager - handles webcam and RTSP CCTV streams.
Supports TP-Link Tapo C200/C210 via RTSP.
"""

import cv2
import threading
import time


class CameraStream:
    def __init__(self, source=0, name="Camera_0"):
        self.source = source
        self.name = name
        self.cap = None
        self.frame = None
        self.is_running = False
        self.thread = None
        self.fps = 0
        self.frame_count = 0
        self.lock = threading.Lock()

    def start(self):
        self.cap = cv2.VideoCapture(self.source)
        if not self.cap.isOpened():
            print(f"[CAM] Failed to open: {self.name} ({self.source})")
            return False

        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        if isinstance(self.source, str) and "rtsp" in self.source.lower():
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        self.is_running = True
        self.thread = threading.Thread(target=self._read_loop, daemon=True)
        self.thread.start()
        print(f"[CAM] Started: {self.name}")
        return True

    def _read_loop(self):
        fps_timer = time.time()
        fps_count = 0

        while self.is_running:
            ret, frame = self.cap.read()
            if not ret:
                time.sleep(0.1)
                self.cap.release()
                self.cap = cv2.VideoCapture(self.source)
                continue

            with self.lock:
                self.frame = frame
                self.frame_count += 1

            fps_count += 1
            elapsed = time.time() - fps_timer
            if elapsed >= 1.0:
                self.fps = fps_count / elapsed
                fps_count = 0
                fps_timer = time.time()

    def get_frame(self):
        with self.lock:
            if self.frame is not None:
                return True, self.frame.copy()
        return False, None

    def stop(self):
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=3)
        if self.cap:
            self.cap.release()
        print(f"[CAM] Stopped: {self.name}")


class CameraManager:
    def __init__(self):
        self.cameras = {}

    def add_webcam(self, camera_index=0, name=None):
        name = name or f"Webcam_{camera_index}"
        cam = CameraStream(source=camera_index, name=name)
        self.cameras[name] = cam
        return name

    def add_rtsp(self, rtsp_url, name=None):
        """
        Add RTSP camera (e.g. TP-Link Tapo).
        URL format: rtsp://username:password@192.168.x.x:554/stream1
        """
        name = name or f"RTSP_{len(self.cameras)}"
        cam = CameraStream(source=rtsp_url, name=name)
        self.cameras[name] = cam
        return name

    def add_video_file(self, file_path, name=None):
        name = name or f"Video_{len(self.cameras)}"
        cam = CameraStream(source=file_path, name=name)
        self.cameras[name] = cam
        return name

    def start_all(self):
        for name, cam in self.cameras.items():
            cam.start()

    def start_camera(self, name):
        if name in self.cameras:
            return self.cameras[name].start()
        return False

    def get_frame(self, name):
        if name in self.cameras:
            return self.cameras[name].get_frame()
        return False, None

    def stop_all(self):
        for cam in self.cameras.values():
            cam.stop()

    def stop_camera(self, name):
        if name in self.cameras:
            self.cameras[name].stop()

    def list_cameras(self):
        return [
            {
                "name": name,
                "source": cam.source,
                "running": cam.is_running,
                "fps": round(cam.fps, 1),
                "frames": cam.frame_count,
            }
            for name, cam in self.cameras.items()
        ]
