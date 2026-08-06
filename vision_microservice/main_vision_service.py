# -*- coding: utf-8 -*-
"""
===================================================================================
  Dhatri Vision Microservice — main_vision_service.py
===================================================================================

  This is the core vision service for the Dhatri AI assistant. It provides:

    1. Real-time webcam capture
    2. Object detection using YOLO v11
    3. Face recognition using dlib (via the face_recognition library)
    4. A FastAPI server that streams detection results via SSE (Server-Sent Events)
    5. An optional local GUI window for live visual feedback

  Architecture Overview:
  ─────────────────────
  The service uses a decoupled multi-threaded architecture:

    [Camera Thread]  ──frames──►  [Inference Thread]  ──results──►  [FastAPI SSE]
          │                              │
          └──frames──► [Display Queue] ──► [Main GUI Thread (optional)]

  - Camera Thread:    Grabs raw frames from the webcam at full speed
  - Inference Thread: Runs YOLO + face_recognition on every Nth frame
  - Main GUI Thread:  Renders annotated frames in a local OpenCV window
  - FastAPI Server:   Exposes /stream (SSE) and /status (REST) endpoints

  GPU Acceleration:
  ─────────────────
  - YOLO object detection uses NVIDIA GPU via PyTorch CUDA when available
  - Face detection uses dlib's CNN model when dlib is compiled with CUDA support,
    otherwise falls back to the faster (but less accurate) HOG model
  - All GPU detection happens at startup with clear diagnostic logging

===================================================================================
"""

import os

# ── Ultralytics Telemetry Suppression ────────────────────────────────────────
# These environment variables MUST be set BEFORE importing ultralytics,
# otherwise the library will attempt to phone home on every startup.
os.environ["YOLO_VERBOSE"] = "False"
os.environ["YOLO_SYNC"] = "False"

from ultralytics import settings
settings.update({'sync': False})  # Disable Ultralytics analytics/sync

from ultralytics import YOLO
import cv2
import face_recognition
import numpy as np
import time
import json
import threading
import queue
import sys
from datetime import datetime

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import asyncio


# =============================================================================
#  GPU DETECTION & DIAGNOSTICS
# =============================================================================
# We probe for NVIDIA GPU support at startup and store the results globally.
# Two independent GPU paths exist:
#   1. PyTorch CUDA  → used by YOLO for object detection
#   2. dlib CUDA     → used by face_recognition for CNN-based face detection
#
# Both are optional — the system falls back to CPU gracefully.

def detect_gpu_capabilities():
    """Probes the system for GPU support and returns a diagnostics dict.

    Returns a dict with keys:
        - yolo_device:        int (GPU index) or "cpu"
        - face_model:         "cnn" (GPU) or "hog" (CPU)
        - torch_cuda:         bool — whether PyTorch sees CUDA
        - dlib_cuda:          bool — whether dlib was compiled with CUDA
        - gpu_name:           str or None — human-readable GPU name
        - gpu_vram_mb:        int or None — total VRAM in MB
    """
    result = {
        "yolo_device": "cpu",
        "face_model": "hog",     # Default: CPU-based HOG face detector
        "torch_cuda": False,
        "dlib_cuda": False,
        "gpu_name": None,
        "gpu_vram_mb": None,
    }

    # ── Step 1: Check PyTorch CUDA (for YOLO) ────────────────────────────
    try:
        import torch
        if torch.cuda.is_available() and torch.cuda.device_count() > 0:
            # Smoke test: actually allocate a tensor on GPU to catch driver issues
            torch.tensor([1.0]).cuda()
            result["torch_cuda"] = True
            result["yolo_device"] = 0  # Ultralytics expects int 0 for first GPU

            # Grab human-readable GPU info for the diagnostics banner
            result["gpu_name"] = torch.cuda.get_device_name(0)
            result["gpu_vram_mb"] = int(
                torch.cuda.get_device_properties(0).total_mem / (1024 * 1024)
            )
    except Exception:
        # Any failure (no torch, no driver, etc.) → stay on CPU
        pass

    # ── Step 2: Check dlib CUDA (for face_recognition CNN model) ─────────
    try:
        import dlib
        # dlib exposes DLIB_USE_CUDA as a boolean if compiled with CUDA support
        if getattr(dlib, "DLIB_USE_CUDA", False) and dlib.cuda.get_num_devices() > 0:
            result["dlib_cuda"] = True
            result["face_model"] = "cnn"  # Use CNN face detector (GPU-accelerated)
    except Exception:
        # dlib without CUDA, or dlib not installed — stay on HOG
        pass

    return result


