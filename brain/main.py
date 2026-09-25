import os
import sys
import threading
import queue

# Add project root to sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from brain.core import process_prompt

def audio_player_thread(q):
    """Background worker thread that continuously plays audio chunks from the queue."""
    try:
        import sounddevice as sd
    except ImportError:
        print("[Speak Microservice] Error: sounddevice library not installed.")
        return

    while True:
        item = q.get()
        if item is None:
            q.task_done()
            break
        sample_rate, chunk = item
        try:
            sd.play(chunk, sample_rate)
            sd.wait()
        except Exception as e:
            print(f"[Speak Microservice] Playback error: {e}")
        q.task_done()

def main():
    print("=" * 60)
    print("       Project Dhatri - Brain + Speak Microservices        ")
    print("=" * 60)
    print("Initializing Brain & Speak Microservices...")

    # Ensure speak_microservice is accessible
    speak_dir = os.path.join(PROJECT_ROOT, "speak_microservice")
    if speak_dir not in sys.path:
        sys.path.insert(0, speak_dir)

    default_voice_path = os.path.join(speak_dir, "default_voice.wav")
    if not os.path.exists(default_voice_path):
        fallback_voice = os.path.join(speak_dir, "test_reference.wav")
        if os.path.exists(fallback_voice):
            import shutil
            shutil.copyfile(fallback_voice, default_voice_path)

    # Initialize Speak Microservice TTS Engine
    engine = None
    try:
        from speak_microservice.tts_engine import TTSEngine
        engine = TTSEngine(preload_voice=default_voice_path)
        print("[Speak Microservice] TTS Engine ready with cloned voice.")
    except Exception as e:
        print(f"[Speak Microservice] Warning: TTS Engine could not be started ({e}).")

    # Persistent playback queue and worker
    audio_queue = queue.Queue(maxsize=4)
    player = threading.Thread(target=audio_player_thread, args=(audio_queue,), daemon=True)
    player.start()

    print("\n[Brain Microservice] Ready!")
    print("Type your message and hit Enter. The Brain will return the same text,")
    print("and the Speak Microservice will speak whatever the Brain outputs.")
    print("Type 'exit' or 'quit' to stop.\n")

    while True:
        try:
            user_input = input("You > ").strip()
            if not user_input:
                continue

            if user_input.lower() in ["exit", "quit"]:
                print("Exiting...")
                break

            # 1. Process prompt with the Brain microservice
            brain_output = process_prompt(user_input)
            print(f"Brain > {brain_output}")

            # 2. Speak the Brain's output via Speak microservice
            if engine and brain_output:
                print(f"[Speak Microservice] Speaking: \"{brain_output}\"...")
                try:
                    for sample_rate, audio_chunk in engine.generate_stream(brain_output, default_voice_path):
                        audio_queue.put((sample_rate, audio_chunk))
                    audio_queue.join()
                except Exception as e:
                    print(f"[Speak Microservice] Playback error: {e}")

        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"Error: {e}")

    # Clean shutdown of player thread
    audio_queue.put(None)
    player.join(timeout=3)

if __name__ == "__main__":
    main()
