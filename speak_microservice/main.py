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
            break
        
        sample_rate, chunk = item
        sd.play(chunk, sample_rate)
        sd.wait() # Block this thread until the chunk finishes
        q.task_done()

def main():
    print("==================================================")
    print("      Speak Microservice - Voice Generator        ")
    print("==================================================")
    print("Initializing TTS Engine... (This may take a moment to load into VRAM)")
    
    # Initialize the TTS Engine
    engine = TTSEngine()
    
    default_voice_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "default_voice.wav")
    if not os.path.exists(default_voice_path):
        print(f"\nWarning: default_voice.wav not found at {default_voice_path}.")
        print("Please run set_default_voice.py or ensure the default voice file exists.")
        sys.exit(1)
        
    print("\nEngine ready! Using voice from 'default_voice.wav'.")
    print("Type your text and hit Enter to generate speech.")
    print("Type 'exit' or 'quit' to stop.")
    
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
            
            # Create a queue and start the playback thread
            audio_queue = queue.Queue()
            player_thread = threading.Thread(target=audio_player_thread, args=(audio_queue,))
            player_thread.start()
            
            try:
                # Consume the generator sentence by sentence
                for sample_rate, audio_chunk in engine.generate_stream(text_input, default_voice_path):
                    audio_queue.put((sample_rate, audio_chunk))
                    
                # Signal the player thread to finish after generation is complete
                audio_queue.put(None)
                player_thread.join() # Wait for all audio to finish playing before asking for next input
            except ImportError:
                print("Could not stream audio directly. Please install sounddevice.")
            except Exception as e:
                print(f"Audio playback error: {e}")
                audio_queue.put(None)
                
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"\nAn error occurred during generation: {e}")

if __name__ == "__main__":
    main()