def print_gpu_diagnostics(gpu_info):
    """Prints a clear startup banner showing GPU status.

    This is the first thing a user sees in the terminal — it should
    immediately tell them whether their NVIDIA GPU is being used.
    Falls back to a plain ASCII banner if the terminal can't render Unicode.
    """
    try:
        # ── Fancy Unicode banner (works on modern terminals) ─────────────
        divider = "=" * 62
        print(f"\n+{divider}+")
        print(f"|  [*] DHATRI VISION -- GPU DIAGNOSTICS{' ' * 24}|")
        print(f"+{divider}+")

        # GPU hardware info
        if gpu_info["gpu_name"]:
            name = gpu_info["gpu_name"]
            vram = gpu_info["gpu_vram_mb"]
            print(f"|  GPU Found  : {name:<47}|")
            print(f"|  VRAM       : {vram} MB{' ' * (44 - len(str(vram)))}|")
        else:
            print(f"|  GPU Found  : {'None detected':<47}|")

        print(f"+{divider}+")

        # YOLO (PyTorch CUDA) status
        if gpu_info["torch_cuda"]:
            yolo_status = "[OK] NVIDIA GPU (PyTorch CUDA)"
        else:
            yolo_status = "[--] CPU only (PyTorch CUDA not available)"
        print(f"|  YOLO       : {yolo_status:<47}|")

        # Face recognition (dlib CUDA) status
        if gpu_info["dlib_cuda"]:
            face_status = "[OK] NVIDIA GPU (dlib CUDA CNN)"
        else:
            face_status = "[--] CPU (HOG model -- dlib CUDA not compiled)"
        print(f"|  Face Detect: {face_status:<47}|")

        print(f"+{divider}+")

        # Overall verdict
        if gpu_info["torch_cuda"] and gpu_info["dlib_cuda"]:
            verdict = ">>> FULL GPU ACCELERATION ACTIVE <<<"
        elif gpu_info["torch_cuda"]:
            verdict = ">>> PARTIAL GPU -- YOLO on GPU, faces on CPU <<<"
        else:
            verdict = ">>> CPU ONLY -- install CUDA toolkit for GPU boost <<<"
        print(f"|  {verdict:<60}|")

        print(f"+{divider}+\n")

    except (UnicodeEncodeError, UnicodeDecodeError):
        # ── ASCII fallback for terminals that can't handle Unicode ────────
        print("\n" + "=" * 64)
        print("  DHATRI VISION - GPU DIAGNOSTICS")
        print("=" * 64)
        gpu_name = gpu_info['gpu_name'] or 'None detected'
        print(f"  GPU       : {gpu_name}")
        if gpu_info['gpu_vram_mb']:
            print(f"  VRAM      : {gpu_info['gpu_vram_mb']} MB")
        print(f"  YOLO      : {'GPU (CUDA)' if gpu_info['torch_cuda'] else 'CPU'}")
        print(f"  Face Det. : {'GPU (CNN)' if gpu_info['dlib_cuda'] else 'CPU (HOG)'}")
        if gpu_info['torch_cuda'] and gpu_info['dlib_cuda']:
            print("  Status    : FULL GPU ACCELERATION")
        elif gpu_info['torch_cuda']:
            print("  Status    : PARTIAL GPU (YOLO=GPU, Faces=CPU)")
        else:
            print("  Status    : CPU ONLY")
        print("=" * 64 + "\n")


# ── Run GPU detection at module load time ────────────────────────────────────
# This happens once, before any threads start. The results are stored globally
# and referenced by all threads throughout the service's lifetime.
GPU_INFO = detect_gpu_capabilities()
print_gpu_diagnostics(GPU_INFO)

# Extract the two key values used throughout the inference loop:
SAFE_DEVICE = GPU_INFO["yolo_device"]      # int(0) for GPU, "cpu" for CPU
FACE_DETECT_MODEL = GPU_INFO["face_model"] # "cnn" for GPU, "hog" for CPU


# =============================================================================
#  CONFIGURATION CONSTANTS
# =============================================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, "models")
YOLO_MODEL_PATH = os.path.join(MODELS_DIR, "yolo11s.pt")  # YOLOv11-small weights
UNKNOWN_FACES_DIR = os.path.join(BASE_DIR, "unknown_faces")  # Auto-saved unknown face crops
KNOWN_FACES_DIR = os.path.join(BASE_DIR, "known_faces")  # Reference images for recognition

# How many frames to skip between inference runs.
# Higher = less CPU/GPU load, lower = more responsive detection.
INFERENCE_EVERY_N_FRAMES = 6

# Face distance tolerance for matching.
# Lower values are stricter (fewer false positives, more false negatives).
# 0.6 is the library default; 0.5 is strict; 0.7 is lenient.
FACE_MATCH_TOLERANCE = 0.6

