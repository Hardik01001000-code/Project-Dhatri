import os
# EXPLICITLY DISABLE ULTRALYTICS TELEMETRY BEFORE IMPORT
os.environ["YOLO_VERBOSE"] = "False"
os.environ["YOLO_SYNC"] = "False"

from ultralytics import settings
settings.update({'sync': False}) # Disable sync

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

def get_safe_device():
    try:
        import torch
        if torch.cuda.is_available() and torch.cuda.device_count() > 0:
            torch.tensor([1.0]).cuda()
            return "cuda:0"
    except Exception:
        pass
    return "cpu"

SAFE_DEVICE = get_safe_device()

# Configurations
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, "models")
YOLO_MODEL_PATH = os.path.join(MODELS_DIR, "yolo26n.pt")
UNKNOWN_FACES_DIR = os.path.join(BASE_DIR, "unknown_faces")
KNOWN_FACES_DIR = os.path.join(BASE_DIR, "known_faces")
INFERENCE_EVERY_N_FRAMES = 6
FACE_MATCH_TOLERANCE = 0.6  # lower is stricter

# Ensure directories exist
os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(UNKNOWN_FACES_DIR, exist_ok=True)
os.makedirs(KNOWN_FACES_DIR, exist_ok=True)

# Global state
latest_broadcast_data = {
    "timestamp": time.time(),
    "detected_objects": [],
    "recognized_faces": [],
    "unknown_faces_count": 0
}
latest_data_event = threading.Event()
shutdown_event = threading.Event()

# Queues for decoupled architecture
display_queue = queue.Queue(maxsize=2)
inference_queue = queue.Queue(maxsize=1)

shared_annotations = {
    "lock": threading.Lock(),
    "boxes": [] # List of dicts: {"box": [x1, y1, x2, y2], "label": "Text", "color": (B, G, R)}
}

