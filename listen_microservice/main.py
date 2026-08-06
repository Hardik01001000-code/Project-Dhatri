import os
import time
import numpy as np
import pyaudio
import webrtcvad
import openwakeword
import threading
import queue
from openwakeword.model import Model
from faster_whisper import WhisperModel

import warnings
warnings.filterwarnings("ignore")
os.environ["TRANSFORMERS_NO_ADVISORY_WARNINGS"] = "1"
import logging
logging.getLogger("transformers.tokenization_utils_base").setLevel(logging.ERROR)

# --- Configuration ---
# Fix model path for relative imports when called from main_app.py
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WAKE_WORD_MODEL = os.path.join(BASE_DIR, "models/dhatri.onnx")
WHISPER_MODELS_DIR = os.path.join(BASE_DIR, "models/")

WHISPER_MODEL_SIZE = "base.en" # Lightweight model so it doesn't melt the PC
SAMPLE_RATE = 16000
CHUNK_SIZE = 1280 # 80ms chunk for 16kHz
VAD_FRAME_MS = 30 # WebRTC VAD needs 10, 20, or 30ms frames
VAD_CHUNK_SIZE = int(SAMPLE_RATE * VAD_FRAME_MS / 1000)
SILENCE_DURATION_THRESHOLD = 1.2 # Stop recording after 1.2 seconds of silence
WAIT_FOR_SPEECH_THRESHOLD = 2.5 # Wait 2.5 seconds for user to start speaking
MAX_RECORDING_SECONDS = 30.0 # High cap: allows speaking up to 30 seconds for long prompts
MIN_SPEECH_RMS = 250.0 # Ignore VAD speech detection if volume is below this noise floor

# --- Audio Gain & Wake Word Tuning ---
WAKE_WORD_THRESHOLD = 0.3 # Lowered from 0.5 — laptop mics produce quieter audio
GAIN_TARGET_RMS = 3000 # Target RMS level for normalization (int16 range: 0-32768)
GAIN_MAX_FACTOR = 10.0 # Cap gain to avoid amplifying silence into noise

# Number of recent wake word chunks to keep as a pre-buffer so the first
# word of a command isn't clipped after wake word detection.
PRE_DETECTION_BUFFER_CHUNKS = 5 # ~400ms of audio at 80ms/chunk

def setup_vad():
    vad = webrtcvad.Vad()
    vad.set_mode(2) # Mode 2 + RMS threshold filters out mic noise & static effectively
    return vad

def normalize_audio_gain(audio_np):
    """Normalize audio to a consistent RMS level to compensate for quiet laptop mics."""
    rms = np.sqrt(np.mean(np.square(audio_np.astype(np.float32))))
    if rms < 1.0:
        return audio_np # Pure silence, don't amplify
    gain = min(GAIN_TARGET_RMS / rms, GAIN_MAX_FACTOR)
    if gain > 1.0:
        amplified = (audio_np.astype(np.float32) * gain)
        amplified = np.clip(amplified, -32768, 32767)
        return amplified.astype(np.int16)
    return audio_np

whisper_model = None

def load_whisper_bg():
    global whisper_model
    # download_root ensures the model is saved and loaded directly from the models folder
    # Reverting to CPU because cublas64_12.dll (CUDA 12) is not installed on this system.
    whisper_model = WhisperModel(WHISPER_MODEL_SIZE, device="cpu", compute_type="int8", download_root=WHISPER_MODELS_DIR)
    print("\n[System] Whisper AI Model finished loading in the background!", flush=True)

def transcribe_audio(audio_data):
    global whisper_model
    if whisper_model is None:
        print("\nWaiting for Whisper AI to finish loading...", flush=True)
        while whisper_model is None:
            time.sleep(0.1)
            
    print("\nTranscribing...", flush=True)
    # Convert raw audio bytes to float32 numpy array
    audio_np = np.frombuffer(b''.join(audio_data), dtype=np.int16).astype(np.float32) / 32768.0
    
    # beam_size=1 (greedy decoding) makes it significantly faster on CPU
    segments, info = whisper_model.transcribe(audio_np, beam_size=1, language="en", condition_on_previous_text=False)
        
    transcribed_text = ""
    for segment in segments:
        if segment.no_speech_prob > 0.85:
            continue
        transcribed_text += segment.text + " "
        
    final_text = transcribed_text.strip()
    
    # Filter common whisper hallucinations
    hallucinations = ["you", "you.", "you!", "thanks for watching.", "thanks for watching!", "thanks for watching", "thank you.", "thank you"]
    if final_text.lower().strip() in hallucinations or not final_text:
        print(" [Filtered background noise hallucination]", flush=True)
        return ""
        
    print(f"[YOU]: {final_text}", flush=True)
    return final_text