# ── Ensure required directories exist ────────────────────────────────────────
os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(UNKNOWN_FACES_DIR, exist_ok=True)
os.makedirs(KNOWN_FACES_DIR, exist_ok=True)


# =============================================================================
#  GLOBAL SHARED STATE
# =============================================================================
# These variables are shared across threads. Access is synchronized via
# threading.Event and threading.Lock to avoid race conditions.

# The latest detection results, broadcast to SSE clients via /stream endpoint.
latest_broadcast_data = {
    "timestamp": time.time(),
    "detected_objects": [],      # List of unique object class names (e.g., ["person", "laptop"])
    "recognized_faces": [],      # List of recognized person names (e.g., ["Hardik"])
    "unknown_faces_count": 0     # Count of faces detected but not recognized
}

# Event flag: set by inference thread when new data is available,
# cleared by SSE generator after broadcasting it.
latest_data_event = threading.Event()

# Event flag: set to signal all threads to gracefully shut down.
shutdown_event = threading.Event()


# =============================================================================
#  INTER-THREAD QUEUES
# =============================================================================
# Queues decouple frame production (camera) from consumption (inference, display).
# maxsize prevents unbounded memory growth if a consumer falls behind.

# Frames waiting to be rendered in the GUI window.
display_queue = queue.Queue(maxsize=2)

# Frames waiting to be processed by the inference thread.
inference_queue = queue.Queue(maxsize=1)

# Bounding box annotations produced by inference, consumed by the display thread.
# Protected by a Lock since both threads access it concurrently.
shared_annotations = {
    "lock": threading.Lock(),
    "boxes": []  # List of dicts: {"box": [x1, y1, x2, y2], "label": str, "color": (B, G, R)}
}


# =============================================================================
#  FASTAPI APPLICATION SETUP
# =============================================================================

app = FastAPI(title="Vision Microservice API")

# Allow all CORS origins so the GUI frontend and brain can connect freely.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
#  WORKER THREAD MANAGEMENT
# =============================================================================
# The camera and inference threads are managed as a pair. They can be
# started and stopped together, which is useful for graceful restarts.

_workers = []  # Holds references to active worker threads


def start_workers():
    """Spins up the camera capture and inference worker threads.

    If workers are already running, they are stopped first to avoid
    duplicate threads competing for the same resources.
    """
    global _workers
    if _workers:
        stop_workers()

    shutdown_event.clear()

    # Camera thread: captures raw frames from the webcam
    t1 = threading.Thread(target=camera_thread, daemon=True)
    # Inference thread: runs YOLO + face recognition on queued frames
    t2 = threading.Thread(target=inference_worker, daemon=True)

    t1.start()
    t2.start()
    _workers.extend([t1, t2])


def stop_workers():
    """Signals all worker threads to stop and waits for them to exit.

    Uses a short timeout to avoid blocking indefinitely if a thread is stuck.
    """
    global _workers
    shutdown_event.set()
    for t in _workers:
        if t.is_alive():
            t.join(timeout=2.0)
    _workers.clear()


# =============================================================================
#  CAMERA CAPTURE THREAD
# =============================================================================

def camera_thread():
    """Continuously grabs frames from the webcam in a background thread.

    Frames are pushed to two queues:
      - inference_queue: for the AI inference thread (every Nth frame)
      - display_queue:   for the GUI rendering loop (every frame)

    Both queues use a "drop oldest" policy when full, ensuring the system
    always processes the most recent frame rather than building up lag.
    """
    print("[Dhatri Vision] Starting webcam capture thread...")

    # cv2.CAP_DSHOW (DirectShow) prevents some hanging issues on Windows.
    # If it fails, we fall back to the default backend.
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        cap = cv2.VideoCapture(0)  # Fallback to default backend

    if not cap.isOpened():
        print("[Dhatri Vision] ERROR: Could not open webcam.")
        shutdown_event.set()
        return

    # Request a 640x480 resolution from the camera hardware.
    # The camera may ignore this if it doesn't support this exact resolution.
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    frame_count = 0

    while not shutdown_event.is_set():
        ret, frame = cap.read()
        if not ret:
            # Camera glitch — brief sleep to avoid busy-spinning, then retry
            time.sleep(0.01)
            continue

        # Ensure consistent resolution regardless of camera output
        height, width = frame.shape[:2]
        if width > 640 or height > 480:
            frame = cv2.resize(frame, (640, 480))

        frame_count += 1

        # ── Push to inference queue (every Nth frame) ────────────────────
        # We only run heavy AI inference every N frames to save compute.
        # If the inference thread hasn't consumed the previous frame yet,
        # we drop the old one and replace it with the newest frame.
        if frame_count % INFERENCE_EVERY_N_FRAMES == 0:
            if inference_queue.full():
                try:
                    inference_queue.get_nowait()  # Drop stale frame
                except queue.Empty:
                    pass
            inference_queue.put(frame.copy())  # .copy() to avoid shared buffer issues

        # ── Push to display queue (every frame) ──────────────────────────
        # The GUI loop wants every frame for smooth video playback.
        # Same "drop oldest" policy as above.
        if display_queue.full():
            try:
                display_queue.get_nowait()
            except queue.Empty:
                pass
        display_queue.put(frame)

    cap.release()
    print("[Dhatri Vision] Camera capture thread terminated.")