app = FastAPI(title="Vision Microservice API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_workers = []

def start_workers():
    global _workers
    if _workers:
        stop_workers()
        
    shutdown_event.clear()
    t1 = threading.Thread(target=camera_thread, daemon=True)
    t2 = threading.Thread(target=inference_worker, daemon=True)
    t1.start()
    t2.start()
    _workers.extend([t1, t2])

def stop_workers():
    global _workers
    shutdown_event.set()
    for t in _workers:
        if t.is_alive():
            t.join(timeout=2.0)
    _workers.clear()



def camera_thread():
    """Background thread specifically for grabbing frames from the webcam."""
    print("Starting webcam capture thread...")
    # cv2.CAP_DSHOW can prevent some hanging issues on Windows
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        cap = cv2.VideoCapture(0) # Fallback
        
    if not cap.isOpened():
        print("Error: Could not open webcam.")
        shutdown_event.set()
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    frame_count = 0

    while not shutdown_event.is_set():
        ret, frame = cap.read()
        if not ret:
            time.sleep(0.01)
            continue
            
        height, width = frame.shape[:2]
        if width > 640 or height > 480:
            frame = cv2.resize(frame, (640, 480))

        frame_count += 1
        
        # Push to inference queue strictly every N frames
        if frame_count % INFERENCE_EVERY_N_FRAMES == 0:
            if inference_queue.full():
                try:
                    inference_queue.get_nowait()
                except queue.Empty:
                    pass
            inference_queue.put(frame.copy())

        # Push to display queue for the main thread
        if display_queue.full():
            try:
                display_queue.get_nowait()
            except queue.Empty:
                pass
        display_queue.put(frame)

    cap.release()
    print("Camera capture thread terminated.")


# --- Global Model Caches ---
_yolo_model = None
_known_face_names = []
_known_face_encodings = []
_models_loaded = False

def load_models():
    """Loads heavy AI models and known faces globally once."""
    global _yolo_model, _known_face_names, _known_face_encodings, _models_loaded
    if _models_loaded:
        return

    print("[Dhatri Vision] Initializing offline vision service AI models globally...")
    if not os.path.exists(YOLO_MODEL_PATH):
        print(f"CRITICAL ERROR: YOLO model not found at {YOLO_MODEL_PATH}.")
        print("Please run setup_assets.py to download it.")
        return
        
    try:
        # Load YOLO Model
        _yolo_model = YOLO(YOLO_MODEL_PATH)
    except Exception as e:
        print(f"Error loading YOLO model: {e}")
        return

    # Load known faces from directory
    _known_face_names.clear()
    _known_face_encodings.clear()
    print(f"Scanning {KNOWN_FACES_DIR} for known faces...")
    for filename in os.listdir(KNOWN_FACES_DIR):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            name = os.path.splitext(filename)[0]
            filepath = os.path.join(KNOWN_FACES_DIR, filename)
            image = face_recognition.load_image_file(filepath)
            encodings = face_recognition.face_encodings(image)
            if len(encodings) > 0:
                _known_face_names.append(name)
                _known_face_encodings.append(encodings[0])
                print(f"  -> Learned face: {name}")
            else:
                print(f"  -> Warning: No face found in {filename}")

    print(f"Loaded {len(_known_face_names)} known faces into global memory.")
    _models_loaded = True

# Pre-load models asynchronously upon module import!
# threading.Thread(target=load_models, daemon=True).start()

def inference_worker():
    """Background thread running heavy math models."""
    global latest_broadcast_data, _yolo_model, _known_face_names, _known_face_encodings
    
    # Load models directly in this thread to avoid CUDA context destruction
    if not _models_loaded:
        load_models()
            
    if shutdown_event.is_set() or not _models_loaded:
        return

    print("Inference worker starting using cached models...")
    
    # Map to local variables for inference loop compatibility
    yolo_model = _yolo_model
    known_face_names = _known_face_names
    known_face_encodings = _known_face_encodings

    while not shutdown_event.is_set():
        try:
            frame = inference_queue.get(timeout=0.5)
        except queue.Empty:
            continue

        current_timestamp = time.time()
        detected_objects = []
        recognized_faces = []
        unknown_faces_count = 0
        new_annotations = []
        
        # Optimize feed: Only apply contrast enhancement if the feed is poorly lit or washed out
        mean_brightness = np.mean(frame)
        if mean_brightness < 80 or mean_brightness > 200:
            # cv2.convertScaleAbs is extremely fast
            enhanced_frame = cv2.convertScaleAbs(frame, alpha=1.1, beta=10)
        else:
            enhanced_frame = frame
        
        person_detected = False
        
        # --- Object Detection (YOLO) ---
        # imgsz=320 aggressively speeds up YOLO inference while using less RAM
        results = yolo_model(enhanced_frame, imgsz=320, verbose=False, device=SAFE_DEVICE)
        if len(results) > 0:
            for box in results[0].boxes:
                class_id = int(box.cls[0])
                conf = float(box.conf[0])
                class_name = yolo_model.names[class_id]
                
                if class_name == "person":
                    person_detected = True
                
                # Extract coordinates
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                
                if class_name not in detected_objects:
                    detected_objects.append(class_name)
                    
                # Add to annotations (Blue for objects)
                label_text = f"{class_name.capitalize()} ({int(conf * 100)}%)"
                new_annotations.append({
                    "box": [x1, y1, x2, y2],
                    "label": label_text,
                    "color": (255, 150, 0) # BGR
                })

        # --- Face Recognition (HEAVILY OPTIMIZED) ---
        # ONLY run heavy face recognition if YOLO actually saw a person in the frame!
        if person_detected:
            rgb_frame = cv2.cvtColor(enhanced_frame, cv2.COLOR_BGR2RGB)
    
            # The system naturally detects multiple faces at a time by iterating over face_locations
            face_locations = face_recognition.face_locations(rgb_frame)
            if len(face_locations) > 0:
                face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
    
                # Handles multiple faces simultaneously in the same frame
                for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
                    name = "Unknown"
                    match_pct = 0
                    if len(known_face_encodings) > 0:
                        matches = face_recognition.compare_faces(known_face_encodings, face_encoding, tolerance=FACE_MATCH_TOLERANCE)
                        face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
                        best_match_index = np.argmin(face_distances)
                        if matches[best_match_index]:
                            name = known_face_names[best_match_index]
                            match_pct = int((1.0 - face_distances[best_match_index]) * 100)
    
                    if name != "Unknown":
                        if name not in recognized_faces:
                            recognized_faces.append(name)
                        # Add to annotations (Green for known faces)
                        new_annotations.append({
                            "box": [left, top, right, bottom],
                            "label": f"{name} ({match_pct}%)",
                            "color": (0, 255, 0)
                        })
                    else:
                        unknown_faces_count += 1
                        # Add to annotations (Red for unknown faces)
                        new_annotations.append({
                            "box": [left, top, right, bottom],
                            "label": "Unknown Face",
                            "color": (0, 0, 255)
                        })
                        
                        # Save unknown face crop
                        face_image = frame[top:bottom, left:right]
                        if face_image.size > 0:
                            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                            filename = os.path.join(UNKNOWN_FACES_DIR, f"unknown_{timestamp_str}.jpg")
                            cv2.imwrite(filename, face_image)

        # Update shared state securely
        with shared_annotations["lock"]:
            shared_annotations["boxes"] = new_annotations

        # Update broadcast data
        latest_broadcast_data = {
            "timestamp": current_timestamp,
            "detected_objects": detected_objects,
            "recognized_faces": recognized_faces,
            "unknown_faces_count": unknown_faces_count
        }
        latest_data_event.set()
    
    print("Inference thread terminated.")


async def event_generator():
    """Generator for Server-Sent Events"""
    while True:
        if latest_data_event.is_set():
            latest_data_event.clear()
            data_json = json.dumps(latest_broadcast_data)
            yield f"data: {data_json}\n\n"
        await asyncio.sleep(0.05)

@app.get("/stream")
async def stream():
    """SSE Endpoint broadcasting the latest vision data."""
    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.get("/status")
async def status():
    """Simple REST endpoint to get the current latest data."""
    return latest_broadcast_data

def run_fastapi():
    print("Starting FastAPI server for Vision Microservice in background...")
    # Using Config and Server explicitly to avoid signal handling issues in background threads
    config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="info")
    server = uvicorn.Server(config)
    server.run()


