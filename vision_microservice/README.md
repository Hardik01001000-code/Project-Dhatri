# 👁️ Vision Microservice

A fully offline, real-time computer vision service for Project Dhatri. Performs object detection using YOLOv11 and face recognition using dlib — streaming results via FastAPI SSE while rendering a live annotated video feed.

---

## Overview

The Vision Microservice acts as Dhatri's "eyes". It captures live webcam video, detects objects and faces in real-time, recognizes known people, captures unknown faces for review, and broadcasts detection results as a JSON stream — all running 100% offline.

### Key Features

- **🔒 100% Offline** — Zero telemetry, all models loaded locally
- **🎯 Object Detection** — YOLOv11s detects 80 COCO classes (person, laptop, phone, cup, etc.)
- **👤 Face Recognition** — dlib-based 128-dimensional face encodings with configurable tolerance
- **📂 Multi-Image Enrollment** — Folder-per-person layout for higher recognition accuracy
- **🧠 Self-Learning** — Dynamically caches high-confidence encodings at runtime to improve recognition over time
- **📸 Stranger Capture** — Automatically crops and saves unknown faces for manual review
- **📡 SSE Streaming** — FastAPI server broadcasts live detection data on port 8000
- **🖥️ GPU Accelerated** — Auto-detects NVIDIA CUDA for YOLO + dlib CNN, graceful CPU fallback

---

## Architecture

The service uses a **decoupled multi-threaded architecture** to keep camera capture smooth while AI inference runs independently:

```
                  ┌──────────────────────┐
                  │   Camera Thread      │
                  │  (cv2.VideoCapture)  │
                  └──────────┬───────────┘
                             │
            ┌────────────────┴────────────────┐
      (Every Frame)                   (Every 6th Frame)
            │                                 │
            ▼                                 ▼
   ┌─────────────────┐               ┌──────────────────┐
   │  display_queue   │               │ inference_queue   │
   │  (maxsize = 2)   │               │  (maxsize = 1)    │
   └────────┬────────┘               └────────┬─────────┘
            │                                 │
            ▼                                 ▼
┌───────────────────────┐        ┌────────────────────────┐
│   Main GUI Thread     │        │ Inference Worker Thread │
│  (OpenCV window)      │◄───────┤ (YOLO + Face Recog)     │
└───────────────────────┘ shared │                         │
                      annotations └──────────┬──────────────┘
                         (Lock)              │
                                    latest_broadcast_data
                                              │
                                              ▼
                                 ┌────────────────────────┐
                                 │  FastAPI / Uvicorn SSE  │
                                 │  (port 8000)            │
                                 └────────────────────────┘
```

### Thread Breakdown

| Thread | Role | Details |
|--------|------|---------|
| **Camera Thread** | Captures raw frames | DirectShow backend (Windows), 640×480, pushes every frame to display queue, every 6th to inference |
| **Inference Worker** | Runs AI models | YOLO object detection → conditional face recognition (only when "person" detected) |
| **Main GUI Thread** | Renders video | OpenCV window with color-coded bounding boxes, must run on main thread |
| **FastAPI Server** | Broadcasts results | SSE streaming on `/stream`, REST snapshot on `/status` |

---

## GPU Detection & Fallback

At startup, the service probes two independent GPU acceleration paths:

| Path | Library | GPU Mode | CPU Fallback |
|------|---------|----------|--------------|
| Object Detection | PyTorch CUDA | YOLO runs on GPU (device `0`) | YOLO runs on CPU |
| Face Detection | dlib CUDA | CNN face detector (more accurate) | HOG face detector (faster) |

A detailed diagnostics banner is printed at startup showing GPU name, VRAM, and acceleration status.

---

## Face Recognition

### Known Faces Directory Structure

The service supports two layouts (folder-per-person is recommended):

**Recommended — Multiple images per person:**
```
known_faces/
└── PersonName/
    ├── photo1.jpg
    ├── photo2.jpeg
    └── photo3.png
```

**Legacy — Single image per person:**
```
known_faces/
├── PersonName.jpg
└── AnotherPerson.png
```

### How Matching Works

1. **Encoding** — Each face is converted to a 128-dimensional vector using dlib's ResNet
2. **Distance Calculation** — Euclidean distance computed against all known encodings
3. **Confidence Scoring** — Non-linear curve converts distance to human-readable percentage:
   - Distance ~0.3 → ~96% confidence
   - Distance ~0.5 → ~87% confidence
   - Distance ~0.6 → ~50% confidence (match threshold)
4. **Self-Learning** — High-confidence matches (>85%) dynamically cache new encodings (up to 5 per person) to adapt to lighting and angle changes
5. **Stranger Capture** — Unrecognized faces are auto-saved to `unknown_faces/` as timestamped crops

---

## API Endpoints

**Base URL:** `http://localhost:8000`

### `GET /stream` — Server-Sent Events

Continuous real-time detection stream (~20 updates/sec max).

```bash
curl -N http://localhost:8000/stream
```

Response format:
```
data: {"timestamp": 1723000000.0, "detected_objects": ["person", "laptop"], "recognized_faces": ["Hardik"], "unknown_faces_count": 0}
```

### `GET /status` — REST Snapshot

Returns the latest detection state as a single JSON object.

```bash
curl http://localhost:8000/status
```

---

## Setup

### Prerequisites

- Python 3.9+
- **Windows**: Visual Studio C++ Build Tools ("Desktop development with C++" workload) + CMake in PATH — required for building `dlib`
- NVIDIA GPU recommended (not required)

### Installation

```bash
cd vision_microservice

# 1. Install dependencies
pip install -r requirements.txt

# 2. Download YOLOv11 model weights
python setup_assets.py

# 3. Add known faces (create a folder per person)
mkdir known_faces\YourName
# Copy face photos into the folder
```

### Running

```bash
python main_vision_service.py
```

This will:
- Detect GPU capabilities and print diagnostics
- Start webcam capture
- Launch the inference pipeline
- Start the FastAPI server on `http://0.0.0.0:8000`
- Open the "Dhatri Vision Feed" window

Press **`q`** in the video window to shut down.

---

## Configuration

All parameters are constants at the top of `main_vision_service.py`:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `YOLO_MODEL_PATH` | `./models/yolo11s.pt` | Path to YOLO weights |
| `INFERENCE_EVERY_N_FRAMES` | `6` | Only run AI on every Nth frame |
| `FACE_MATCH_TOLERANCE` | `0.6` | Face matching strictness (lower = stricter) |
| `MAX_DYNAMIC_ENCODINGS` | `5` | Max self-learned encodings cached per person |
| Frame Resolution | `640×480` | Camera capture resolution |
| Server Port | `8000` | FastAPI SSE/REST server port |

---

## Dependencies

```
fastapi
uvicorn
opencv-python
ultralytics
face_recognition
numpy
sse-starlette
```

---

## File Structure

```
vision_microservice/
├── main_vision_service.py   # Core service (capture, detection, recognition, SSE)
├── setup_assets.py          # Downloads YOLOv11s model weights
├── requirements.txt         # Python dependencies
├── README.md                # This file
├── vision_memory.db         # SQLite database (legacy)
├── models/                  # YOLO model weights (git-ignored)
│   └── yolo11s.pt
├── known_faces/             # Reference face images (git-ignored)
│   └── PersonName/
│       ├── photo1.jpg
│       └── photo2.jpg
└── unknown_faces/           # Auto-captured stranger crops (git-ignored)
    └── unknown_YYYYMMDD_HHMMSS_ffffff.jpg
```