# =============================================================================
#  GLOBAL MODEL CACHES
# =============================================================================
# Heavy models (YOLO, face encodings) are loaded once and kept in memory
# for the entire lifetime of the service. This avoids re-loading on every
# inference frame, which would be prohibitively slow.

_yolo_model = None              # The loaded YOLO model instance
_known_face_names = []           # Parallel list of person names
_known_face_encodings = []       # Parallel list of 128-dim face encoding vectors
_dynamic_encodings = {}          # Runtime-learned encodings: {name: [encoding, ...]}
MAX_DYNAMIC_ENCODINGS = 5        # Max dynamic encodings per person (prevents memory creep)
_models_loaded = False           # Guard flag to prevent double-loading


# =============================================================================
#  FACE DISTANCE → CONFIDENCE CONVERSION
# =============================================================================

def face_distance_to_confidence(face_distance, face_match_threshold=0.6):
    """Converts a raw face distance value to a human-readable confidence %.

    The face_recognition library returns a euclidean distance where:
      - 0.0 = identical face
      - 0.6 = default match threshold (faces below this are considered a "match")
      - 1.0+ = completely different face

    The naive formula `(1.0 - distance) * 100` is misleading because a
    perfectly valid match at distance 0.5 would display as only "50%",
    which sounds terrible to a user.

    This function uses a non-linear curve that maps distances more intuitively:
      - distance 0.3 → ~96%  (very confident match)
      - distance 0.4 → ~93%
      - distance 0.5 → ~87%  (solid match, was showing as 50% before!)
      - distance 0.6 → ~50%  (borderline, at the tolerance threshold)

    Args:
        face_distance: Raw euclidean distance from face_recognition.face_distance()
        face_match_threshold: The tolerance value used for matching (default 0.6)

    Returns:
        Integer percentage (0–100) representing match confidence.
    """
    if face_distance > face_match_threshold:
        # Beyond the threshold — linearly taper down to 0%
        range_val = (1.0 - face_match_threshold)
        linear_val = (1.0 - face_distance) / (range_val * 2.0)
        return max(0, int(linear_val * 100))
    else:
        # Within the threshold — apply non-linear boost
        range_val = face_match_threshold
        linear_val = 1.0 - (face_distance / (range_val * 2.0))
        confidence = linear_val + ((1.0 - linear_val) * ((linear_val - 0.5) * 2) ** 0.2)
        return min(100, int(confidence * 100))


# =============================================================================
#  MODEL LOADING
# =============================================================================