def draw_annotations(frame, annotations):
    """Utility to draw bounding boxes and labels on a frame."""
    for ann in annotations:
        x1, y1, x2, y2 = ann["box"]
        label = ann["label"]
        color = ann["color"]
        
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.5
        thickness = 1
        text_size, _ = cv2.getTextSize(label, font, font_scale, thickness)
        text_w, text_h = text_size
        
        cv2.rectangle(frame, (x1, y2), (x1 + text_w + 4, y2 + text_h + 8), color, -1)
        cv2.putText(frame, label, (x1 + 2, y2 + text_h + 4), font, font_scale, (255, 255, 255), thickness)
    return frame

def get_annotated_frame(timeout=0.1):
    """Pulls a frame from the queue, annotates it securely, and returns it."""
    try:
        frame = display_queue.get(timeout=timeout)
    except queue.Empty:
        return None

    with shared_annotations["lock"]:
        boxes_to_draw = shared_annotations["boxes"].copy()
        
    return draw_annotations(frame, boxes_to_draw)

def main_gui_loop():
    """Strictly runs on the Main Thread to handle cv2 GUI rendering."""
    print("Initializing Main GUI Thread...")
    window_name = "Dhatri Vision Feed"
    cv2.namedWindow(window_name, cv2.WINDOW_AUTOSIZE)

    while not shutdown_event.is_set():
        try:
            # Pull frame from the background camera thread
            frame = display_queue.get(timeout=0.1)
        except queue.Empty:
            # Must still pump the event loop even if no frame is ready
            if cv2.waitKey(1) & 0xFF == ord('q'):
                shutdown_event.set()
                break
            continue

        # Render annotations
        with shared_annotations["lock"]:
            boxes_to_draw = shared_annotations["boxes"].copy()
            
        frame = draw_annotations(frame, boxes_to_draw)

        # Show the frame
        cv2.imshow(window_name, frame)
        
        # Graceful shutdown on 'q'
        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("Shutting down vision service...")
            shutdown_event.set()
            break
            
    # Cleanup
    cv2.destroyAllWindows()
    os._exit(0)


if __name__ == "__main__":
    # 1. Start FastAPI in the background
    fastapi_thread = threading.Thread(target=run_fastapi, daemon=True)
    fastapi_thread.start()

    # 2. Start workers (Camera & Inference)
    start_workers()
    
    # 3. Run the GUI Event Loop strictly on the Main Thread
    main_gui_loop()
