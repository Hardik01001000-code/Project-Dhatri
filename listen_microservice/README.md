# 🎙️ Listen Microservice

A fully offline, real-time voice command listener and speech-to-text engine for Project Dhatri. Handles wake word detection, voice activity detection, and speech transcription — all running locally with zero cloud dependencies.

---

## Overview

The Listen Microservice continuously monitors the system microphone, waiting for the custom wake word **"Dhatri"**. Once triggered, it records the user's speech, detects when they stop talking, and transcribes the audio using Faster-Whisper — all in real-time, entirely on-device.

### Key Features

- **🔒 100% Offline** — No cloud APIs, no telemetry, no internet required
- **🗣️ Custom Wake Word** — Trained "Dhatri" wake word model via OpenWakeWord (with "Alexa" fallback)
- **⚡ Real-Time STT** — Faster-Whisper `base.en` model with `int8` quantization for fast CPU transcription
- **🎯 Smart VAD** — WebRTC-based voice activity detection with dynamic silence thresholds
- **🧹 Hallucination Filtering** — Automatically discards common Whisper artifacts on silent audio

---

## Architecture

The microservice runs a **3-state loop** that cycles continuously:

```
┌─────────────┐     wake word      ┌─────────────┐     silence       ┌──────────────┐
│   WAKEWORD  │ ──── detected ───► │  RECORDING   │ ── threshold ──► │  PROCESSING  │
│  (Listening) │                    │  (Capturing) │                  │ (Transcribing)│
└─────────────┘                    └─────────────┘                   └──────┬───────┘
       ▲                                                                    │
       └────────────────────── reset & loop ────────────────────────────────┘
```

### State Details

| State | What Happens | Audio Config |
|-------|-------------|--------------|
| **WAKEWORD** | Monitors mic for wake word using OpenWakeWord (confidence > 0.5) | 1280 samples / 80ms chunks at 16kHz |
| **RECORDING** | Records speech, uses WebRTC VAD to track speech/silence, calculates RMS for visualizer | 480 samples / 30ms chunks at 16kHz |
| **PROCESSING** | Converts PCM to float32, runs Faster-Whisper, filters hallucinations, emits transcript | — |

---

## Models & Libraries

| Component | Library | Details |
|-----------|---------|---------|
| Wake Word Engine | `openwakeword` | Custom `dhatri.onnx` model (fallback: built-in `alexa`) |
| Voice Activity Detection | `webrtcvad` | Aggressiveness mode 2 |
| Speech-to-Text | `faster-whisper` | `base.en` model, CPU, `int8` quantization, `beam_size=1` |
| Audio Capture | `pyaudio` | 16kHz, mono, 16-bit PCM |
| Signal Processing | `numpy` | PCM → float32 conversion, RMS calculation |

---

## Setup

### Prerequisites

- Python 3.9+
- A working microphone
- **Windows**: No special build tools required for this microservice

### Installation

```bash
cd listen_microservice
pip install -r requirements.txt
```

### Wake Word Model (Optional)

By default, the service falls back to the built-in **"Alexa"** wake word if the custom model is missing. To use **"Dhatri"** as the wake word:

1. Run `python generate_wakeword.py` for instructions
2. Open the [OpenWakeWord Colab notebook](https://colab.research.google.com/) and train with `target_word = "dhatri"`
3. Download the trained model and place it at:
   ```
   listen_microservice/models/dhatri.onnx
   ```

### Whisper Model

The Faster-Whisper `base.en` model is downloaded automatically on first run and cached in `models/`.

---

## Usage

### Standalone

```bash
python main.py
```

The service will:
1. Initialize the microphone and wake word engine
2. Load the Whisper model in a background thread
3. Begin listening for the wake word
4. Print transcriptions to stdout as `[YOU]: <text>`

### Integrated (with Dhatri GUI)

The service is designed to be imported and run as a worker thread:

```python
from listen_microservice.main import listen_worker

# Launch in a background thread with communication queues
listen_worker(shutdown_event, state_queue)
```

The `state_queue` receives status updates and transcriptions that the GUI uses to update the chat display and audio visualizer.

---

## Configuration

All configuration is via constants in `main.py`:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `SAMPLE_RATE` | `16000` Hz | Audio sample rate |
| `CHUNK_SIZE` | `1280` | Samples per wake word chunk (80ms) |
| `VAD_FRAME_MS` | `30` ms | WebRTC VAD frame duration |
| `SILENCE_DURATION_THRESHOLD` | `2.5` s | Silence duration to stop recording |
| `WAIT_FOR_SPEECH_THRESHOLD` | `4.0` s | Max wait for speech to start |
| `WHISPER_MODEL_SIZE` | `base.en` | Faster-Whisper model variant |

### Hallucination Filter

The service automatically discards these common Whisper artifacts on silent/noisy audio:
`"you"`, `"you."`, `"you!"`, `"thanks for watching."`, `"thank you."`, and similar variants.

---

## File Structure

```
listen_microservice/
├── main.py                 # Core service: wake word → VAD → STT pipeline
├── generate_wakeword.py    # Instructions for training custom wake word
├── requirements.txt        # Python dependencies
└── models/
    ├── dhatri.onnx         # Custom wake word model (user-provided)
    └── models--Systran--faster-whisper-base.en/  # Auto-downloaded STT model
```