def load_models():
    """Loads YOLO model and known face encodings into global memory.

    This function is called once by the inference worker thread. It:
      1. Loads the YOLO model weights from disk
      2. Scans the known_faces/ directory for reference face images
      3. Computes 128-dimensional face encodings for each reference image

    Known faces can be organized in two ways (both work simultaneously):
      - Folder-per-person:  known_faces/PersonName/*.jpg   (multiple angles)
      - Flat files:         known_faces/PersonName.jpg     (single image, legacy)

    The folder-per-person approach is recommended because having 3–5 reference
    photos from different angles dramatically improves recognition accuracy.
    """
    global _yolo_model, _known_face_names, _known_face_encodings, _models_loaded

    # Guard: only load once
    if _models_loaded:
        return

    print("[Dhatri Vision] Initializing AI models...")

    # ── Load YOLO model ──────────────────────────────────────────────────
    if not os.path.exists(YOLO_MODEL_PATH):
        print(f"[Dhatri Vision] CRITICAL ERROR: YOLO model not found at {YOLO_MODEL_PATH}")
        print("[Dhatri Vision] Please run setup_assets.py to download it.")
        return

    try:
        _yolo_model = YOLO(YOLO_MODEL_PATH)
        device_label = "GPU" if SAFE_DEVICE != "cpu" else "CPU"
        print(f"[Dhatri Vision] YOLO model loaded — running on {device_label}")
    except Exception as e:
        print(f"[Dhatri Vision] Error loading YOLO model: {e}")
        return

    # ── Load known face encodings ────────────────────────────────────────
    _known_face_names.clear()
    _known_face_encodings.clear()
    print(f"[Dhatri Vision] Scanning {KNOWN_FACES_DIR} for known faces...")

    def _load_face_image(filepath, label):
        """Encode a single face image and append to the global lists.

        Args:
            filepath: Absolute path to the image file
            label: The person's name to associate with this encoding

        Returns:
            True if a face was found and encoded, False otherwise.
        """
        image = face_recognition.load_image_file(filepath)
        encodings = face_recognition.face_encodings(image)
        if len(encodings) > 0:
            _known_face_names.append(label)
            _known_face_encodings.append(encodings[0])
            return True
        return False

    # Iterate over entries in the known_faces directory
    for entry in os.listdir(KNOWN_FACES_DIR):
        entry_path = os.path.join(KNOWN_FACES_DIR, entry)

        if os.path.isdir(entry_path):
            # ── Folder-per-person layout ─────────────────────────────────
            # Each subfolder name is a person's name, and every image inside
            # is a reference photo (front, side, different lighting, etc.)
            name = entry
            loaded_count = 0
            for img_file in os.listdir(entry_path):
                if img_file.lower().endswith(('.png', '.jpg', '.jpeg')):
                    img_path = os.path.join(entry_path, img_file)
                    if _load_face_image(img_path, name):
                        loaded_count += 1
                    else:
                        print(f"  -> Warning: No face found in {entry}/{img_file}")
            if loaded_count > 0:
                print(f"  -> Learned face: {name} ({loaded_count} reference image{'s' if loaded_count > 1 else ''})")
            else:
                print(f"  -> Warning: No usable face images in folder {entry}/")

        elif entry.lower().endswith(('.png', '.jpg', '.jpeg')):
            # ── Flat file layout (legacy/simple) ─────────────────────────
            # The filename (without extension) is used as the person's name.
            name = os.path.splitext(entry)[0]
            if _load_face_image(entry_path, name):
                print(f"  -> Learned face: {name} (1 reference image)")
            else:
                print(f"  -> Warning: No face found in {entry}")

    # Summary
    unique_names = len(set(_known_face_names))
    print(
        f"[Dhatri Vision] Loaded {len(_known_face_encodings)} encodings for "
        f"{unique_names} known {'person' if unique_names == 1 else 'people'} "
        f"into global memory."
    )

    # Log face detection model being used
    if FACE_DETECT_MODEL == "cnn":
        print("[Dhatri Vision] Face detection: using CNN model (NVIDIA GPU accelerated)")
    else:
        print("[Dhatri Vision] Face detection: using HOG model (CPU)")

    _models_loaded = True


# =============================================================================
#  INFERENCE WORKER THREAD
# =============================================================================

