import os
import sys
from datetime import datetime
from tts_engine import TTSEngine

import threading
import queue

def audio_player_thread(q):
    """Background thread that continuously plays audio chunks from the queue."""
    import sounddevice as sd
    while True:
        item = q.get()
        if item is None:  # Poison pill to exit
            q.task_done()
            break
        
        sample_rate, chunk = item
        try:
            sd.play(chunk, sample_rate)
            sd.wait()  # Block this thread until the chunk finishes
        except Exception as e:
            print(f"Playback error: {e}")
        q.task_done()

def main():
    print("==================================================")
    print("      Speak Microservice - Voice Generator        ")
    print("==================================================")
    print("Initializing TTS Engine... (This may take a moment to load into VRAM)")
    
    default_voice_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "default_voice.wav")
    if not os.path.exists(default_voice_path):
        print(f"\nError: default_voice.wav not found at {default_voice_path}.")
        print("Please run set_default_voice.py or ensure the default voice file exists.")
        sys.exit(1)

    # Initialize the TTS Engine with pre-warmed speaker embedding
    engine = TTSEngine(preload_voice=default_voice_path)
        
    print("\nEngine ready! Using voice from 'default_voice.wav'.")
    print("Type your text and hit Enter to generate speech.")
    print("Type 'exit' or 'quit' to stop.")
    
    # Create a persistent audio playback queue and worker thread.
    # Reused across all user inputs instead of spawning a new thread per utterance.
    audio_queue = queue.Queue(maxsize=4)
    player = threading.Thread(target=audio_player_thread, args=(audio_queue,), daemon=True)
    player.start()
    
    while True:
        try:
            print("\n" + "-"*50)
            text_input = input("Enter text: ").strip()
            
            if not text_input:
                continue
                
            if text_input.lower() in ['exit', 'quit']:
                print("Exiting...")
                break
                
            print("Generating audio stream in-memory...")
            
            try:
                # Consume the generator sentence by sentence.
                # Chunks are pushed to the persistent audio queue, so the next
                # sentence is generated while the current one is still playing.
                for sample_rate, audio_chunk in engine.generate_stream(text_input, default_voice_path):
                    audio_queue.put((sample_rate, audio_chunk))
                    
                # Wait for all queued chunks to finish playing before asking for next input
                audio_queue.join()
            except ImportError:
                print("Could not stream audio directly. Please install sounddevice.")
            except Exception as e:
                print(f"Audio playback error: {e}")
                
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"\nAn error occurred during generation: {e}")
    
    # Shut down the player thread cleanly
    audio_queue.put(None)
    player.join(timeout=5)

if __name__ == "__main__":
    main()
