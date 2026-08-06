# 🤖 Project Dhatri

**Dhatri** is a multi-modal AI assistant that can see, hear, and speak — built as a modular microservices system with a desktop GUI. Every component runs **100% offline** with zero cloud dependencies, using state-of-the-art open-source ML models for real-time computer vision, speech recognition, and voice-cloned text-to-speech.

---

## ✨ Features

| Capability | Technology | What It Does |
|-----------|-----------|--------------|
| 👁️ **Vision** | YOLOv11 + dlib | Real-time object detection (80 classes) and face recognition with self-learning |
| 🎙️ **Listening** | Faster-Whisper + OpenWakeWord | Wake word detection ("Dhatri") → speech-to-text transcription |
| 🔊 **Speaking** | MeloTTS + OpenVoice V2 | Text-to-speech with zero-shot voice cloning from any reference audio |
| 🧠 **Brain** | Pluggable LLM interface | Central logic for processing user prompts (extensible) |
| 🖥️ **GUI** | PyQt6 | Desktop app with chat, live camera feed, and audio visualizer |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        main.py                               │
│         (CUDA diagnostics, venv auto-relaunch, bootstrap)    │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    PyQt6 GUI (MainWindow)                     │
│  ┌──────────┐  ┌──────────────┐  ┌────────────────────────┐ │
│  │  Chat    │  │  Controls     │  │  Visualizer Overlay    │ │
│  │  Display │  │  (Vision,     │  │  (Animated audio       │ │
│  │          │  │   Listen,     │  │   waveform circles)    │ │
│  │          │  │   Mute)       │  │                        │ │
│  └──────────┘  └──────────────┘  └────────────────────────┘ │
└──────┬──────────────┬──────────────────┬────────────────────┘
       │              │                  │
       ▼              ▼                  ▼
┌────────────┐ ┌────────────┐  ┌──────────────┐  ┌──────────┐
│  Listen    │ │  Speak     │  │   Vision     │  │  Brain   │
│  Thread    │ │  Thread    │  │   Thread     │  │  Module  │
│  (QThread) │ │  (QThread) │  │   (QThread)  │  │          │
└─────┬──────┘ └─────┬──────┘  └──────┬───────┘  └──────────┘
      │              │                │
      ▼              ▼                ▼
┌────────────┐ ┌────────────┐  ┌──────────────┐
│  Listen    │ │  Speak     │  │   Vision     │
│  µService  │ │  µService  │  │   µService   │
│            │ │            │  │              │
│ OpenWakeWord│ │ MeloTTS    │  │ YOLOv11     │
│ WebRTC VAD │ │ OpenVoice  │  │ face_recog   │
│ Whisper    │ │ V2         │  │ FastAPI SSE  │
└────────────┘ └────────────┘  └──────────────┘
```

Each microservice is **self-contained** with its own dependencies, models, and README. They communicate with the GUI via Python queues and threads — no network overhead between components.

---

## 📦 Project Structure

```
Project-Dhatri/
├── main.py                          # Entry point — CUDA check, venv bootstrap, GUI launch
├── requirements.txt                 # Root Python dependencies
├── README.md                        # This file
│
├── gui/                             # PyQt6 Desktop Interface
│   ├── main_window.py               # Main chat window with controls
│   ├── vision_window.py             # Live camera feed window
│   ├── components/
│   │   └── visualizer_overlay.py    # Animated audio visualizer
│   └── threads/
│       ├── listen_thread.py         # QThread → Listen microservice
│       ├── speak_thread.py          # QThread → Speak microservice
│       └── video_thread.py          # QThread → Vision microservice
│
├── listen_microservice/             # 🎙️ Wake Word + Speech-to-Text
│   ├── main.py                      # 3-state loop: WAKEWORD → RECORDING → PROCESSING
│   ├── generate_wakeword.py         # Custom wake word training guide
│   ├── requirements.txt
│   └── README.md
│
├── speak_microservice/              # 🔊 Text-to-Speech + Voice Cloning
│   ├── main.py                      # Interactive CLI for testing
│   ├── tts_engine.py                # MeloTTS + OpenVoice V2 engine
│   ├── set_default_voice.py         # Configure reference voice
│   ├── setup_env.py                 # Download model checkpoints
│   ├── test_tts.py                  # Verification script
│   ├── requirements.txt
│   └── README.md
│
├── vision_microservice/             # 👁️ Object Detection + Face Recognition
│   ├── main_vision_service.py       # Multi-threaded vision pipeline
│   ├── setup_assets.py              # Download YOLO model weights
│   ├── requirements.txt
│   └── README.md
│
├── brain/                           # 🧠 Central AI Logic
│   ├── __init__.py
│   └── core.py                      # process_prompt() — LLM interface
│
└── .github/workflows/
    └── python-app.yml               # CI: Lint with flake8 on push/PR