def inference_worker():
    """Background thread that runs the AI inference pipeline.

    This is where the heavy computation happens. For each frame pulled
    from the inference_queue, this thread:

      1. Optionally enhances brightness/contrast for poor lighting
      2. Runs YOLO object detection to find objects and people
      3. If a person is detected, runs face recognition to identify them
      4. Updates shared_annotations for the GUI and latest_broadcast_data for SSE

    The face recognition pipeline:
      - Detect face locations using HOG (CPU) or CNN (GPU) model
      - Compute 128-dim face encodings for each detected face
      - Compare against all known encodings (static + dynamic)
      - The closest match below the tolerance threshold is accepted
      - High-confidence matches are cached as "dynamic encodings" to improve
        recognition from different angles over time (self-learning)
    """
    global latest_broadcast_data, _yolo_model, _known_face_names, _known_face_encodings, _dynamic_encodings

    # Load AI models in this thread (not the main thread) to ensure the
    # CUDA context is owned by the thread that will use it. CUDA contexts
    # are thread-local — creating them in one thread and using in another
    # causes crashes.
    if not _models_loaded:
        load_models()

    if shutdown_event.is_set() or not _models_loaded:
        return

    print("[Dhatri Vision] Inference worker started — waiting for frames...")

    # Create local references for faster access inside the hot loop
    yolo_model = _yolo_model
    known_face_names = _known_face_names
    known_face_encodings = _known_face_encodings
    dynamic_encodings = _dynamic_encodings

    while not shutdown_event.is_set():
        # ── Wait for a frame from the camera thread ──────────────────────
        try:
            frame = inference_queue.get(timeout=0.5)
        except queue.Empty:
            # No frame available — loop back and check shutdown_event
            continue

        current_timestamp = time.time()
        detected_objects = []     # Unique object class names for this frame
        recognized_faces = []     # Unique recognized person names for this frame
        unknown_faces_count = 0   # Number of unrecognized faces in this frame
        new_annotations = []      # Bounding boxes to draw on the GUI

        # ── Adaptive brightness/contrast enhancement ─────────────────────
        # If the frame is too dark (< 80) or washed out (> 200), apply a
        # mild contrast boost. This helps both YOLO and face_recognition
        # perform better in suboptimal lighting conditions.
        # cv2.convertScaleAbs is very fast (~0.1ms) so this adds negligible cost.
        mean_brightness = np.mean(frame)
        if mean_brightness < 80 or mean_brightness > 200:
            enhanced_frame = cv2.convertScaleAbs(frame, alpha=1.1, beta=10)
        else:
            enhanced_frame = frame

        person_detected = False

        # ═════════════════════════════════════════════════════════════════
        #  STAGE 1: OBJECT DETECTION (YOLO)
        # ═════════════════════════════════════════════════════════════════
        # Run YOLO on the frame to detect all objects (people, laptops, etc.)
        # imgsz=640 uses YOLO's native resolution for best accuracy.
        # device=SAFE_DEVICE routes to GPU or CPU based on startup detection.
        results = yolo_model(enhanced_frame, imgsz=640, verbose=False, device=SAFE_DEVICE)

        if len(results) > 0:
            for box in results[0].boxes:
                # Extract detection metadata
                class_id = int(box.cls[0])       # Numeric class ID (e.g., 0 = person)
                conf = float(box.conf[0])         # Confidence score (0.0 to 1.0)
                class_name = yolo_model.names[class_id]  # Human-readable class name

                # Flag if we saw a person — this gates face recognition below
                if class_name == "person":
                    person_detected = True

                # Extract bounding box pixel coordinates
                x1, y1, x2, y2 = map(int, box.xyxy[0])

                # Track unique object types (deduplicated for the SSE broadcast)
                if class_name not in detected_objects:
                    detected_objects.append(class_name)

                # Create annotation for the GUI overlay (blue for objects)
                label_text = f"{class_name.capitalize()} ({int(conf * 100)}%)"
                new_annotations.append({
                    "box": [x1, y1, x2, y2],
                    "label": label_text,
                    "color": (255, 150, 0)  # BGR: orange-blue
                })

        # ═════════════════════════════════════════════════════════════════
        #  STAGE 2: FACE RECOGNITION
        # ═════════════════════════════════════════════════════════════════
        # OPTIMIZATION: Only run the expensive face recognition pipeline
        # if YOLO detected at least one person in the frame. This avoids
        # wasting compute on empty rooms or frames with only objects.
        if person_detected:
            # face_recognition expects RGB, but OpenCV captures in BGR
            rgb_frame = cv2.cvtColor(enhanced_frame, cv2.COLOR_BGR2RGB)

            # ── Detect face locations ────────────────────────────────────
            # model=FACE_DETECT_MODEL uses "cnn" (GPU, more accurate) when
            # dlib CUDA is available, otherwise "hog" (CPU, faster).
            face_locations = face_recognition.face_locations(
                rgb_frame,
                model=FACE_DETECT_MODEL
            )

            if len(face_locations) > 0:
                # ── Compute face encodings ───────────────────────────────
                # For each detected face, compute a 128-dimensional vector
                # that uniquely represents the face's geometry. These vectors
                # can be compared using euclidean distance.
                face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

                # ── Match each face against known people ─────────────────
                # Process all faces in the frame simultaneously
                for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
                    name = "Unknown"
                    match_pct = 0

                    if len(known_face_encodings) > 0:
                        # Build a combined list of all known encodings:
                        # static (from disk) + dynamic (learned at runtime)
                        all_encs = known_face_encodings.copy()
                        all_names = known_face_names.copy()
                        for d_name, d_list in dynamic_encodings.items():
                            all_encs.extend(d_list)
                            all_names.extend([d_name] * len(d_list))

                        # Compare the detected face against ALL known encodings
                        matches = face_recognition.compare_faces(
                            all_encs, face_encoding, tolerance=FACE_MATCH_TOLERANCE
                        )
                        # Get euclidean distances (lower = more similar)
                        face_distances = face_recognition.face_distance(all_encs, face_encoding)

                        # Find the closest match
                        best_match_index = np.argmin(face_distances)

                        # Only accept the match if it's within the tolerance threshold
                        if matches[best_match_index]:
                            name = all_names[best_match_index]
                            # Convert raw distance to an intuitive confidence %
                            match_pct = face_distance_to_confidence(
                                face_distances[best_match_index], FACE_MATCH_TOLERANCE
                            )

                            # ── Self-learning: cache high-confidence angles ──
                            # When we get a very confident match (>85%), save
                            # the encoding so future frames from this angle
                            # match even better. Capped at MAX_DYNAMIC_ENCODINGS
                            # per person to prevent unbounded memory growth.
                            if match_pct > 85:
                                if name not in dynamic_encodings:
                                    dynamic_encodings[name] = []
                                dynamic_encodings[name].append(face_encoding)
                                if len(dynamic_encodings[name]) > MAX_DYNAMIC_ENCODINGS:
                                    dynamic_encodings[name].pop(0)  # FIFO eviction

                    # ── Create annotation based on recognition result ────
                    if name != "Unknown":
                        if name not in recognized_faces:
                            recognized_faces.append(name)
                        # Green bounding box for recognized faces
                        new_annotations.append({
                            "box": [left, top, right, bottom],
                            "label": f"{name} ({match_pct}%)",
                            "color": (0, 255, 0)  # BGR: green
                        })
                    else:
                        unknown_faces_count += 1
                        # Red bounding box for unknown faces
                        new_annotations.append({
                            "box": [left, top, right, bottom],
                            "label": "Unknown Face",
                            "color": (0, 0, 255)  # BGR: red
                        })

                        # ── Save unknown face crop to disk ───────────────
                        # These can be reviewed later to add new people to
                        # the known_faces directory.
                        face_image = frame[top:bottom, left:right]
                        if face_image.size > 0:
                            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                            filename = os.path.join(
                                UNKNOWN_FACES_DIR, f"unknown_{timestamp_str}.jpg"
                            )
                            cv2.imwrite(filename, face_image)

        # ── Update shared annotations for the GUI thread ─────────────────
        # Uses a Lock to prevent the GUI thread from reading a partially
        # updated annotation list.
        with shared_annotations["lock"]:
            shared_annotations["boxes"] = new_annotations

        # ── Update SSE broadcast data ────────────────────────────────────
        # This dict is sent to all connected SSE clients on the next poll.
        latest_broadcast_data = {
            "timestamp": current_timestamp,
            "detected_objects": detected_objects,
            "recognized_faces": recognized_faces,
            "unknown_faces_count": unknown_faces_count
        }
        # Signal the SSE generator that new data is available
        latest_data_event.set()

    print("[Dhatri Vision] Inference thread terminated.")


