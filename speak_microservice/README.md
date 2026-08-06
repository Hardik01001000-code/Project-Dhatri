# 🔊 Speak Microservice

A fully offline text-to-speech engine with zero-shot voice cloning for Project Dhatri. Combines MeloTTS for fast English speech synthesis with OpenVoice V2 for neural voice cloning — producing natural-sounding speech in any target voice from a single reference audio sample.

---

## Overview

The Speak Microservice converts text into speech that sounds like a specific person. Provide a short reference audio clip (5–10 seconds), and the engine will synthesize any text in that voice — with support for real-time sentence-level streaming.

### Key Features

- **🔒 100% Offline** — All models run locally, no API calls or internet required
- **🎭 Zero-Shot Voice Cloning** — Clone any voice from a single audio sample using OpenVoice V2
- **⚡ Streaming Synthesis** — Sentence-level streaming for low-latency audio playback
- **🧠 Smart Caching** — Speaker embeddings are cached by MD5 hash to avoid recomputation
- **🎛️ GPU Accelerated** — Automatically uses NVIDIA CUDA when available, falls back to CPU

---

## Architecture

```
Input Text + Reference Audio (.wav)
            │
            ├──► 1. Speaker Embedding Extraction
            │      └── Cache lookup (MD5 hash) → or → OpenVoice se_extractor
            │
            ├──► 2. Base Speech Synthesis (MeloTTS)
            │      └── English text → Base waveform (EN-US speaker)
            │
            └──► 3. Tone Color Conversion (OpenVoice V2)
                   ├── Source embedding: base EN-US speaker
                   ├── Target embedding: reference voice
                   └── Base waveform → Cloned voice output
                           │
                           ▼
                    Final Audio (file or streaming chunks)
```

### Processing Pipeline

1. **Embedding Extraction** — Extracts a speaker embedding tensor from the reference audio. Results are cached as `.pt` files keyed by MD5 hash in `embeddings_cache/`
2. **Base TTS** — MeloTTS generates a base English waveform from the input text
3. **Voice Conversion** — OpenVoice V2's ToneColorConverter transforms the base audio to match the target speaker's timbre and tone

---

## Models & Libraries

| Component | Library / Model | Purpose |
|-----------|----------------|---------|
| Base TTS | `melo.api.TTS` (MeloTTS) | Fast English speech synthesis |
| Voice Cloning | `openvoice.api.ToneColorConverter` | Neural tone/timbre color conversion |
| Speaker Extraction | `openvoice.se_extractor` | VAD + speaker embedding extraction |
| Tensor Computation | `torch` (PyTorch) | GPU/CPU model execution |
| Audio I/O | `soundfile`, `sounddevice` | Audio encoding/decoding and playback |
| FFmpeg | `imageio_ffmpeg` | Audio format processing |

---

## Setup

### Prerequisites

- Python 3.9+
- NVIDIA GPU with CUDA recommended (CPU works but is slower)
- ~2 GB disk space for model checkpoints

### Installation

```bash
cd speak_microservice

# 1. Install Python dependencies
pip install -r requirements.txt

# 2. Download OpenVoice V2 model checkpoints
python setup_env.py
```

This downloads and extracts the `checkpoints_v2/` directory containing:
- `converter/checkpoint.pth` — ToneColorConverter weights
- `converter/config.json` — Model configuration
- `base_speakers/ses/en-us.pth` — Base English speaker embedding

### Configure Your Voice

Provide a 5–10 second reference audio clip of the target voice:

```bash
# Option 1: Copy directly
cp /path/to/your/voice.wav default_voice.wav

# Option 2: Use the config script
python set_default_voice.py /path/to/your/voice.wav
```

Supported formats: `.wav`, `.mp3`, `.flac`, `.ogg`

### Verify Installation

```bash
python test_tts.py
```

This generates `test_output.wav` to verify that all models load correctly and audio synthesis works end-to-end.

---

## Usage

### Standalone (Interactive CLI)

```bash
python main.py
```

Type any text and hear it spoken in the configured voice. Audio streams in real-time, sentence by sentence.

### Integrated (with Dhatri GUI)

The TTS engine is imported directly by the GUI's speak thread:

```python
from speak_microservice.tts_engine import TTSEngine

engine = TTSEngine()

# One-shot generation (saves to file)
engine.generate("Hello, world!", "default_voice.wav", output_path="output.wav")

# Streaming generation (yields audio chunks)
for sample_rate, audio_chunk in engine.generate_stream("Hello!", "default_voice.wav"):
    play_audio(audio_chunk, sample_rate)
```

---

## API Reference

### `TTSEngine` Class

| Method | Description |
|--------|-------------|
| `__init__(checkpoints_dir, cache_dir)` | Loads MeloTTS + OpenVoice models, detects GPU |
| `get_target_speaker_embedding(ref_audio_path)` | Extracts/caches speaker embedding from reference audio |
| `generate(text, ref_audio_path, output_path, speed)` | Full text → audio file synthesis |
| `generate_stream(text, ref_audio_path, speed)` | Sentence-level streaming synthesis (yields chunks) |

---

## Configuration

| Parameter | Location | Description |
|-----------|----------|-------------|
| Reference Voice | `default_voice.wav` | Target voice for cloning |
| Checkpoints | `checkpoints_v2/` | OpenVoice V2 model weights |
| Embedding Cache | `embeddings_cache/` | Cached speaker embedding tensors |
| Speech Speed | `speed` param (default `1.0`) | Playback speed multiplier |

### Environment Variables (set internally)

| Variable | Value | Purpose |
|----------|-------|---------|
| `HF_HUB_OFFLINE` | `1` | Prevents HuggingFace downloads at runtime |
| `TRANSFORMERS_OFFLINE` | `1` | Enforces fully offline model loading |

---

## File Structure

```
speak_microservice/
├── main.py                 # Interactive CLI for testing TTS
├── tts_engine.py           # Core TTSEngine class (MeloTTS + OpenVoice V2)
├── set_default_voice.py    # Utility to configure reference voice
├── setup_env.py            # Downloads OpenVoice V2 checkpoints
├── test_tts.py             # End-to-end verification script
├── default_voice.wav       # Reference voice audio (user-provided, git-ignored)
├── checkpoints_v2/         # OpenVoice V2 model weights (git-ignored)
│   ├── converter/
│   │   ├── checkpoint.pth
│   │   └── config.json
│   └── base_speakers/
│       └── ses/en-us.pth
├── embeddings_cache/       # Cached speaker embeddings (auto-generated)
└── output/                 # Generated audio output directory
```