def listen_worker(shutdown_event=None, state_queue=None):
    print("Initializing listen microservice...", flush=True)
    
    # Initialize Faster Whisper in the background
    print("Starting background load of Whisper AI (CPU)...", flush=True)
    threading.Thread(target=load_whisper_bg, daemon=True).start()
    
    # Initialize OpenWakeWord
    print(f"Loading wake word model: {WAKE_WORD_MODEL}", flush=True)
    if not os.path.exists(WAKE_WORD_MODEL):
        print(f"\n[WARNING]: Custom wake word model not found at {WAKE_WORD_MODEL}")
        print("[WARNING]: Falling back to the default 'alexa' wake word so the app can run.")
        print("[WARNING]: You must say 'Alexa' to trigger the system for now!\n", flush=True)
        owwModel = Model(wakeword_models=["alexa"])
    else:
        owwModel = Model(wakeword_models=[WAKE_WORD_MODEL], inference_framework="onnx")
    
    # Setup VAD
    vad = setup_vad()
    
    # Initialize PyAudio
    audio = pyaudio.PyAudio()
    stream = audio.open(format=pyaudio.paInt16,
                        channels=1,
                        rate=SAMPLE_RATE,
                        input=True,
                        frames_per_buffer=CHUNK_SIZE)
    
    # Rolling buffer to keep recent audio chunks before wake word detection
    # so the beginning of a command spoken right after the wake word isn't lost
    from collections import deque
    pre_buffer = deque(maxlen=PRE_DETECTION_BUFFER_CHUNKS)

    print("\n=======================================================")
    if not os.path.exists(WAKE_WORD_MODEL):
        print(" Listening for wake word: 'ALEXA' (Fallback)")
    else:
        print(" Listening for wake word: 'DHATRI'")
    print("=======================================================\n", flush=True)
    
    state = "WAKEWORD" # States: WAKEWORD, RECORDING, PROCESSING
    if state_queue: state_queue.put({"type": "STATE", "value": state})
    
    recorded_audio = []
    silence_frames = 0
    max_silence_frames = int((SILENCE_DURATION_THRESHOLD * 1000) / VAD_FRAME_MS)

    try:
        while True:
            if shutdown_event and shutdown_event.is_set():
                break

            if state == "WAKEWORD":
                try:
                    chunk = stream.read(CHUNK_SIZE, exception_on_overflow=False)
                except IOError as e:
                    print(f"[Listen] Audio stream error, recovering: {e}", flush=True)
                    try:
                        stream.stop_stream()
                        stream.start_stream()
                    except Exception:
                        pass
                    continue
                
                audio_np = np.frombuffer(chunk, dtype=np.int16)
                
                # Normalize gain for quiet laptop mics before feeding to wake word model
                audio_np_normalized = normalize_audio_gain(audio_np)
                
                # Keep chunk in rolling pre-buffer for seamless transition to recording
                pre_buffer.append(chunk)
                
                prediction = owwModel.predict(audio_np_normalized)
                
                for mdl, score in prediction.items():
                    # Debug feedback for scores above 0.08 to help user test pronunciation
                    if score > 0.08 and score <= WAKE_WORD_THRESHOLD:
                        print(f"[WakeWord Debug] Hear speech! '{mdl}' confidence: {score:.2f} (Needs > {WAKE_WORD_THRESHOLD:.2f})", flush=True)

                    if score > WAKE_WORD_THRESHOLD: 
                        print(f"\n*** Wake Word Detected! ({mdl}: {score:.2f}) ***")
                        print("Listening to your command...")
                        state = "RECORDING"
                        if state_queue: state_queue.put({"type": "STATE", "value": state})
                        
                        # Seed recorded_audio with pre-buffer to preserve speech
                        # that started right as the wake word ended
                        recorded_audio = list(pre_buffer)
                        pre_buffer.clear()
                        silence_frames = 0
                        has_started_speaking = False
                        break
                        
            elif state == "RECORDING":
                try:
                    chunk = stream.read(VAD_CHUNK_SIZE, exception_on_overflow=False)
                except IOError as e:
                    print(f"[Listen] Audio stream error during recording: {e}", flush=True)
                    continue
                recorded_audio.append(chunk)
                
                audio_np = np.frombuffer(chunk, dtype=np.int16)
                # Calculate RMS volume level
                rms = float(np.sqrt(np.mean(np.square(audio_np.astype(np.float32)))))
                
                if state_queue:
                    state_queue.put({"type": "RMS", "value": rms})
                
                try:
                    # Speech requires BOTH WebRTC VAD = True AND volume > MIN_SPEECH_RMS noise floor
                    raw_vad_speech = vad.is_speech(chunk, SAMPLE_RATE)
                    is_speech = raw_vad_speech and (rms >= MIN_SPEECH_RMS)
                    
                    if not is_speech:
                        silence_frames += 1
                    else:
                        has_started_speaking = True
                        silence_frames = 0
                except Exception as e:
                    pass
                    
                current_threshold_frames = int((SILENCE_DURATION_THRESHOLD * 1000) / VAD_FRAME_MS) if has_started_speaking else int((WAIT_FOR_SPEECH_THRESHOLD * 1000) / VAD_FRAME_MS)
                
                # Total time recorded in seconds
                recording_time_sec = (len(recorded_audio) * VAD_FRAME_MS) / 1000.0

                # Transition to processing if silence threshold is reached OR max duration exceeded
                if silence_frames > current_threshold_frames or recording_time_sec >= MAX_RECORDING_SECONDS:
                    print(f"Processing command (recorded {recording_time_sec:.1f}s)...", flush=True)
                    state = "PROCESSING"
                    if state_queue: state_queue.put({"type": "STATE", "value": state})
                    
                    final_text = transcribe_audio(recorded_audio)
                    if state_queue and final_text:
                        state_queue.put({"type": "TEXT", "value": final_text})
                    
                    state = "WAKEWORD"
                    if state_queue: state_queue.put({"type": "STATE", "value": state})
                    silence_frames = 0
                    recorded_audio = []
                    pre_buffer.clear()
                    try:
                        stream.read(stream.get_read_available(), exception_on_overflow=False)
                    except IOError:
                        pass
                    owwModel.reset()
                    
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        stream.stop_stream()
        stream.close()
        audio.terminate()

if __name__ == "__main__":
    listen_worker()