# =============================================================================
#  FASTAPI ENDPOINTS
# =============================================================================

async def event_generator():
    """Async generator that yields Server-Sent Events (SSE).

    Continuously checks for new detection data and yields it as JSON.
    The 50ms sleep interval prevents busy-spinning while keeping latency low.
    SSE format: each message is prefixed with "data: " and ends with double newline.
    """
    while True:
        if latest_data_event.is_set():
            latest_data_event.clear()
            data_json = json.dumps(latest_broadcast_data)
            yield f"data: {data_json}\n\n"
        await asyncio.sleep(0.05)  # ~20 updates/sec max


@app.get("/stream")
async def stream():
    """SSE endpoint that streams live vision detection results.

    Connect via EventSource in JavaScript:
        const source = new EventSource("http://localhost:8000/stream");
        source.onmessage = (event) => { console.log(JSON.parse(event.data)); };

    Returns a continuous stream of JSON objects with fields:
        - timestamp: Unix timestamp of the detection
        - detected_objects: list of object class names
        - recognized_faces: list of recognized person names
        - unknown_faces_count: number of unrecognized faces
    """
    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/status")
async def status():
    """REST endpoint that returns the most recent detection snapshot.

    Unlike /stream (which is continuous), this returns a single JSON response
    with the latest detection data. Useful for polling or one-off checks.
    """
    return latest_broadcast_data


def run_fastapi():
    """Starts the FastAPI/Uvicorn server.

    Uses uvicorn.Config + Server explicitly (instead of uvicorn.run) to avoid
    signal handler conflicts when running in a background thread. Signal
    handlers can only be installed on the main thread, so the simpler
    uvicorn.run() would crash here.
    """
    print("[Dhatri Vision] Starting FastAPI server on http://0.0.0.0:8000 ...")
    config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="info")
    server = uvicorn.Server(config)
    server.run()


# =============================================================================
#  GUI ANNOTATION RENDERING
# =============================================================================