```

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.9+** (3.10 recommended)
- **NVIDIA GPU with CUDA** — highly recommended for real-time performance (CPU fallback supported)
- **Windows**: Visual Studio C++ Build Tools + CMake (required for `dlib` / face recognition)

### Step 1 — Clone & Setup Environment

```bash
git clone https://github.com/Hardik01001000-code/Project-Dhatri.git
cd Project-Dhatri

python -m venv venv

# Windows
venv\Scripts\activate

# Linux/macOS
source venv/bin/activate
```

### Step 2 — Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 3 — Download AI Models

```bash
# Download OpenVoice V2 checkpoints for voice cloning
python speak_microservice/setup_env.py

# Download YOLOv11 weights for object detection
python vision_microservice/setup_assets.py
```

> **Note:** The Faster-Whisper STT model is downloaded automatically on first run.

### Step 4 — Configure (Optional)

```bash
# Set a custom voice for the AI to speak in
python speak_microservice/set_default_voice.py path/to/voice_sample.wav

# Add faces for recognition (create a folder per person)
mkdir vision_microservice\known_faces\YourName
# Copy clear face photos into the folder
```

### Step 5 — Run

```bash
python main.py
```

This will:
1. Auto-detect and test CUDA GPU availability
2. Initialize PyTorch CUDA context on the main thread
3. Launch the PyQt6 GUI with all microservices running in background threads

---

## 🖥️ GUI Controls

| Button | Function |
|--------|----------|
| **👁️ Vision** | Toggle the live camera feed window on/off |
| **🎙️ Listening** | Toggle wake word detection on/off (enabled by default) |
| **🔇 Mute** | Toggle AI voice responses on/off |

- **Chat Box** — Type messages directly or speak using the wake word
- **Audio Visualizer** — Animated overlay showing microphone activity (pulsing circles during recording)
- **Vision Window** — Live 640×480 feed with color-coded bounding boxes:
  - 🟠 Orange / 🔵 Blue — Detected objects
  - 🟢 Green — Recognized faces (with confidence %)
  - 🔴 Red — Unknown/stranger faces

---

## 📖 Microservice Documentation

Each microservice has its own detailed README with architecture diagrams, configuration options, and setup instructions:

| Microservice | README | Description |
|-------------|--------|-------------|
| Listen | [`listen_microservice/README.md`](listen_microservice/README.md) | Wake word detection, VAD, speech-to-text |
| Speak | [`speak_microservice/README.md`](speak_microservice/README.md) | TTS engine with zero-shot voice cloning |
| Vision | [`vision_microservice/README.md`](vision_microservice/README.md) | Object detection, face recognition, SSE streaming |

---

## ⚙️ How `main.py` Works

The entry point handles several critical bootstrapping tasks:

1. **Virtual Environment Auto-Relaunch** — If not running inside `venv/`, automatically re-launches using the venv Python binary
2. **CUDA Safety Check** — Runs an isolated subprocess test (`torch.matmul` on CUDA) with a 30s timeout. If it fails (missing DLLs, broken drivers), CUDA is disabled via `CUDA_VISIBLE_DEVICES=""` before any model loads
3. **CUDA Context Init** — Allocates a dummy tensor on GPU from the main thread to prevent multi-threading CUDA initialization crashes on Windows
4. **GUI Launch** — Creates the PyQt6 application and starts the event loop

---

## 🔐 Privacy & Security

- **100% Offline** — No data ever leaves your machine. No API keys, no cloud services, no telemetry
- **Face data is git-ignored** — The `known_faces/` and `unknown_faces/` directories are excluded from version control
- **All media files blocked** — `.jpg`, `.png`, `.wav`, `.mp3` and similar formats are in `.gitignore`

---

## 🧪 CI/CD

GitHub Actions workflow runs on every push and PR to `main`:

- **Runner:** `ubuntu-latest`, Python 3.10
- **Checks:** `flake8` linting for syntax errors and undefined names
- **Config:** `.github/workflows/python-app.yml`

---

## 📋 Notice Regarding AI Models

Due to the large size of AI model weights, they are **excluded from this repository**. When you run the setup scripts or launch the microservices for the first time, they will automatically download the required models:

| Model | Size | Auto-Download |
|-------|------|---------------|
| YOLOv11s | ~25 MB | `python vision_microservice/setup_assets.py` |
| Faster-Whisper base.en | ~150 MB | Auto-downloaded on first run |
| OpenVoice V2 Checkpoints | ~300 MB | `python speak_microservice/setup_env.py` |
| OpenWakeWord (dhatri) | ~5 MB | User-trained (see listen README) |

---

## 📄 License

This project is for personal/educational use.
