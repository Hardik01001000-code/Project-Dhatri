# Offline Vision Microservice

A 100% offline computer vision microservice in Python that detects objects using YOLOv11 and recognizes faces using the `face_recognition` library. It acts as a "vision brain" that captures frames from a webcam, processes them periodically to save resources, and streams the results locally as JSON via FastAPI Server-Sent Events (SSE).

## Features
- **100% Offline**: Zero telemetry, loads all weights locally.
- **Resource Efficient**: Only runs heavy YOLO and Face Recognition inference on every 5th frame.
- **Local SQLite DB**: Remembers recognized faces based on embeddings.
- **Captures Strangers**: Saves timestamped crops of unknown faces.
- **JSON Broadcast**: Emits a lightweight JSON stream of detected objects and faces locally.

---

## 🛠 Prerequisites and Installation

### 1. Install System Dependencies (Windows Only)
The `face_recognition` package depends on `dlib`, which requires C++ compilation on Windows.
* Install **Visual Studio C++ Build Tools** (Select "Desktop development with C++" workload).
* Install **CMake** and ensure it's in your system PATH.

### 2. Setup Python Environment
It is recommended to use a virtual environment.
```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 4. Download YOLOv11 Nano Weights Locally
To keep the script 100% offline, you must manually download the YOLOv11 nano model weights.
1. Download `yolo11n.pt` from the official Ultralytics repository (or export it). 
2. For YOLO11 nano: `wget https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11n.pt` (Make sure the link corresponds to YOLO11 nano release).
3. Place `yolo11n.pt` exactly in the `./models/` directory:
   ```text
   vision_microservice/
   └── models/
       └── yolo11n.pt
   ```

*(Note: `face_recognition` bundles its own models in the python package, so it will work entirely offline once installed).*

---

## 🏃‍♂️ Usage

### Learning New Faces

Before the system can recognize you, you must teach it your face using the `teach_face.py` CLI script.

1. Ensure you have a clear, well-lit image of your face.
2. Run the teaching script:
```bash
python teach_face.py "Your Name" path/to/your/image.jpg
```
The script will extract the facial embedding and save it to the local `vision_memory.db` SQLite database.

### Running the Microservice

Start the microservice:
```bash
python main_vision_service.py
```
This will:
* Disable all YOLO telemetry.
* Start capturing from your default webcam.
* Start a FastAPI server on `http://0.0.0.0:8000`.

### Consuming the Data Broadcast

The microservice broadcasts continuous updates via Server-Sent Events (SSE). 

**Endpoint**: `GET http://localhost:8000/stream`

Example using `curl`:
```bash
curl -N http://localhost:8000/stream
```

Example JSON Payload:
```json
{
  "timestamp": 1684321234.567,
  "detected_objects": ["person", "laptop", "cup"],
  "recognized_faces": ["Your Name"],
  "unknown_faces_count": 0
}
```

If the service detects a face that is not in its memory, it will increment `unknown_faces_count` and save a cropped image to the `./unknown_faces/` folder for your manual review.