def draw_annotations(frame, annotations):
    """Draws bounding boxes and labels on a video frame.

    Each annotation dict contains:
        - box: [x1, y1, x2, y2] pixel coordinates of the bounding box
        - label: Text to display (e.g., "Hardik (92%)")
        - color: BGR tuple for the box and label background

    Labels are positioned above the bounding box by default. If the box is
    too close to the top edge of the frame, the label is pushed below.
    Similarly, labels near the right edge are shifted left to stay visible.

    Args:
        frame: The OpenCV frame (numpy array) to draw on (modified in place)
        annotations: List of annotation dicts

    Returns:
        The annotated frame (same reference as input).
    """
    for ann in annotations:
        x1, y1, x2, y2 = ann["box"]
        label = ann["label"]
        color = ann["color"]

        # Draw the bounding box rectangle
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

        # Measure text size for the label background
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.5
        thickness = 1
        text_size, _ = cv2.getTextSize(label, font, font_scale, thickness)
        text_w, text_h = text_size

        # Default: position label ABOVE the bounding box
        rect_x1 = x1
        rect_y1 = y1 - text_h - 8
        rect_x2 = x1 + text_w + 4
        rect_y2 = y1
        text_y = y1 - 4

        # ── Clamp to frame boundaries ────────────────────────────────
        if rect_y1 < 0:
            # Box is near the top edge — push label below the top edge
            rect_y1 = y1
            rect_y2 = y1 + text_h + 8
            text_y = y1 + text_h + 4

        if rect_x2 > frame.shape[1]:
            # Label overflows the right edge — shift left
            shift = rect_x2 - frame.shape[1]
            rect_x1 -= shift
            rect_x2 -= shift

        if rect_x1 < 0:
            # Label overflows the left edge — clamp to 0
            rect_x1 = 0
            rect_x2 = text_w + 4

        # Draw filled rectangle behind the label text for readability
        cv2.rectangle(frame, (rect_x1, rect_y1), (rect_x2, rect_y2), color, -1)
        # Draw the label text in white
        cv2.putText(frame, label, (rect_x1 + 2, text_y), font, font_scale, (255, 255, 255), thickness)

    return frame


def get_annotated_frame(timeout=0.1):
    """Convenience function: grabs a frame and draws annotations on it.

    Used by external callers (e.g., the GUI module) who want a ready-to-display
    frame without manually managing the display_queue and shared_annotations.

    Args:
        timeout: Max seconds to wait for a frame from the display queue.

    Returns:
        Annotated frame (numpy array), or None if no frame was available.
    """
    try:
        frame = display_queue.get(timeout=timeout)
    except queue.Empty:
        return None

    with shared_annotations["lock"]:
        boxes_to_draw = shared_annotations["boxes"].copy()

    return draw_annotations(frame, boxes_to_draw)


# =============================================================================
#  MAIN GUI LOOP (runs on the main thread)
# =============================================================================

def main_gui_loop():
    """Renders annotated video frames in a local OpenCV window.

    IMPORTANT: This function MUST run on the main thread. On macOS and Windows,
    OpenCV's GUI functions (namedWindow, imshow, waitKey) are only safe to call
    from the main thread. Calling them from a background thread causes crashes
    or hangs.

    The loop:
      1. Pulls the latest frame from the display_queue
      2. Copies the current annotations (thread-safe via Lock)
      3. Draws bounding boxes and labels on the frame
      4. Displays the frame in the "Dhatri Vision Feed" window
      5. Checks for 'q' keypress to trigger graceful shutdown

    Press 'q' in the OpenCV window to stop the entire vision service.
    """
    print("[Dhatri Vision] Initializing GUI window...")
    window_name = "Dhatri Vision Feed"
    cv2.namedWindow(window_name, cv2.WINDOW_AUTOSIZE)

    while not shutdown_event.is_set():
        try:
            # Pull the latest frame from the camera thread
            frame = display_queue.get(timeout=0.1)
        except queue.Empty:
            # No frame yet — but we MUST still pump the OpenCV event loop,
            # otherwise the window becomes unresponsive on Windows/macOS.
            if cv2.waitKey(1) & 0xFF == ord('q'):
                shutdown_event.set()
                break
            continue

        # Thread-safe copy of the current annotations
        with shared_annotations["lock"]:
            boxes_to_draw = shared_annotations["boxes"].copy()

        # Draw bounding boxes and labels onto the frame
        frame = draw_annotations(frame, boxes_to_draw)

        # Display the annotated frame
        cv2.imshow(window_name, frame)

        # Check for 'q' keypress → graceful shutdown
        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("[Dhatri Vision] Shutting down (user pressed 'q')...")
            shutdown_event.set()
            break

    # Cleanup: close the OpenCV window and force-exit
    # os._exit is used because background daemon threads (camera, inference,
    # FastAPI) don't respond to normal sys.exit() cleanly.
    cv2.destroyAllWindows()
    os._exit(0)


# =============================================================================
#  ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    # 1. Start the FastAPI server in a background daemon thread.
    #    This serves the /stream and /status endpoints on port 8000.
    fastapi_thread = threading.Thread(target=run_fastapi, daemon=True)
    fastapi_thread.start()

    # 2. Start the camera capture and inference worker threads.
    #    These run as daemon threads and will be killed when the main thread exits.
    start_workers()

    # 3. Run the GUI event loop on the main thread.
    #    This blocks until the user presses 'q' or the window is closed.
    main_gui_loop()
